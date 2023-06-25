import logging, json
import azure.functions as func
from utilities.helper import LLMHelper

def main(msg: func.QueueMessage) -> None:
    logging.info('Python queue trigger function processed a queue item: %s', msg.get_body().decode('utf-8'))

    # Set up LLM Helper
    llm_helper = LLMHelper()
    # Get the file name from the message
    file_name = json.loads(msg.get_body().decode('utf-8'))['filename']
    file_index = json.loads(msg.get_body().decode('utf-8'))['index']
    citationURL = json.loads(msg.get_body().decode('utf-8'))['url']
    meta_filename = json.loads(msg.get_body().decode('utf-8'))['meta_filename']
    # Generate the SAS URL for the file
    file_sas = llm_helper.blob_client.get_blob_sas(file_name)

    # Check the file extension
    if file_name.endswith('.txt'):
        # Add the text to the embeddings
        llm_helper.add_embeddings_lc(file_sas,index=file_index,citation_URL= citationURL,file_name=meta_filename)
    else:
        # Get OCR with Layout API and then add embeddigns
        llm_helper.convert_file_and_add_embeddings( file_sas , file_name, index=file_index,citation_URL = citationURL,meta_filename=meta_filename)
        
    
    # In filename index is already included so only include term after last / in filename
    file_name = file_name.split('/')[-1]
    llm_helper.blob_client.upsert_blob_metadata( file_index, file_name, {'embeddings_added': 'true', 'converted': 'true', 'index': file_index})
