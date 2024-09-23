import json
import os
import time
import argparse

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.utilities import ApifyWrapper
from customgpt_client import CustomGPT
from customgpt_client.types import File
from requests.exceptions import HTTPError


def main(starting_url, user_prompt):
    # Load environment variables from .env file
    load_dotenv()

    CUSTOMGPT_API_KEY = os.getenv("CUSTOMGPT_API_KEY")
    APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

    # Create an instance of the ApifyWrapper class.
    apify = ApifyWrapper(apify_api_token=APIFY_API_TOKEN)

    # Call actor to scrape the website content.
    loader = apify.call_actor(
        actor_id="apify/website-content-crawler",
        run_input={"startUrls": [{"url": starting_url}], "maxCrawlDepth": 20},
        dataset_mapping_function=lambda item: Document(
            page_content=item["text"] or "", metadata={"source": item["url"]}
        ),
    )

    # Load the documents
    docs = loader.load()
    # Create an instance of the CustomGPT class.
    project_name = f"ChatBot for {starting_url}"
    CustomGPT.api_key = CUSTOMGPT_API_KEY

    project = CustomGPT.Project.create(project_name=project_name)

    # Check status of the project if the chatbot is active
    if project.status_code != 201:
        raise HTTPError(f"Failed to create project. Status code: {project.status_code}")

    data = project.parsed.data

    # Get project id from response for created project
    project_id = data.id

    for idx, doc in enumerate(docs):
        # Create a document for each page content
        file_name = f"document_{idx}.doc"
        file_content = doc.page_content
        file_metadata = doc.metadata

        # Check if the document content is empty or contains only whitespace
        if not file_content.strip():
            print(f"Skipping {file_name} because it is empty.")
            continue

        # Create a file object
        file_obj = File(file_name=file_name, payload=file_content)

        # Upload the document to the project
        add_source = CustomGPT.Source.create(project_id=project_id, file=file_obj)

        # Check if the file was uploaded successfully
        if add_source.status_code != 201:
            raise HTTPError(
                f"Failed to upload file {file_name}. Status code: {add_source.status_code}"
            )

        print(f"File {file_name} uploaded successfully!")

        # Get the page id of the uploaded file
        page_id = add_source.parsed.data.pages[0].id

        # Update the metadata of the uploaded file
        update_metadata = CustomGPT.PageMetadata.update(
            project_id, page_id, url=file_metadata["source"]
        )

        # Check the status of the metadata update
        if update_metadata.status_code != 200:
            raise HTTPError(
                f"Failed to update metadata for {file_name}. Status code: {update_metadata.status_code}"
            )

        print(f"Metadata updated for {file_name}!")

    # GET project details
    page_n = 1
    all_pages_indexed = False  # Track if all pages are indexed

    while not all_pages_indexed:
        pages_response = CustomGPT.Page.get(project_id=project_id, page=page_n)

        # Check if the get request was successful
        if pages_response.status_code != 200:
            raise HTTPError(
                f"Failed to retrieve pages. Status code: {pages_response.status_code}"
            )

        pages_data = pages_response.parsed.data.pages
        pages = pages_data.data
        page_n_completed = True  # Assume the page we are currently on is indexed unless we find it queued

        for page in pages:
            print(f"{page.filename}: {page.index_status}")
            if page.index_status == "queued":
                time.sleep(5)
                page_n_completed = (
                    False  # If the page is still queued, break out of the loop
                )
                break

        # If the current page is queued, we try again, otherwise we move to the next page.
        if page_n_completed:
            if pages_data.next_page_url:
                page_n += 1
            else:
                all_pages_indexed = True

    # Create a conversation before sending a message to the chatbot
    project_conversation = CustomGPT.Conversation.create(
        project_id=project_id, name="My First Conversation"
    )

    # Check if the conversation creation was successful
    if project_conversation.status_code != 201:
        raise HTTPError(
            f"Failed to create conversation. Status code: {project_conversation.status_code}"
        )

    project_data = project_conversation.parsed

    # Get the session id for the conversation
    session_id = project_data.data.session_id

    # Pass in your question to prompt
    prompt = user_prompt

    response = CustomGPT.Conversation.send(
        project_id=project_id, session_id=session_id, prompt=prompt, stream=False
    )

    # Check if the conversation response was successful
    if response.status_code != 200:
        raise HTTPError(f"Failed to send prompt. Status code: {response.status_code}")

    # Format and display the result in a more readable way
    formatted_response = f"""
    Query Sent:
    ------------
    {response.parsed.data.user_query}

    Response Received:
    ------------------
    {response.parsed.data.openai_response}
    """

    # Print the formatted response
    print(formatted_response)


if __name__ == "__main__":
    # Create an argument parser to accept --starting-url and --prompt arguments
    parser = argparse.ArgumentParser(
        description="CLI for scraping a website and using CustomGPT"
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
