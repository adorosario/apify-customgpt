import json
import os
import time

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.utilities import ApifyWrapper
from customgpt_client import CustomGPT
from customgpt_client.types import File


# Load environment variables from .env file
load_dotenv()


CUSTOMGPT_API_KEY = os.getenv("CUSTOMGPT_API_KEY")
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# Define the content to be scraped.
URL_TO_BE_SCRAPED = "https://docs.apify.com/api/v2"


# Create an instance of the ApifyWrapper class.
apify = ApifyWrapper(apify_api_token=APIFY_API_TOKEN)

# Call actor to scrape the website content.
loader = apify.call_actor(
    actor_id="apify/website-content-crawler",
    run_input={"startUrls": [{"url": URL_TO_BE_SCRAPED}]},
    dataset_mapping_function=lambda item: Document(
        page_content=item["text"] or "", metadata={"source": item["url"]}
    ),
)

# load the documents
docs = loader.load()

# Create an instance of the CustomGPT class.
project_name = "Example ChatBot using Apify Actors"

CustomGPT.api_key = CUSTOMGPT_API_KEY

project = CustomGPT.Project.create(project_name=project_name)


# Check status of the project if chat bot is active
data = project.parsed.data

# Get project id from response for created project
project_id = data.id

for idx, doc in enumerate(docs):
    # Create a document for each page content
    file_name = f"document_{idx}.txt"
    file_content = doc.page_content

    # Create a file object
    file_obj = File(file_name=file_name, payload=file_content)

    # Upload the document to the project
    add_source = CustomGPT.Source.create(project_id=project_id, file=file_obj)

    # Check the status of the uploaded file
    print(f"File {file_name} uploaded successfully!")

while True:
    # GET project details
    get_project = CustomGPT.Project.get(project_id=project_id)
    project_data = get_project.parsed

    # Check if 'is_chat_active' is True
    is_chat_active = project_data.data.is_chat_active
    print(f"ChatBot Active Status: {is_chat_active}")

    # Break the loop if chatbot is active
    if is_chat_active:
        print("Chatbot is now active!")
        break

    # Sleep for a few seconds before checking again
    time.sleep(5)

# Create a conversation before sending a message to the chat bot
project_conversataion = CustomGPT.Conversation.create(
    project_id=project_id, name="My First Conversation"
)
project_data = project_conversataion.parsed

# Get the session id for the conversation
session_id = project_data.data.session_id

# pass in your question to prompt
prompt = "How do I run an apify actor?"

response = CustomGPT.Conversation.send(
    project_id=project_id, session_id=session_id, prompt=prompt, stream=False
)


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
