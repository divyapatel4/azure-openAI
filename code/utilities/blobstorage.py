import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, generate_blob_sas, generate_container_sas, ContentSettings
from dotenv import load_dotenv
from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.models import Entity
from datetime import datetime 

class AzureBlobStorageClient:
    def __init__(self, account_name: str = None, account_key: str = None, container_name: str = None, table_name: str = "logs"):

        load_dotenv()

        self.account_name : str = account_name if account_name else os.getenv('BLOB_ACCOUNT_NAME')
        self.account_key : str = account_key if account_key else os.getenv('BLOB_ACCOUNT_KEY')
        self.connect_str : str = f"DefaultEndpointsProtocol=https;AccountName={self.account_name};AccountKey={self.account_key};EndpointSuffix=core.windows.net"
        self.container_name : str = container_name if container_name else os.getenv('BLOB_CONTAINER_NAME')
        self.blob_service_client : BlobServiceClient = BlobServiceClient.from_connection_string(self.connect_str)
        
        self.table_name: str = table_name if table_name else os.getenv('TABLE_NAME')
        self.table_service: TableService = TableService(connection_string=self.connect_str)
        self.create_table_if_not_exists()


    def upload_file(self, bytes_data, file_name, content_type='application/pdf',index = None):
        # write data in a folder inside container with name converted
        if index is not None:
            file_name = f"{index}/{file_name}"      
        
        # Create a blob client using the local file name as the name for the blob
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=file_name)
        # Upload the created file
        blob_client.upload_blob(bytes_data, overwrite=True, content_settings=ContentSettings(content_type=content_type))
        # Generate a SAS URL to the blob and return it
        return blob_client.url + '?' + generate_blob_sas(self.account_name, self.container_name, file_name,account_key=self.account_key,  permission="r", expiry=datetime.utcnow() + timedelta(hours=3))

    def get_all_files(self):
        # Get all files in the container from Azure Blob Storage
        container_client = self.blob_service_client.get_container_client(self.container_name)
        blob_list = container_client.list_blobs(include='metadata')
        # sas = generate_blob_sas(account_name, container_name, blob.name,account_key=account_key,  permission="r", expiry=datetime.utcnow() + timedelta(hours=3))
        sas = generate_container_sas(self.account_name, self.container_name,account_key=self.account_key,  permission="r", expiry=datetime.utcnow() + timedelta(hours=3))
        files = []
        converted_files = {}
        for blob in blob_list:
            if not blob.name.startswith('converted/'):
                tempindex = blob.name.split('/')[0]
                files.append({
                    "filename" : blob.name,
                    # If metadata is present for converted files then that value else false
                    "converted": blob.metadata.get('converted', 'false') == 'true' if blob.metadata else False,
                    "embeddings_added": blob.metadata.get('embeddings_added', 'false') == 'true' if blob.metadata else False,
                    "index": blob.metadata.get('index', '') if blob.metadata else tempindex,
                    "url": blob.metadata.get('url', '') if blob.metadata else 'NONE',
                    "meta_filename": blob.metadata.get('filename', '') if blob.metadata else 'NONE',
                    })
            else:
                converted_files[blob.name] = f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob.name}?{sas}"

        for file in files:
            converted_filename = file.pop('converted_filename', '')
            if converted_filename in converted_files:
                file['converted'] = True
        return files

    def upsert_blob_metadata(self, index, file_name, metadata):
        try:
            # Include index in the blob name if it is provided
            blob_name = f'{index}/{file_name}' if index else file_name

            # Create blob client
            blob_client = BlobServiceClient.from_connection_string(self.connect_str).get_blob_client(container=self.container_name, blob=blob_name)

            # Check if the blob exists
            if blob_client.exists():
                # Read metadata from the blob
                blob_metadata = blob_client.get_blob_properties().metadata

                # Update metadata
                blob_metadata.update(metadata)
                # Add metadata to the blob
                blob_client.set_blob_metadata(metadata= blob_metadata)
            else:
                print(f'Blob {blob_name} does not exist.')
        except Exception as e:
            print(f'An error occurred: {str(e)}')
            
    def get_blob_metadata(self, file_name,index = None):
        try:
            # Include index in the blob name if it is provided
            blob_name = f'{index}/{file_name}' if index else file_name

            # Create blob client
            blob_client = BlobServiceClient.from_connection_string(self.connect_str).get_blob_client(container=self.container_name, blob=blob_name)

            # Check if the blob exists
            if blob_client.exists():
                # Read metadata from the blob
                blob_metadata = blob_client.get_blob_properties().metadata

                # Return the metadata
                return blob_metadata
            else:
                print(f'Blob {blob_name} does not exist.')
                return None
            
            
        except Exception as e:
            print(f'An error occurred: {str(e)}')
            return None


    def get_container_sas(self):
        # Generate a SAS URL to the container and return it
        return "?" + generate_container_sas(account_name= self.account_name, container_name= self.container_name,account_key=self.account_key,  permission="r", expiry=datetime.utcnow() + timedelta(hours=1))

    def get_blob_sas(self, file_name):
        # Generate a SAS URL to the blob and return it
        return f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{file_name}" + "?" + generate_blob_sas(account_name= self.account_name, container_name=self.container_name, blob_name= file_name, account_key= self.account_key, permission='r', expiry=datetime.utcnow() + timedelta(hours=1))
    
    
    def create_table_if_not_exists(self):
        # Check if the table already exists
        if not self.table_service.exists(self.table_name): # corrected here
            # If not, create it
            self.table_service.create_table(self.table_name)


   
    def add_to_table(self, index:str, question: str, answer: str, temperature: float):
        # Create a timestamp to use as a unique row key
        timestamp = datetime.utcnow().isoformat()

        # Define the entity
        task = {'PartitionKey': 'search', 'RowKey': timestamp,'index':index, 'question': question, 'answer': answer, 'temperature': temperature}

        # Insert the entity into the table
        self.table_service.insert_entity(self.table_name, task)