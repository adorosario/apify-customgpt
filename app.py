import streamlit as st
import os
import time
from datetime import datetime
from urllib.parse import urlparse
import re

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.utilities import ApifyWrapper
from customgpt_client import CustomGPT
from customgpt_client.types import File
from requests.exceptions import HTTPError

# Load environment variables
load_dotenv()

def generate_project_name(wp_url):
    domain = urlparse(wp_url).netloc
    domain = re.sub(r'^www\.', '', domain)
    timestamp = datetime.now().strftime("%Y%m%d:%H%M%S")
    return f"{domain} - {timestamp}"

def transfer_to_customgpt(project_name, docs, api_key):
    CustomGPT.api_key = api_key
    
    project = CustomGPT.Project.create(project_name=project_name)
    if project.status_code != 201:
        st.error(f"Failed to create project. Status code: {project.status_code}")
        return None
    
    project_id = project.parsed.data.id
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    for idx, doc in enumerate(docs):
        file_name = f"document_{idx}.doc"
        file_content = doc.page_content
        file_metadata = doc.metadata

        file_obj = File(file_name=file_name, payload=file_content)
        
        add_source = CustomGPT.Source.create(project_id=project_id, file=file_obj)
        if add_source.status_code != 201:
            st.error(f"Failed to upload file {file_name}. Status code: {add_source.status_code}")
            continue
        
        page_id = add_source.parsed.data.pages[0].id
        update_metadata = CustomGPT.PageMetadata.update(
            project_id, 
            page_id, 
            url=file_metadata["url"],
            title=file_metadata["title"]
        )
        if update_metadata.status_code != 200:
            st.error(f"Failed to update metadata for {file_name}. Status code: {update_metadata.status_code}")
        
        progress = (idx + 1) / len(docs)
        progress_bar.progress(progress)
        status_text.text(f"Transferring documents: {idx + 1}/{len(docs)}")
    
    status_text.text("Transfer complete!")
    return project_id

def check_indexing_status(project_id, api_key):
    CustomGPT.api_key = api_key
    page_n = 1
    all_documents_indexed = False
    
    status_text = st.empty()
    
    while not all_documents_indexed:
        documents_response = CustomGPT.Page.get(project_id=project_id, page=page_n)
        if documents_response.status_code != 200:
            st.error(f"Failed to retrieve documents. Status code: {documents_response.status_code}")
            return False
        
        documents_data = documents_response.parsed.data.pages
        documents = documents_data.data
        
        page_n_completed = True
        for doc in documents:
            if doc.index_status == "queued":
                status_text.text(f"Indexing in progress... (Page {page_n})")
                time.sleep(5)
                page_n_completed = False
                break
        
        if page_n_completed:
            if documents_data.next_page_url:
                page_n += 1
            else:
                all_documents_indexed = True 
    
    status_text.text("All documents indexed successfully!")
    return True

# Streamlit UI
st.set_page_config(page_title="Apify Web Scraper to CustomGPT AI Agent Builder", layout="wide")

st.title("Apify Web Scraper to CustomGPT AI Agent Builder")
st.markdown("*Securely sync website content scraped from Apify to CustomGPT to build your AI Agent. [ [Github](https://github.com/adorosario/apify-customgpt) ]*")
st.markdown("---")

# Source Section
st.header("Source: Apify")
col1, col2= st.columns(2)

with col1:
    starting_url = st.text_input(
        "Starting URL",
        help="Enter the full URL of the website you want to scrape (e.g., https://www.example.com)"
    )

with col2:
    apify_api_token = st.text_input(
        "Apify API Token",
        type="password",
        help="Enter your Apify API token. You can find this in your Apify account settings."
    )

# Destination Section
st.header("Destination: CustomGPT")
customgpt_api_key = st.text_input(
    "CustomGPT API Key",
    type="password",
    help="Enter your [CustomGPT API key](https://app.customgpt.ai/profile#api). You can find this in your CustomGPT account settings.")

# Action Button
if st.button("Fetch and Transfer Data", help="Click to start the data transfer process"):
    if not starting_url or not apify_api_token or not customgpt_api_key:
        st.error("Please fill in all required fields before proceeding.")
    else:
        # Set up Apify
        os.environ["APIFY_API_TOKEN"] = apify_api_token
        apify = ApifyWrapper()

        # Scrape website content
        st.info(f"Starting Apify actor to scrape: {starting_url} ...")
        with st.spinner("Scraping website content..."):
            loader = apify.call_actor(
                actor_id="apify/website-content-crawler",
                run_input={"startUrls": [{"url": starting_url}], "maxCrawlDepth": 20},
                dataset_mapping_function=lambda item: Document(
                    page_content=item["text"] or "",
                    metadata={
                        "url": item["url"],
                        "title": item.get("metadata", {}).get("title", ""),
                        "description": item.get("metadata", {}).get("description", "")[:197] + "..." if item.get("metadata", {}).get("description") else ""
                    }
                ),
            )
            docs = loader.load()

        # Transfer to CustomGPT
        total_documents = len(docs)
        st.info(f"Beginning sync of {total_documents} documents to CustomGPT ...")
        customgpt_project_name = generate_project_name(starting_url)
        
        with st.spinner("Transferring data to CustomGPT..."):
            project_id = transfer_to_customgpt(customgpt_project_name, docs, customgpt_api_key)

        if project_id:
            st.info("Checking indexing status...")
            with st.spinner("Checking indexing status..."):
                indexing_successful = check_indexing_status(project_id, customgpt_api_key)
            if indexing_successful:
                st.markdown(f"""
                ### :tada: Data Successfully Synced!
                
                Your Apify scraped content has been successfully transferred to CustomGPT and indexed.
                
                You can now query your data using the CustomGPT dashboard:
                
                **[Open CustomGPT Dashboard](https://app.customgpt.ai/projects/{project_id}/ask-me-anything)**
                """)
        else:
            st.error("Failed to create CustomGPT project. Please check your inputs and try again.")
