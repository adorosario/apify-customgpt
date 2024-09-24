import json
import os
import time
import argparse
from urllib.parse import urlparse
import re
from datetime import datetime

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.utilities import ApifyWrapper
from customgpt_client import CustomGPT
from customgpt_client.types import File
from requests.exceptions import HTTPError

def generate_project_name(wp_url):
    # Extract domain name from the URL
    domain = urlparse(wp_url).netloc
    
    # Remove 'www.' if present
    domain = re.sub(r'^www\.', '', domain)
    
    # Generate timestamp
    timestamp = datetime.now().strftime("%Y%m%d:%H%M%S")
    
    # Combine domain and timestamp
    project_name = f"{domain} - {timestamp}"
    
    return project_name

def transfer_to_customgpt(project_name, docs, api_key):
    CustomGPT.api_key = api_key
    
    project = CustomGPT.Project.create(project_name=project_name)
    if project.status_code != 201:
        print(f"Failed to create project. Status code: {project.status_code}")
        return None
    
    project_id = project.parsed.data.id
    
    for idx, doc in enumerate(docs):
        file_name = f"document_{idx}.doc"
        file_content = doc.page_content
        file_metadata = doc.metadata

        file_obj = File(file_name=file_name, payload=file_content)
        
        add_source = CustomGPT.Source.create(project_id=project_id, file=file_obj)
        if add_source.status_code != 201:
            print(f"Failed to upload file {file_name}. Status code: {add_source.status_code}")
            continue
        
        page_id = add_source.parsed.data.pages[0].id
        update_metadata = CustomGPT.PageMetadata.update(
            project_id, 
            page_id, 
            url=file_metadata["url"],
            title=file_metadata["title"]
        )
        if update_metadata.status_code != 200:
            print(f"""Failed to update metadata for project_id={project_id}, page_id={page_id}, url={file_metadata["url"]}, title={file_metadata["title"]}. Status code: {update_metadata.status_code}. response={update_metadata}""")
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Data transferred to CustomGPT project: {project_name}")
    return project_id

def check_indexing_status(project_id, api_key):
    CustomGPT.api_key = api_key
    page_n = 1 # Pagination
    all_documents_indexed = False
    
    while not all_documents_indexed:
        documents_response = CustomGPT.Page.get(project_id=project_id, page=page_n)
        if documents_response.status_code != 200:
            print(f"Failed to retrieve documents. Status code: {documents_response.status_code}")
            return False
        
        documents_data = documents_response.parsed.data.pages
        documents = documents_data.data
        
        page_n_completed = True
        for doc in documents:
            if doc.index_status == "queued":
                print(f"Documents queued in indexing queue -- sleeping 5 seconds ...")
                time.sleep(5)
                page_n_completed = False
                break
        
        # At this point, all documents found in paginated responses until page_n have been indexed
        if page_n_completed:
            if documents_data.next_page_url:
                page_n += 1
            else:
                all_documents_indexed = True 
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] All documents indexed successfully ...")
    return True

def query_customgpt(project_id, prompt, api_key):
    CustomGPT.api_key = api_key
    
    # Create a conversation before sending a message to the chatbot
    project_conversation = CustomGPT.Conversation.create(
        project_id=project_id, name="My First Conversation"
    )

    # Check if the conversation creation was successful
    if project_conversation.status_code != 201:
        raise HTTPError(
            f"Failed to create conversation. Status code: {project_conversation.status_code}"
        )

    # Get the session id for the conversation
    session_id = project_conversation.parsed.data.session_id

    response = CustomGPT.Conversation.send(
        project_id=project_id, session_id=session_id, prompt=prompt, stream=False
    )

    # Check if the conversation response was successful
    if response.status_code != 200:
        raise HTTPError(f"Failed to send prompt. Status code: {response.status_code}, response={response}")

    # Format and display the result in a more readable way
    print(f"""
    user: {response.parsed.data.user_query}
    assistant: {response.parsed.data.openai_response}
    """)

def main(starting_url, user_prompt):
    # Load environment variables from .env file
    load_dotenv()

    # Create an instance of the ApifyWrapper class.
    apify = ApifyWrapper(apify_api_token=os.getenv("APIFY_API_TOKEN"))

    # Call actor to scrape the website content.
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting apify actor to scrape: {starting_url} ...")
    loader = apify.call_actor(
        actor_id="apify/website-content-crawler",
        run_input={"startUrls": [{"url": starting_url}], "maxCrawlDepth": 20},
        dataset_mapping_function=lambda item: Document(
            page_content=item["text"] or "",
            metadata={
                "url": item["url"],
                "title": item.get("metadata", {}).get("title", ""),
                "description": item.get("metadata", {}).get("description", "")
            }
        ),
    )

    # Load the documents
    docs = loader.load()

    # Create the CustomGPT.ai project and upload all the documents to it. 
    CUSTOMGPT_API_KEY = os.getenv("CUSTOMGPT_API_KEY")
    total_documents = len(docs)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Beginning sync of {total_documents} documents to CustomGPT ...")
    customgpt_project_name = generate_project_name(starting_url)
    project_id = transfer_to_customgpt(customgpt_project_name, docs, CUSTOMGPT_API_KEY)

    if project_id:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] All documents uploaded. Checking CustomGPT indexing status ...")
        indexing_successful = check_indexing_status(project_id, CUSTOMGPT_API_KEY)
        if indexing_successful:
            print(f"""[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ### :tada: Data Successfully Synced!
            
            Your Apify scraped content has been successfully synced to CustomGPT and indexed.
            
            You can now also chat with your data here: https://app.customgpt.ai/projects/{project_id}/ask-me-anything
            """)
    else:
        print("No data fetched. Please check your inputs and try again.")

    # Let's query the newly created CustomGPT project
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Trying the prompt via API ...")
    query_customgpt(project_id=project_id, prompt=user_prompt, api_key=CUSTOMGPT_API_KEY)

if __name__ == "__main__":
    # Create an argument parser to accept --starting-url and --prompt arguments
    parser = argparse.ArgumentParser(
        description="Build an AI agent using Apify and CustomGPT"
    )
    parser.add_argument(
        "--starting-url", required=True, help="The URL to start scraping"
    )
    parser.add_argument(
        "--prompt", required=True, help="The prompt or question to send to the chatbot"
    )

    # Parse the arguments
    args = parser.parse_args()

    # Call the main function with the starting URL and prompt
    main(args.starting_url, args.prompt)
