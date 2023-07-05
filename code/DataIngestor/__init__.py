import datetime
import logging
import requests
import mimetypes
import chardet
import os
import json

import azure.functions as func
import base64 as b64
from utilities.helper import LLMHelper
from urllib.parse import quote

llm_helper = LLMHelper()

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


def encode_url(url):
    return quote(url, safe='/:')

def encode_colon_in_url(url):
    # Find the first occurrence of : in the URL
    colon_index = url.find(':')
    
    # If the colon is not found or it is found immediately after the scheme, return the URL unchanged
    if colon_index == -1 or url[colon_index:colon_index+3] == '://':
        return url
    
    # Otherwise, replace all occurrences of : with %3A
    return url.replace(':', '%3A')


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
        page_url = encode_colon_in_url(page_url)
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
                url = url + "?path=" + encode_url(page_content['path']) + "&includeContent=true&api-version=7.0"
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
                        print(page['remoteUrl'])

                        bytesdata = final_content.encode('utf-8')
                    
                        blob_url = llm_helper.blob_client.upload_file(bytes_data=bytesdata, file_name= file_name , content_type='text/plain', index= 'ado')
                        
                        llm_helper.blob_client.upsert_blob_metadata('ado', file_name, {'URL': page['remoteUrl'], 'converted': "true", 'index': 'ado','filename':file_name_meta})
                    
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


def main(mytimer: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function ran at %s', utc_timestamp)    

    llm_helper = LLMHelper()  

    # Place the tokens here
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
    for proj, header in zip(projects, headers):       

        try:
            base_url = f"https://dev.azure.com/{proj}/_apis/projects"
            response = requests.get(base_url, headers=header)
            data = response.json()

            for project in data['value']:
                project_name = project['name']
                project_id = project['id']
                base_url = f"https://dev.azure.com/{proj}/{project_id}/_apis/wiki/wikis?api-version=7.0"
                base_url = encode_colon_in_url(base_url)
                response = requests.get(base_url, headers=header)
                wiki_data = response.json()

                for wiki in wiki_data['value']:
                    wiki_id = wiki['id']
                    wiki_name = wiki['name']
                    if(wiki_name != 'DTP Solutions.wiki' and proj != 'CarbonNetwork'):
                        continue
                    pages_url = f"https://dev.azure.com/{proj}/{project_id}/_apis/wiki/wikis/{wiki_id}/pages?api-version=7.0&includeContent=true&recursionLevel=Full"
                    pages_url = encode_colon_in_url(pages_url)
                    pages_response = requests.get(pages_url, headers=header)

                    if pages_response.status_code == 200:
                        pages_data = pages_response.json()
                        process_page(pages_data, project_name, wiki_id, header,wiki_name)
                    else:
                        print(f"Failed to fetch wiki pages for in project {project_name}. Status code: {pages_response.status_code}")
        except Exception as e:
            print(f"Unexpected error in main loop: {str(e)}")
    
    #====================================================================================================
    # Fetching Readme files from ADO for all Sustainability projects
    #====================================================================================================

    # Fetch Readme files from Azure DevOps (ADO) for all Sustainability projects
    for project, header in zip(projects, headers):
        try:
            # Define base url for project
            project_url = f"https://dev.azure.com/{project}/_apis/projects"

            # Get project data
            project_response = requests.get(project_url, headers=header)
            project_data = project_response.json()

            # Traverse through each project
            for proj in project_data['value']:
                # Define repositories URL for the project
                repo_url = f"https://dev.azure.com/{project}/{proj['id']}/_apis/git/repositories"

                # Get repository data
                repo_response = requests.get(repo_url, headers=header)
                repo_data = repo_response.json()

                # Traverse through each repository
                for repo in repo_data['value']:
                    # Only consider the repository if 'sust' is part of its name
                    if 'sust' not in repo['name'].lower():
                        continue

                    # Define readme URL for the repository
                    readme_url = f"https://dev.azure.com/{project}/{proj['name']}/_apis/git/repositories/{repo['id']}/items?path=/README.md&includeContentMetadata=true&versionDescriptor.versionType=branch"

                    # Get README file
                    readme_response = requests.get(readme_url, headers=header)

                    # Check if the request was successful
                    if readme_response.status_code == 200:
                        # Define file name
                        file_name = f"{project}/{proj['name']}/_git/{repo['name']}?path=/README.md"
                        # Replace special characters and file extension
                        file_name = file_name.replace('/', '_').replace(':', '_').replace('?', '_').replace('.md', '')
                        file_name = f"ReadmeFiles/{file_name}.txt"

                        readme_header = "Readme file for " + repo['name'] + " in project " + proj['name'] + "\n\n "
                        readme_content = readme_header + readme_response.content.decode('utf-8', errors='replace')

                        URL_for_file = f"https://dev.azure.com/{project}/{proj['name']}/_git/{repo['name']}?path=%2FREADME.md"
                        
                        file_name_meta = f"{project}/{proj['name']}/_git/{repo['name']}?path=%2FREADME.md"

                        bytes_data = readme_content.encode('utf-8')
                        blob_url = llm_helper.blob_client.upload_file(bytes_data=bytes_data, file_name=file_name,content_type='text/plain',index ='ado')
                        llm_helper.blob_client.upsert_blob_metadata('ado', file_name, {'URL': URL_for_file, 'converted':"true", 'index':'ado','filename':file_name_meta})

        except Exception as e:
            logging.error(f"Error occurred for project {project}: {e}")
            
    #====================================================================================================
    # Scrap Pull Requests from ADO for all Sustainability projects
    #====================================================================================================

    remote_convert_files_and_add_embeddings()