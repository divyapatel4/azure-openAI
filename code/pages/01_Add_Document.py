import streamlit as st
import os, json, re, io
from os import path
import requests
import mimetypes
import traceback
import chardet
from utilities.helper import LLMHelper
import uuid
from redis.exceptions import ResponseError 
from urllib import parse
import pandas as pd
import utilities.scrapdata as scrapdata
from dotenv import load_dotenv
load_dotenv()
import logging
import azure.functions as func
from azure.storage.queue import QueueClient, BinaryBase64EncodePolicy
from utilities.helper import LLMHelper
logger = logging.getLogger('azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)



# Set favicon and page title
st.set_page_config(
    page_title="Add Documents",
    page_icon="assets/logo.png",
    layout="wide"
)

st.session_state['INDEX'] = 'SELECT'

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

def delete_file():
    try:
        embeddings_to_delete = data[data.filename == st.session_state['file_to_drop']].key.tolist()
        embeddings_to_delete = list(map(lambda x: f"{x}", embeddings_to_delete))
        llm_helper.vector_store.delete_keys(embeddings_to_delete)
        st.success("File deleted successfully.")
    except Exception as e:
        st.error(traceback.format_exc())

    

def remote_convert_files_and_add_embeddings():
    url = os.getenv('CONVERT_ADD_EMBEDDINGS_URL')
    print("Remote conversion started.")
    try:
        response = requests.post(url)
        if response.status_code == 200:
            st.success(f"{response.text}\nPlease note this is an asynchronous process and may take a few minutes to complete.")
        else:
            st.error(f"Error: {response.text}")
    except Exception as e:
        st.error(traceback.format_exc())


def add_urls():
    urls = st.session_state['urls'].split('\n')
    for url in urls:
        if url:
            llm_helper.add_embeddings_lc(url)
            st.success(f"Embeddings added successfully for {url}")

@st.cache_data(show_spinner=False)
def get_all_documents():
    return llm_helper.get_all_documents(k=1000)

def upload_file(bytes_data: bytes, file_name: str, index: str):
    # Upload a new file
    st.session_state['filename'] = index + '/' + file_name  # prepend the index folder name
    content_type = mimetypes.MimeTypes().guess_type(file_name)[0]
    charset = f"; charset={chardet.detect(bytes_data)['encoding']}" if content_type == 'text/plain' else ''
    st.session_state['file_url'] = llm_helper.blob_client.upload_file(bytes_data, st.session_state['filename'], content_type=content_type+charset)


with st.sidebar:
    st.header("About this")
    st.write("This is powered by the OpenAI's GPT-3.5 Turbo and is capable of answering your questions related to Microsoft Cloud for Sustainability.")

try:

    llm_helper = LLMHelper()
    st.session_state['INDEX'] = st.selectbox("Select Index", options=['SELECT','smes', 'ado', 'sharepoint'])

    uploaded_files = st.file_uploader("Upload a document to add it to the Azure Storage Account", type=['pdf','jpeg','jpg','png', 'txt'], accept_multiple_files=True)

    if st.session_state['INDEX'] != 'SELECT':
        if uploaded_files is not None:
            for up in uploaded_files:
                # To read file as bytes:
                bytes_data = up.getvalue()

                if st.session_state.get('filename', '') != up.name:
                    # Upload a new file
                    upload_file(bytes_data, up.name,index=st.session_state['INDEX'])
                    if up.name.endswith('.txt'):
                        llm_helper.blob_client.upsert_blob_metadata(st.session_state['INDEX'], up.name, {'converted': "true", 'index': st.session_state['INDEX'], 'url':"NONE"}) 
                    else:
                        llm_helper.blob_client.upsert_blob_metadata(st.session_state['INDEX'], up.name, {'converted': "false", 'index': st.session_state['INDEX'], 'url':"NONE"})

        col1, col2, col3 = st.columns([2,2,2])
        with col3:
            st.button("Convert all files and add embeddings", on_click=remote_convert_files_and_add_embeddings)

    else:
        st.warning("Please select an index first.")
        
        
    if st.button("Run Scraper", disabled = False):
        try:
            scrapdata.main() # calling the main function in scrapdata.py
            st.success("Scraper ran successfully.")
        except Exception as e:
            st.error(f"Error running the scraper: {e}")

    with st.expander("Add a single document to the knowledge base", expanded=True):
        uploaded_file = st.file_uploader("Upload a document to add it to the knowledge base", type=['pdf','jpeg','jpg','png', 'txt'])
        if uploaded_file is not None:
            # To read file as bytes:
            bytes_data = uploaded_file.getvalue()

            if st.session_state.get('filename', '') != uploaded_file.name:
                upload_file(bytes_data, uploaded_file.name, index = st.session_state['INDEX'])
                converted_filename = ''
                if uploaded_file.name.endswith('.txt'):
                    # Add the text to the embeddings
                    llm_helper.add_embeddings_lc(st.session_state['file_url'], index = st.session_state['INDEX'], citation_URL= "NONE" )

                else:
                    # Get OCR with Layout API and then add embeddigns
                    converted_filename = llm_helper.convert_file_and_add_embeddings(st.session_state['file_url'], st.session_state['filename'], st.session_state['INDEX'], citation_URL = "NONE", meta_filename="NONE")
                
                llm_helper.blob_client.upsert_blob_metadata( st.session_state['INDEX'], uploaded_file.name, {'converted': 'true', 'embeddings_added': 'true', 'index': st.session_state['INDEX']}) 
                st.success(f"File {uploaded_file.name} embeddings added to the knowledge base.")
            

            
    with st.expander("View documents in the knowledge base", expanded=True):
            files_data = llm_helper.blob_client.get_all_files()
            df = pd.DataFrame(files_data)

            st.dataframe(df, use_container_width=True )

except Exception as e:
    st.error(traceback.format_exc())
    