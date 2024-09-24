# Docker Guide for apify-customgpt

This guide provides instructions on how to build and run the Docker container for the apify-customgpt project locally.

## Prerequisites

- Docker installed on your local machine
- Git installed

## Building and Running Locally

1. Clone the repository:
   ```
   git clone https://github.com/adorosario/apify-customgpt.git
   cd apify-customgpt
   ```

2. Set up your environment variables:
   Create a `.env` file in the root directory of the project with the following content:
   ```
   APIFY_API_TOKEN=your_apify_token
   CUSTOMGPT_API_KEY=your_customgpt_key
   ```
   Replace `your_apify_token` and `your_customgpt_key` with your actual API tokens.

3. Build the Docker image:
   ```
   docker build -t apify-customgpt .
   ```

4. Run the container locally:
   ```
   docker run -it --rm -v $(pwd):/app apify-customgpt
   ```

5. You will be dropped into a bash prompt inside the container. From here, you can run your Python script:
   ```
   python main.py --starting-url https://example.com --prompt "Your prompt here"
   ```

## Troubleshooting

- If you encounter any issues with running the script inside the Docker container, make sure your `.env` file is correctly set up and placed in the project root directory.
- If you need to install additional packages, you can do so using `pip` inside the container, or add them to the `requirements.txt` file and rebuild the image.

## Additional Notes

- Remember to update your `requirements.txt` file if you add any new dependencies to your project.
- The current Dockerfile is set up for local development and drops you into a bash prompt. This allows for interactive development and debugging.
- Never commit your `.env` file to the repository, as it contains sensitive information. Make sure it's listed in your `.gitignore` file.

For more information on using Docker for Python development, refer to the [official Docker documentation](https://docs.docker.com/language/python/).