import logging, json, os
import azure.functions as func
from azure.storage.queue import QueueClient, BinaryBase64EncodePolicy
from utilities.helper import LLMHelper

queue_name = os.environ['QUEUE_NAME']

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Requested to start processing all documents received')
    # Set up LLM Helper
    llm_helper = LLMHelper()
    # Get all files from Blob Storage
    files_data = llm_helper.blob_client.get_all_files() # Get all files from Blob Storage
    
    #
    files_data = list(filter(lambda x : not x['embeddings_added'], files_data)) 
    files_data = list(map(lambda x: {'filename': x['filename'], 'index': x['index'], 'url': x['url'], 'meta_filename':x['meta_filename']}, files_data))
    
    queue_client = QueueClient.from_connection_string(llm_helper.blob_client.connect_str, queue_name, message_encode_policy=BinaryBase64EncodePolicy())
    # Send a message to the queue for each file
    for fd in files_data:
        queue_client.send_message(json.dumps(fd).encode('utf-8'))
        
    print("Conversion started successfully.")
 
    return func.HttpResponse(f"Conversion started successfully for {len(files_data)} documents.", status_code=200)