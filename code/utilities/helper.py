import os
import openai
from dotenv import load_dotenv
import logging
import re
import hashlib
import numpy as np
import difflib
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import AzureOpenAI
from langchain.vectorstores.base import VectorStore
from langchain.chains import ChatVectorDBChain
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.qa_with_sources import load_qa_with_sources_chain
from langchain.chains.llm import LLMChain
from langchain.chains.chat_vector_db.prompts import CONDENSE_QUESTION_PROMPT
from langchain.prompts import PromptTemplate
from langchain.document_loaders.base import BaseLoader
from langchain.document_loaders import WebBaseLoader
from langchain.text_splitter import TokenTextSplitter, TextSplitter
from langchain.document_loaders.base import BaseLoader
from langchain.document_loaders import TextLoader
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from utilities.formrecognizer import AzureFormRecognizerClient
from utilities.blobstorage import AzureBlobStorageClient
from utilities.customprompt import PROMPT, SMES_PROMPT
from utilities.redis import RedisExtended
from utilities.vectorsearch import AzureSearch, AzureSearchVectorStoreRetriever
from utilities.similarities import SentenceSimilarityComparator
import pandas as pd
import urllib

from fake_useragent import UserAgent


class LLMHelper:
    def __init__(self,
        document_loaders : BaseLoader = None, 
        text_splitter: TextSplitter = None,
        embeddings: OpenAIEmbeddings = None,
        llm: AzureOpenAI = None,
        temperature: float = None,
        max_tokens: int = None,
        custom_prompt: str = "",
        vector_store: VectorStore = None,
        k: int = None,
        pdf_parser: AzureFormRecognizerClient = None,
        blob_client: AzureBlobStorageClient = None):

        load_dotenv()
        openai.api_type = "azure"
        openai.api_base = os.getenv('OPENAI_API_BASE')
        openai.api_version = "2023-03-15-preview"
        openai.api_key = os.getenv("OPENAI_API_KEY")

        # Azure OpenAI settings
        self.api_base = openai.api_base
        self.api_version = openai.api_version
        self.index_name: str = "embeddings"
        self.model: str = os.getenv('OPENAI_EMBEDDINGS_ENGINE_DOC', "text-embedding-ada-002")
        self.deployment_name: str = os.getenv("OPENAI_ENGINE", os.getenv("OPENAI_ENGINES", "gpt-35-turbo"))
        
        # Change this to "Text" if you want to use DaVinci-003 for text generation
        self.deployment_type: str = os.getenv("OPENAI_DEPLOYMENT_TYPE", "Chat")
        
        self.temperature: float = float(os.getenv("OPENAI_TEMPERATURE", 0.2)) if temperature is None else temperature
        self.max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", -1)) if max_tokens is None else max_tokens
        

        self.vector_store_type = os.getenv("VECTOR_STORE_TYPE")

        # Azure Search settings
        self.vector_store_address: str = os.getenv('AZURE_SEARCH_SERVICE_NAME')
        self.vector_store_password: str = os.getenv('AZURE_SEARCH_ADMIN_KEY')

        self.chunk_size = int(os.getenv('CHUNK_SIZE', 2000))
        self.chunk_overlap = int(os.getenv('CHUNK_OVERLAP', 500))
        
        self.chunk_size_smes = int(os.getenv('CHUNK_SIZE_SMES', 250))
        self.chunk_overlap_smes = int(os.getenv('CHUNK_OVERLAP_SMES', 50))
        
        self.document_loaders: BaseLoader = WebBaseLoader if document_loaders is None else document_loaders
        self.text_splitter: TextSplitter = TokenTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap) if text_splitter is None else text_splitter
        self.embeddings: OpenAIEmbeddings = OpenAIEmbeddings(model=self.model, chunk_size=1) if embeddings is None else embeddings
        self.comparator: SentenceSimilarityComparator = SentenceSimilarityComparator()
        
        if self.deployment_type == "Chat":
            self.llm: ChatOpenAI = ChatOpenAI(model_name=self.deployment_name, engine=self.deployment_name, temperature=self.temperature, max_tokens=self.max_tokens if self.max_tokens != -1 else None) if llm is None else llm
        else:
            self.llm: AzureOpenAI = AzureOpenAI(deployment_name=self.deployment_name, temperature=self.temperature, max_tokens=self.max_tokens) if llm is None else llm
        
        if self.vector_store_type == "AzureSearch":
            self.vector_store: VectorStore = AzureSearch(azure_cognitive_search_name=self.vector_store_address, azure_cognitive_search_key=self.vector_store_password, index_name=self.index_name, embedding_function=self.embeddings.embed_query)  
        else:
            self.vector_store: RedisExtended = RedisExtended(redis_url=self.vector_store_full_address, index_name=self.index_name, embedding_function=self.embeddings.embed_query)     
        
        self.k : int = 3 if k is None else k
        self.smes_k = 8
        self.pdf_parser : AzureFormRecognizerClient = AzureFormRecognizerClient() if pdf_parser is None else pdf_parser
        self.blob_client: AzureBlobStorageClient = AzureBlobStorageClient() if blob_client is None else blob_client
        self.user_agent: UserAgent() = UserAgent()
        self.user_agent.random

    def add_embeddings_lc(self, source_url,index, citation_URL,file_name):
        self.index_name = index
        
        if self.vector_store_type == "AzureSearch":
            self.vector_store: VectorStore = AzureSearch(azure_cognitive_search_name=self.vector_store_address, azure_cognitive_search_key=self.vector_store_password, index_name=self.index_name, embedding_function=self.embeddings.embed_query)  
        else:
            self.vector_store: RedisExtended = RedisExtended(redis_url=self.vector_store_full_address, index_name=self.index_name, embedding_function=self.embeddings.embed_query)     
        
        try:
            documents = self.document_loaders(source_url).load()
            
            # Convert to UTF-8 encoding for non-ascii text
            for(document) in documents:
                try:
                    if document.page_content.encode("iso-8859-1") == document.page_content.encode("latin-1"):
                        document.page_content = document.page_content.encode("iso-8859-1").decode("utf-8", errors="ignore")
                except:
                    pass
            
            if index =='smes':
                self.text_splitter = TokenTextSplitter(chunk_size=self.chunk_size_smes, chunk_overlap=self.chunk_overlap_smes)
                # print("Chunk : ", self.chunk_size_smes, "Overlap : ", self.chunk_overlap_smes)
            else:
                self.text_splitter = TokenTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)
                # print("Chunk : ", self.chunk_size, "Overlap : ", self.chunk_overlap)
                
            docs = self.text_splitter.split_documents(documents)
            
            # Remove half non-ascii character from start/end of doc content (langchain TokenTextSplitter may split a non-ascii character in half)
            pattern = re.compile(r'[\x00-\x1f\x7f\u0080-\u00a0\u2000-\u3000\ufff0-\uffff]')
            for(doc) in docs:
                doc.page_content = re.sub(pattern, '', doc.page_content)
                if doc.page_content == '':
                    docs.remove(doc)
            keys = []
            for i, doc in enumerate(docs):
                # Create a unique key for the document
                source_url = source_url.split('?')[0]
                filename = file_name
                hash_key = hashlib.sha1(f"{source_url}_{i}".encode('utf-8')).hexdigest()
                hash_key = f"doc:{self.index_name}:{hash_key}"
                keys.append(hash_key)
                doc.metadata = {"source": f"[{source_url}]({source_url}_SAS_TOKEN_PLACEHOLDER_)" , "chunk": i, "key": hash_key, "filename": filename, "citation_url": citation_URL}
            if self.vector_store_type == 'AzureSearch':
                self.vector_store.add_documents(documents=docs, keys=keys)
            else:
                self.vector_store.add_documents(documents=docs, redis_url=self.vector_store_full_address,  index_name=self.index_name, keys=keys)
            
        except Exception as e:
            logging.error(f"Error adding embeddings for {source_url}: {e}")
            raise e


    def convert_file_and_add_embeddings(self, source_url, filename, index,citation_URL, meta_filename):
        
        self.index_name = index 
        self.prompt = SMES_PROMPT if index == 'smes' else PROMPT 
        
        if self.vector_store_type == "AzureSearch":
            self.vector_store: VectorStore = AzureSearch(azure_cognitive_search_name=self.vector_store_address, azure_cognitive_search_key=self.vector_store_password, index_name=self.index_name, embedding_function=self.embeddings.embed_query)  
        else:
            self.vector_store: RedisExtended = RedisExtended(redis_url=self.vector_store_full_address, index_name=self.index_name, embedding_function=self.embeddings.embed_query)     
        
        
        # Extract the text from the file
        text = self.pdf_parser.analyze_read(source_url)

        # Upload the text to Azure Blob Storage
        converted_filename = f"converted/{filename}.txt"
        source_url = self.blob_client.upload_file("\n".join(text), f"converted/{filename}.txt", content_type='text/plain; charset=utf-8')

        print(f"Converted file uploaded to {source_url} with filename {filename}")
        # Update the metadata to indicate that the file has been converted
        self.blob_client.upsert_blob_metadata( index, filename, {"converted": "true"})

        self.add_embeddings_lc(source_url=source_url, index=index, citation_URL = citation_URL,file_name=meta_filename )

        return converted_filename

    def get_all_documents(self, k: int = None):
        result = self.vector_store.similarity_search(query="*", k= k if k else self.k)
        return pd.DataFrame(list(map(lambda x: {
                'key': x.metadata['key'],
                'filename': x.metadata['filename'],
                'index':x.metadata['index'],
                'source': urllib.parse.unquote(x.metadata['source']), 
                'content': x.page_content, 
                'metadata' : x.metadata,
                }, result)))

    def get_semantic_answer_lang_chain(self, question,index, chat_history):
        self.index_name = index
        k = 4
        if index == 'smes':
            k = 30
        self.prompt = SMES_PROMPT if index == 'smes' else PROMPT 

        
        if self.vector_store_type == "AzureSearch":
            self.vector_store: VectorStore = AzureSearch(azure_cognitive_search_name=self.vector_store_address, azure_cognitive_search_key=self.vector_store_password, index_name=self.index_name, embedding_function=self.embeddings.embed_query)
        else:
            self.vector_store: RedisExtended = RedisExtended(redis_url=self.vector_store_full_address, index_name=self.index_name, embedding_function=self.embeddings.embed_query)
        
        question_generator = LLMChain(llm=self.llm, prompt=CONDENSE_QUESTION_PROMPT, verbose=False)
        
        self.prompt = PROMPT
        
        doc_chain = load_qa_with_sources_chain(self.llm, chain_type="stuff", verbose=False, prompt=self.prompt)
        chain = ConversationalRetrievalChain(
            retriever=self.vector_store.as_retriever(search_kwargs = {"k": k}),
            question_generator=question_generator,
            combine_docs_chain=doc_chain,
            return_source_documents=True
        )
        result = chain({"question": question, "chat_history": chat_history})
        context = "\n".join(list(map(lambda x: x.page_content, result['source_documents'])))
        
        context_list_sources = list(map(lambda x: x.metadata['source'], result['source_documents']))
        
        
        result['answer'] = result['answer'].split('SOURCES:')[0].split('Sources:')[0].split('SOURCE:')[0].split('Source:')[0].split('source:')[0].split('sources:')[0].split('SOURCE')[0].split('Source')[0]
        
        # if last character in result['answer'] is '(' then remove it 
        if result['answer'][-1] == '(':
            result['answer'] = result['answer'][:-1]
            
        
        # get the metadata in 'URL' field for all the sources 
        final_sources = []

        for source_doc in result['source_documents']:
            # URL is in ['citation_URL'] field of the metadata of the vector database 
            URL = source_doc.metadata['citation_url']
            filename = source_doc.metadata['filename']
            if URL != 'NONE':
                final_sources.append({'URL': URL, 'filename': filename})

        if index == 'smes':
            final_sources = [] # don't return sources for smes index
            
            
        self.blob_client.add_to_table(index, question, result['answer'], self.temperature)
        
        # similarity_scores = self.comparator.compareSentencesWithSources(result['answer'], context_list_sources)
            
        return question, result['answer'], context, final_sources 


    def get_semantic_answer_lang_chain_exp(self, question,index, chat_history):
        self.index_name = index
        search_type = "semantic_hybrid"
        k = 4
        if index == 'smes':
            k = 30
        
        self.prompt = SMES_PROMPT if index == 'smes' else PROMPT 

            
        if self.vector_store_type == "AzureSearch":
            self.vector_store: VectorStore = AzureSearch(azure_cognitive_search_name=self.vector_store_address, azure_cognitive_search_key=self.vector_store_password, index_name=self.index_name, embedding_function=self.embeddings.embed_query)
            
            Retriever = AzureSearchVectorStoreRetriever(vectorstore=self.vector_store, search_type=search_type, k =  k)
        else:
            self.vector_store: RedisExtended = RedisExtended(redis_url=self.vector_store_full_address, index_name=self.index_name, embedding_function=self.embeddings.embed_query)
        
        question_generator = LLMChain(llm=self.llm, prompt=CONDENSE_QUESTION_PROMPT, verbose=False)

        doc_chain = load_qa_with_sources_chain(self.llm, chain_type="stuff", verbose=False, prompt=self.prompt)
        chain = ConversationalRetrievalChain(
            retriever=Retriever,
            question_generator=question_generator,
            combine_docs_chain=doc_chain,
            return_source_documents=True
        )
        result = chain({"question": question, "chat_history": chat_history})
        context = "\n".join(list(map(lambda x: x.page_content, result['source_documents'])))
        
        context_list_sources = list(map(lambda x: x.metadata['source'], result['source_documents']))
        
        
        result['answer'] = result['answer'].split('SOURCES:')[0].split('Sources:')[0].split('SOURCE:')[0].split('Source:')[0].split('source:')[0].split('sources:')[0].split('SOURCE')[0].split('Source')[0]
        
        # if last character in result['answer'] is '(' then remove it 
        if result['answer'][-1] == '(':
            result['answer'] = result['answer'][:-1]
            
        
        # get the metadata in 'URL' field for all the sources 
        final_sources = []

        for source_doc in result['source_documents']:
            # URL is in ['citation_URL'] field of the metadata of the vector database 
            URL = source_doc.metadata['citation_url']
            filename = source_doc.metadata['filename']
            if URL != 'NONE':
                final_sources.append({'URL': URL, 'filename': filename})

        
        self.blob_client.add_to_table(index, question, result['answer'], self.temperature)
        
        # only keep unique entries in final_sources
        final_sources = [dict(t) for t in {tuple(d.items()) for d in final_sources}]
        
        # similarity_scores = self.comparator.compareSentencesWithSources(result['answer'], context_list_sources)
            
        return question, result['answer'], context, final_sources


    def get_embeddings_model(self):
        OPENAI_EMBEDDINGS_ENGINE_DOC = os.getenv('OPENAI_EMEBDDINGS_ENGINE', os.getenv('OPENAI_EMBEDDINGS_ENGINE_DOC', 'text-embedding-ada-002'))  
        OPENAI_EMBEDDINGS_ENGINE_QUERY = os.getenv('OPENAI_EMEBDDINGS_ENGINE', os.getenv('OPENAI_EMBEDDINGS_ENGINE_QUERY', 'text-embedding-ada-002'))
        return {
            "doc": OPENAI_EMBEDDINGS_ENGINE_DOC,
            "query": OPENAI_EMBEDDINGS_ENGINE_QUERY
        }
