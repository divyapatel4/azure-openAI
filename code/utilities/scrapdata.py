import datetime
import logging
import requests
import mimetypes
import chardet
import os
import json
from azure.storage.queue import QueueClient, BinaryBase64EncodePolicy
import azure.functions as func
import base64 as b64
from utilities.helper import LLMHelper
from urllib.parse import quote

llm_helper = LLMHelper()

queue_name = "doc-processing"

def encode_url(url):
    return quote(url, safe='/:')

def remote_convert_files_and_add_embeddings():
    url = os.getenv('CONVERT_ADD_EMBEDDINGS_URL')
    try:
        response = requests.post(url)
        if response.status_code == 200:
            # log the response as function app triggered for generating queue
            logging.info(f"{response.text}\n Queue Generator Triggered Successfully.")
        else:
            logging.error(f"Error: {response.text}")
    except Exception as e:
        logging.error(e)

def sanitize_file_name(file_name):
    char_mapping = {
        "?": "_",
        ":": "_",
        "<": "_",
        ">": "_",
        "|": "_",
        "*": "_",
        "/": "_",
        "\\": "_",
        "\"": "_"
    }

    for char, replacement in char_mapping.items():
        file_name = file_name.replace(char, replacement)
        
    if (len(file_name) > 250):
        # Retain last 250 characters
        file_name = file_name[-250:] 
    return file_name


def process_page(page, project_name, wiki_id, headers,wiki_name):
    try:
        page_url = page['url']
        page_response = requests.get(page_url, headers=headers)

        if page_response.status_code == 200:
            try:
                page_content = json.loads(page_response.text)  # Could raise JSONDecodeError
            except:
                try: 
                    page_content = json.loads(page_response.content.decode('utf-8-sig', errors= 'replace') )  
                except Exception as e:
                    print(f"Failed to parse JSON for wiki page for {wiki_id} in project {project_name}. Error: {str(e)}")
                    return
            
            if(page_content['path'] != '/'):
                url = page_content['url'] 
                url = url +  "?path=" + encode_url(page_content['path']) + "&includeContent=true&api-version=7.0"
                file_name = wiki_name + page_content['path']
                
                file_name_meta = file_name
                
                file_name = sanitize_file_name(file_name)
                content = requests.get(url, headers=headers)

                try:
                    content = content.json()
                except Exception as e:
                    print(f"Failed to parse JSON for wiki page content for {wiki_id} in project {project_name}. Error: {str(e)}")
                    return

                try:
                    if(content['content'] is not None and content['content'].strip() != ""):
                        file_name = file_name + '.txt'
                        filepath = project_name + '/' + file_name 
                        filepath = filepath.replace('.txt', '')
                        filepathcontext = wiki_name + page_content['path']
                        # convert project/file1/file2/ ... to this file can be found in project/file1/file2/ ... and title is the last word after last /
                        titleforthisfile = filepathcontext.split('/')[-1]
                        header_for_filepath = "This file can be found in " + filepathcontext + "\n\n"
                        header_for_file = "Project : " + project_name + "\n" + "Path : " + header_for_filepath + "\n" + "Title of this file : " + titleforthisfile + "\n\n"
                        
                        final_content = header_for_file + content['content'] 
                        
                        # if content['content'] is just blanks spaces or empty string, then don't upload it 

                        bytesdata = final_content.encode('utf-8')
                    
                        blob_url = llm_helper.blob_client.upload_file(bytes_data=bytesdata, file_name= file_name , content_type='text/plain', index= 'ado')
                        
                        llm_helper.blob_client.upsert_blob_metadata('ado', file_name, {'url': page['remoteUrl'], 'converted': "true", 'index': 'ado','filename':file_name_meta})
                    
                        print(f"Successfully fetched wiki page for {wiki_id} in project {project_name}.")
                except Exception as e:
                    print(f"Failed to fetch/write content for wiki page for {wiki_id} in project {project_name}. Error: {str(e)}")
        else:
            print(f"Failed to fetch wiki page for {wiki_id} in project {project_name}. Status code: {page_response.status_code}")

        if 'subPages' in page:
            for subpage in page['subPages']:
                process_page(subpage, project_name, wiki_id, headers,wiki_name)
    except Exception as e:
        print(f"Unexpected error in process_page: {str(e)}")


def main():
    llm_helper = LLMHelper()  
    #====================================================================================================
    # Personal Access Tokens
    tokens = [
        'je5eweq6ndtcade7suacgyd3blchrtbc4vyrxudfsrrmqj67ytka', 
        'fnchsdtwi2awgxhi4i2p6mzx7mfej4inznp652avlqzdb6s5gv7q', 
        'hcpyus63vw7afgep2c7fzerip35ed4upm5jgrswmstekbmqqncpa'
    ]

    # Convert the tokens to base64 encoded strings
    tokens = [b64.b64encode(bytes(':'+token, 'utf-8')).decode('utf-8') for token in tokens]

    # Create authorization headers for each token
    headers = [{'Authorization': f'Basic {token}'} for token in tokens]

    # Azure DevOps projects we are interested in
    projects = ['dynamicscrm', 'msazure', 'CarbonNetwork']


    #====================================================================================================
    # Fetching WikiFiles from ADO for all Sustainability projects
    #====================================================================================================
    print("Fetching wiki pages...")
        
    for proj, header in zip(projects, headers):       

        try:
            base_url = f"https://dev.azure.com/{proj}/_apis/projects"
            response = requests.get(base_url, headers=header)
            data = response.json()

            for project in data['value']:
                project_name = project['name']
                project_id = project['id']
                base_url = f"https://dev.azure.com/{proj}/{project_id}/_apis/wiki/wikis?api-version=7.0"
                response = requests.get(base_url, headers=header)
                wiki_data = response.json()

                for wiki in wiki_data['value']:
                    wiki_id = wiki['id']
                    wiki_name = wiki['name']
                    if(wiki_name != 'DTP Solutions.wiki' and proj != 'CarbonNetwork'):
                        continue
                    pages_url = f"https://dev.azure.com/{proj}/{project_id}/_apis/wiki/wikis/{wiki_id}/pages?api-version=7.0&includeContent=true&recursionLevel=Full"
                    pages_response = requests.get(pages_url, headers=header)

                    if pages_response.status_code == 200:
                        pages_data = pages_response.json()
                        process_page(pages_data, project_name, wiki_id, header,wiki_name)
                    else:
                        print(f"Failed to fetch wiki pages for in project {project_name}. Status code: {pages_response.status_code}")
        except Exception as e:
            print(f"Unexpected error in main loop: {str(e)}")
    
    # #====================================================================================================
    # # Fetching Readme files from ADO for all Sustainability projects
    # #====================================================================================================
    # llm_helper = LLMHelper()
    # # Personal Access Tokens
    # personal_access_tokens = [
    #     'je5eweq6ndtcade7suacgyd3blchrtbc4vyrxudfsrrmqj67ytka', 
    #     'fnchsdtwi2awgxhi4i2p6mzx7mfej4inznp652avlqzdb6s5gv7q', 
    #     'hcpyus63vw7afgep2c7fzerip35ed4upm5jgrswmstekbmqqncpa'
    # ]

    # # Convert the tokens to base64 encoded strings
    # encoded_tokens = [b64.b64encode(bytes(':'+token, 'utf-8')).decode('utf-8') for token in personal_access_tokens]

    # # Create authorization headers for each token
    # auth_headers = [{'Authorization': f'Basic {token}'} for token in encoded_tokens]

    # # Azure DevOps projects we are interested in
    # target_projects = ['dynamicscrm', 'msazure', 'CarbonNetwork']

    # # Fetch Readme files from Azure DevOps (ADO) for all Sustainability projects
    # for project, header in zip(target_projects, auth_headers):
    #     try:
    #         # Define base url for project
    #         project_url = f"https://dev.azure.com/{project}/_apis/projects"

    #         # Get project data
    #         project_response = requests.get(project_url, headers=header)
    #         project_data = project_response.json()

    #         # Traverse through each project
    #         for proj in project_data['value']:
    #             # Define repositories URL for the project
    #             repo_url = f"https://dev.azure.com/{project}/{proj['id']}/_apis/git/repositories"

    #             # Get repository data
    #             repo_response = requests.get(repo_url, headers=header)
    #             repo_data = repo_response.json()

    #             # Traverse through each repository
    #             for repo in repo_data['value']:
    #                 # Only consider the repository if 'sust' is part of its name
    #                 if 'sust' not in repo['name'].lower():
    #                     continue

    #                 # Define readme URL for the repository
    #                 readme_url = f"https://dev.azure.com/{project}/{proj['name']}/_apis/git/repositories/{repo['id']}/items?path=/README.md&includeContentMetadata=true&versionDescriptor.versionType=branch"

    #                 # Get README file
    #                 readme_response = requests.get(readme_url, headers=header)

    #                 # Check if the request was successful
    #                 if readme_response.status_code == 200:
    #                     # Define file name
    #                     file_name = f"{project}/{proj['name']}/_git/{repo['name']}?path=/README.md"
    #                     # Replace special characters and file extension
    #                     file_name = file_name.replace('/', '_').replace(':', '_').replace('?', '_').replace('.md', '')
    #                     file_name = f"{file_name}.txt"

    #                     readme_header = "Readme file for " + repo['name'] + " in project " + proj['name'] + "\n\n "
    #                     readme_content = readme_header + readme_response.content.decode('utf-8', errors='replace')

    #                     URL_for_file = f"https://dev.azure.com/{project}/{proj['name']}/_git/{repo['name']}?path=%2FREADME.md"
    #                     print(URL_for_file)
                        
    #                     file_name_meta = f"{project}/{proj['name']}/_git/{repo['name']}?path=%2FREADME.md"

    #                     bytes_data = readme_content.encode('utf-8')
    #                     blob_url = llm_helper.blob_client.upload_file(bytes_data=bytes_data, file_name=file_name,content_type='text/plain',index ='ado')
    #                     llm_helper.blob_client.upsert_blob_metadata('ado', file_name, {'url': URL_for_file, 'converted':"true", 'index':'ado','filename':file_name_meta})

    #     except Exception as e:
    #         logging.error(f"Error occurred for project {project}: {e}")


    # remote_convert_files_and_add_embeddings()
    # Set up LLM Helper
    # llm_helper = LLMHelper()
    # # Get all files from Blob Storage
    # files_data = llm_helper.blob_client.get_all_files() # Get all files from Blob Storage
    
    # # files_data = list(filter(lambda x : not x['embeddings_added'], files_data)) 
    # files_data = list(map(lambda x: {'filename': x['filename'], 'index': x['index'], 'url': x['url'], 'meta_filename':x['meta_filename']}, files_data))

    # for file in files_data:
    #     file_name = file['filename']
    #     file_sas = llm_helper.blob_client.get_blob_sas(file_name)
    #     file_index = file['index']
    
    #     citationURL = file['url']
    #     meta_filename = file['meta_filename']
    #     # Check the file extension
    #     if file_name.endswith('.txt'):
    #         # Add the text to the embeddings
    #         llm_helper.add_embeddings_lc(file_sas,index=file_index,citation_URL= citationURL,file_name=meta_filename)
    #         print("Text file added to embeddings: ")
    #         print(file)
            
    #     else:
    #         # Get OCR with Layout API and then add embeddigns
    #         llm_helper.convert_file_and_add_embeddings( file_sas , file_name, index=file_index,citation_URL = citationURL,meta_filename=meta_filename)
            
        
    #     # In filename index is already included so only include term after last / in filename
    #     file_name = file_name.split('/')[-1]
    #     llm_helper.blob_client.upsert_blob_metadata( file_index, file_name, {'embeddings_added': 'true', 'converted': 'true', 'index': file_index})
    
    # # Set of programming languages extensions we are interested in
    # extensions = {'.py', '.java', '.c', '.cpp', '.cs', '.js', '.jsx', '.ts', '.tsx', '.php', '.rb', '.go', '.rs', '.swift','.md'}

    # # Fetch code files from Azure DevOps (ADO) for all Sustainability projects
    # for project, header in zip(projects, headers):
    #     try:
    #         # Define base url for project
    #         project_url = f"https://dev.azure.com/{project}/_apis/projects"

    #         # Get project data
    #         project_response = requests.get(project_url, headers=header)
    #         project_data = project_response.json()

    #         # Traverse through each project
    #         for proj in project_data['value']:
    #             print(proj['name'])
    #             # Define repositories URL for the project
    #             repo_url = f"https://dev.azure.com/{project}/{proj['id']}/_apis/git/repositories"

    #             # Get repository data
    #             repo_response = requests.get(repo_url, headers=header)
    #             repo_data = repo_response.json()

    #             # Traverse through each repository
    #             for repo in repo_data['value']:
    #                 # Define items URL for the repository
    #                 if 'sust' in repo['name'].lower():
    #                     print("Repo name: " + repo['name'])
    #                     items_url = f"https://dev.azure.com/{project}/{proj['name']}/_apis/git/repositories/{repo['id']}/items?scopePath=/&recursionLevel=Full"

    #                     # Get items data
    #                     items_response = requests.get(items_url, headers=header)
    #                     items_data = items_response.json()

    #                     # Traverse through each item
    #                     for item in items_data['value']:
    #                         if item['gitObjectType'] == 'blob' and not any(part.startswith('.') for part in item['path'].split('/')): # If it is a code file and does not start with .
    #                             file_extension = os.path.splitext(item['path'])[1]
    #                             if file_extension in extensions:
    #                                 file_url = f"https://dev.azure.com/{project}/{proj['name']}/_apis/git/repositories/{repo['id']}/items?path={item['path']}&includeContent=true"
    #                                 file_response = requests.get(file_url, headers=header)
    #                                 file_content = file_response.content.decode('utf-8', errors='replace')

    #                                 # Define file name
    #                                 file_name = f"{project}/{proj['name']}/_git/{repo['name']}?path={item['path']}"
                                    
    #                                 # Replace special characters and file extension
    #                                 file_name = file_name.replace('/', '_').replace(':', '_').replace('?', '_')
    #                                 file_name = f"{file_name}.txt"

    #                                 # Convert content to bytes and upload to blob
    #                                 bytes_data = file_content.encode('utf-8')
    #                                 blob_url = llm_helper.blob_client.upload_file(bytes_data=bytes_data, file_name=file_name,content_type='text/plain',index ='code')

    #                                 # Define URL for metadata
    #                                 URL_for_file = f"https://dev.azure.com/{project}/{proj['name']}/_git/{repo['name']}?path={item['path']}"
                                    
    #                                 # Update blob metadata
    #                                 llm_helper.blob_client.upsert_blob_metadata('code', file_name, {'URL': URL_for_file, 'converted':"true", 'index':'code'})

    #     except Exception as e:
    #         logging.error(f"Error occurred for project {project}: {e}")






# ================================= To Update mass metadata =================================

    # llm_helper = LLMHelper()
    # # Get all files from Blob Storage
    # files_data = llm_helper.blob_client.get_all_files() # Get all files from Blob Storage
    
    # for file in files_data:
        
    #     file_name = file['filename']
    #     print(file_name)
    #     file_index = file_name.split('/')[0]
    #     if file_index !='smes':
    #         continue
        
    #     # In filename index is already included so only include term after last / in filename
    #     file_name = file_name.split('/')[-1]
    #     llm_helper.blob_client.upsert_blob_metadata( file_index, file_name, {'embeddings_added': 'false', 'converted': 'true', 'index': file_index})
    
    # ========================== To add all to queue =================================
    # Get all files from Blob Storage
    # files_data = llm_helper.blob_client.get_all_files() # Get all files from Blob Storage
    
    # #
    # # files_data = list(filter(lambda x : not x['embeddings_added'], files_data)) 
    # files_data = list(map(lambda x: {'filename': x['filename'], 'index': x['index'], 'url': x['url'], 'meta_filename':x['meta_filename']}, files_data))
    
    # queue_client = QueueClient.from_connection_string(llm_helper.blob_client.connect_str, queue_name, message_encode_policy=BinaryBase64EncodePolicy())
    # # Send a message to the queue for each file
    # for fd in files_data:
    #     queue_client.send_message(json.dumps(fd).encode('utf-8'))
        
        
    remote_convert_files_and_add_embeddings()
    
    print("Conversion started successfully.")