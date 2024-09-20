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

# load the page content
file_content = "\n\n".join([doc.page_content for doc in docs])

# Create an instance of the CustomGPT class.
project_name = "Example ChatBot using Apify Actors"

CustomGPT.api_key = CUSTOMGPT_API_KEY

project = CustomGPT.Project.create(
    project_name=project_name, file=File(payload=file_content, file_name="apify.doc")
)


# Check status of the project if chat bot is active
data = project.parsed.data

# Get project id from response for created project
project_id = data.id


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

### Format and display the result in a more readable way
response_content = response.content.decode("utf-8")
response_json = json.loads(response_content)

# Extract the query and response from the parsed JSON
user_query = response_json.get("data", {}).get("user_query", "No query found")
openai_response = response_json.get("data", {}).get(
    "openai_response", "No response found"
)

# Format and display the result in a more readable way
formatted_response = f"""
Query Sent:
------------
{user_query}

Response Received:
------------------
{openai_response}
"""

# Print the formatted response
print(formatted_response)
