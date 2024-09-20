# apify-customgpt

## Table of Contents
1. [Environment Setup](#environment-setup)
2. [Code Explanation](#code-explanation)
   - [Loader](#loader)
   - [Create Project from File](#create-project-from-file)
   - [Create Conversation](#create-conversation)
   - [Send a Message](#send-a-message)
3. [Example Usage](#example-usage)

## Environment Setup

Before running the project, you need to set up your environment variables. Create a `.env` file in the root directory of your project and add the following variables:

```
APIFY_API_TOKEN=<your_apify_api_token>
CUSTOMGPT_API_KEY=<your_customgpt_api_key>
```

Replace `<your_apify_api_token>` with your actual Apify API token and `<your_customgpt_api_key>` with your CustomGPT API key.

## Usage
1. Clone the Repository:
   Clone the repository to your local 
   ```cmd
      git clone https://github.com/adorosario/apify-customgpt.git
   ```

2. Install Requirements:
   Navigate to the project directory and install the necessary dependencies:
   ```cmd
      cd apify-customgpt
      pip install -r requirements.txt
   ```
## Code Explanation

### Setting up the environment variables

```python
from dotenv import load_dotenv

load_dotenv()

APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")
CUSTOMGPT_API_KEY = os.getenv("CUSTOMGPT_API_KEY")
```

### Loader

The loader is responsible for initializing and loading necessary components for the project. It typically includes:

- Initializing the Apify Wrapper
- Setting up the Actor to load the required docs


```python
from langchain_community.utilities import ApifyWrapper


URL_TO_BE_SCRAPED = "https://docs.apify.com/api/v2"

apify = ApifyWrapper(apify_api_token=APIFY_API_TOKEN)

loader = apify.call_actor(
    actor_id="apify/website-content-crawler",
    run_input={"startUrls": [{"url": URL_TO_BE_SCRAPED}]},
    dataset_mapping_function=lambda item: Document(
        page_content=item["text"] or "", metadata={"source": item["url"]}
    ),
)

docs = loader.load()
```

### Create Project from File

This part creates a new project using a file as input. It may involve:

- Reading the contents of the file
- Sending a request to the API to create a new project
- Handling the response and returning the project details

Example:

```python
file_content = "\n\n".join([doc.page_content for doc in docs])

project_name = "Example ChatBot using Apify Actors"

CustomGPT.api_key = CUSTOMGPT_API_KEY

project = CustomGPT.Project.create(
    project_name=project_name, file=File(payload=file_content, file_name="apify.doc")
)

data = project.parsed.data

# Get project id from response for created project
project_id = data.id
```

To check the status of the bot you just created:

```python
get_project = CustomGPT.Project.get(project_id=project_id)
project_data = get_project.parsed
is_chat_active = project_data.data.is_chat_active

# ChatBot Status
print(is_chat_active)
```

### Create Conversation

This part initializes a new conversation within a project. It typically includes:

- Sending a request to the API to create a new conversation
- Handling the response and returning the conversation details

Example:

```python
# Create a conversation before sending a message to the chat bot
project_conversataion = CustomGPT.Conversation.create(
    project_id=project_id, name="My First Conversation"
)
project_data = project_conversataion.parsed

# Get the session id for the conversation
session_id = project_data.data.session_id
```

### Send a Message

This function sends a message within a conversation. It involves:

- Preparing the message content
- Sending a request to the API to add the message to the conversation
- Handling the response and returning any relevant information

Example:

```python
prompt = "How do I run an apify actor?"

response = CustomGPT.Conversation.send(
    project_id=project_id, session_id=session_id, prompt=prompt, stream=False
)
```

## Example Usage

Here's an example:

```md
Query Sent:
------------
How do I run an apify actor?

Response Received:
------------------
To run an Apify actor, follow these steps:

1. **Send a POST Request**:
   - Use the Run actor endpoint: `https://api.apify.com/v2/acts/[actor_id]/runs`
   - Replace `[actor_id]` with the actor ID code (e.g., `vKg4IjxZbEYTYeW8T`) or its name (e.g., `janedoe~my-actor`).

2. **Authorization**:
   - If the actor is not runnable anonymously, include your secret API token in the request's Authorization header (recommended) or as a URL query parameter `?token=[your_token]` (less secure).

3. **Optional Query Parameters**:
   - You can include various query parameters to customize your run, such as `outputRecordKey`, `timeout`, and `memory`.

4. **Using Node.js**:
   - If you're using Node.js, the best way to run an actor is by using the `Apify.call()` method from the Apify SDK. This method runs the actor using the account you are logged into.

### Example Request
```
```json
POST https://api.apify.com/v2/acts/janedoe~my-actor/runs
Authorization: Bearer [your_token]
Content-Type: application/json

{
  "foo": "bar"
}
```
```md
### Response
The response will contain details about the actor run, such as its status and any output records.

### Important Notes
- If the actor run exceeds 300 seconds, the HTTP response will have status 408 (Request Timeout).
- Ensure your HTTP client is configured to have a long enough connection timeout to avoid broken connections.

By following these steps, you can successfully run an Apify actor.
```

This README provides an overview of the project structure and usage. For more detailed information on specific functions or components, please refer to the inline documentation in the source code.
