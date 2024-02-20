
# Talk to your PDF

![banner](assets/talk_to_your_pdf_banner.png)
![Python version](https://img.shields.io/badge/Python%20version-3.11%2B-lightgrey)
![GitHub last commit](https://img.shields.io/github/last-commit/semasuka/Talk-to-your-PDF)
![GitHub repo size](https://img.shields.io/github/repo-size/semasuka/Talk-to-your-PDF)
![License](https://img.shields.io/badge/License-MIT-green)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1wF6NBLDt_SDy1aBeTxNvq7ZIi_bo7nLu)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://talk-to-your-pdf.streamlit.app/)
[![Open Source Love svg1](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://github.com/ellerbrock/open-source-badges/)

Badge [source](https://shields.io/)

## Overview

"Talk to your PDF" is an interactive app that allows users to upload PDF documents and ask questions about their content. Utilizing advanced NLP techniques like retrieval augmented generation (RAG), the app extracts text from the PDFs, generates embeddings of the PDF text and question, and provides relevant responses to user queries without the need for manual document navigation. This app is built from scratch, no framework (like LangChain) used.

## Authors

- [@semasuka](https://www.github.com/semasuka)

## Table of Contents
- [Talk to your PDF](#talk-to-your-pdf)
  - [Overview](#overview)
  - [Authors](#authors)
  - [Table of Contents](#table-of-contents)
  - [Features](#features)
  - [Tech Stack](#tech-stack)
  - [How RAG Works](#how-rag-works)
  - [How the app Works](#how-the-app-works)
      - [Step 1: File Upload](#step-1-file-upload)
      - [Step 2: Pre-run Service](#step-2-pre-run-service)
      - [Step 3: Intent Service](#step-3-intent-service)
      - [Step 4: Information Retrieval Service](#step-4-information-retrieval-service)
      - [Step 5: Response Service](#step-5-response-service)
  - [Quick Start](#quick-start)
  - [App deployed on Streamlit](#app-deployed-on-streamlit)
  - [Repository structure](#repository-structure)
  - [Contributing](#contributing)
  - [License](#license)

## Features

- PDF text extraction and embedding generation for efficient information retrieval.
- User query processing with intent detection to ensure relevant and safe interactions.
- Database storage of PDF embeddings for quick access and response generation.
- Integration with Google Drive for secure and convenient file management.
- Clean and intuitive interface

## Tech Stack

- Python 3.11+
- Streamlit for the web interface
- OpenAI for embeddings and intent detection (using the moderation model) and response generation (using GPT-4 turbo)
- PostgreSQL with Supabase for database management
- pgvector PostgreSQL extension to handle vectors embedding
- Google Drive API for the PDF storage
- Requests and Tempfile for handling HTTP requests and temporary file management
- SQLAlchemy for connecting to the PostgreSQL database using Python to run SQL queries

## How RAG Works

![How RAG works](assets/rag_explained.jpeg)
[Image credit](https://towardsdatascience.com/why-your-rag-is-not-reliable-in-a-production-environment-9e6a73b3eddb)

**Indexing**

- Loader: This component is responsible for loading the knowledge base into the system. The knowledge base contains a vast collection of information that the RAG system will draw from to generate responses.

- Documents: After the knowledge base is loaded, it's organized into documents. These documents are then processed and made ready for the next steps. They could be anything from wiki articles to textbooks or any other structured collection of text. In our case we are using text extracted from the PDF.

- Splitter: The splitter takes these documents and breaks them down into smaller, more manageable pieces known as document snippets. These snippets are easier to work with when matching the information to a query.

- Embedding Machine: The document snippets are then fed into an embedding machine, which converts the text into embeddings. These embeddings are high-dimensional vectors (3072 for this app) that represent the semantic meaning of the snippets.

- Embeddings: The result is a set of embeddings, each corresponding to a document snippet from the knowledge base.

- Vector Database: The embeddings are stored in a vector database(PostgreSQL with pgvector extension). This database allows for efficient similarity searches; for example, when the system needs to find the snippet most closely related to a given query, it can perform a "closeness" query.

**Retrieval**

- Question: This represents the user's query/question regarding the PDF, such as "How do I do X?"

- Embedding Machine: The same embedding machine used during indexing processes the question to convert it into an embedding.

- Embeddings: The question embedding is then used to search the vector database for the most relevant document snippets.

- Vector Database: The system queries the vector database with the embedding of the question to find the closest matching document snippets.

- Relevant Snippets: The most relevant snippets are retrieved from the database. These are the snippets that have the closest embeddings to the question's embedding.

**Augmented Answer Generation**

- LLM (Large Language Model): The retrieved snippets are fed into a large language model along with the original question.

- Answer: By considering both the user's question and the information contained within the relevant snippets, the language model generates an informed, well structured and contextually relevant answer, like "To do X...".

## How the app Works

![How the app works](assets/how_it_works.png)


#### Step 1: File Upload

The user begins by uploading a PDF document through the application's interface. The backend receives this file and prepares it for text processing.

#### Step 2: Pre-run Service

The `PreRunProcessor` class takes charge by extracting text from the PDF. It then generates embeddings for the extracted text using the OpenAI API. These embeddings are numerical representations that encapsulate the meaning of the text segments, making them suitable for comparison and retrieval tasks.

#### Step 3: Intent Service

When the user submits a query about the PDF's content, the `IntentService` class performs two critical functions:

- Malicious Intent Detection: Utilizes OpenAI's moderation model to ensure the query does not contain inappropriate content.
- Relatedness Check: Converts the user's query into embeddings and checks if the query is relevant to the content of the PDF. This is done by comparing the query embeddings against the stored text embeddings from the PDF.


#### Step 4: Information Retrieval Service

Upon establishing the relevance of the query to the PDF content, the `InformationRetrievalService` class employs a cosine similarity search to find the most pertinent text segment that matches the query embeddings. Cosine similarity is a metric used to measure how similar the embeddings are, thus identifying the segment of the PDF that best addresses the user's query.

#### Step 5: Response Service

Finally, the `ResponseService` class uses the information retrieved to generate a response to the user's query. It leverages OpenAI's ChatCompletion API to formulate an answer that is not only relevant but also articulated in a clear and informative manner.

## Quick Start

This guide will walk you through setting up the "Talk to Your PDF" project from start to finish. Follow these steps to clone the repository, set up your environment, and start interacting with your PDFs in a new way.

0. **Pre-Requisites**

    Before starting, ensure you have the following:
      - **Openai API account**: Needed for the OpenAI API key.
      - **Python**: Make sure Python is installed on your machine.
      - **Google Cloud Platform (GCP) Account**: Needed for Google Drive API setup.
      - **Supabase Account**: Required for database setup.

1. **Clone the repository**

    Clone the "Talk to Your PDF" repository and navigate into the project directory

    ```bash
    git clone https://github.com/semasuka/Talk-to-your-PDF
    cd Talk-to-your-PDF/
    ```

2. **Create a Virtual Environment**

    Isolate your project's Python dependencies by creating a virtual environment

    ```bash
    python -m venv venv
    source venv/bin/activate # Unix/macOS
    venv\Scripts\activate # Windows
    ```

3. **Install dependencies**
   
   Install the necessary Python packages for the project

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables Setup**
   
   Add to your `venv` file in the project directory to securely store your environment variables. Initially, it will look like this

   ```bash
    GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google-credentials.json
    SUPABASE_POSTGRES_URL=your_supabase_postgres_url_here
    OPENAI_API_KEY=your_openai_api_key_here
    ```

5. **Google drive API setup**
    
   - **Create a Project in Google Cloud Platform (GCP):**
     - Go to the [Google Cloud Console](https://console.cloud.google.com/).
     - Click on "Select a project" at the top of the dashboard and then "New Project".
     - Enter a project name and click "Create".

   - **Enable Google Drive API:**
     - In the dashboard of your new project, navigate to "APIs & Services" > "Dashboard".
     - Click on "+ ENABLE APIS AND SERVICES".
     - Search for "Google Drive API" and enable it for your project.

   - **Create Credentials:**
     - Go to "APIs & Services" > "Credentials".
     - Click on "Create credentials" and select "Service account".
     - Fill out the service account details and grant it a role of "Editor" (or a more restricted role if you know the specific permissions you need).
     - Click "Create" and then "Done".

   - **Generate a Key for the Service Account:**
     - Find your new service account in the "Credentials" page and click on it.
     - Go to the "Keys" tab.
     - Click on "Add Key" and choose "Create new key".
     - Select "JSON" as the key type and click "Create".
     - The JSON key file will be automatically downloaded. This file contains your API key.
     - Important: Update the GOOGLE_APPLICATION_CREDENTIALS in your .env file with the path to this downloaded JSON file.

   - **Configure the Python Script:**
     - Open the JSON key file with a text editor and find the `client_email` and `private_key` fields.
     - In your Python script or environment, set the `client_email` and `private_key` as environment variables, or directly insert them into the `credentials_info` dictionary within the `upload_to_google_drive` function.

   - **Set Environment Variables:**
     - For security reasons, it's best practice to use environment variables for sensitive information like API keys.
     - You can set environment variables in your system, or use a `.env` file and load them with `load_dotenv()` in your script.
     - Set `GOOGLE_APPLICATION_CREDENTIALS` as an environment variable pointing to the path of the downloaded JSON key file.

   - **Install Required Libraries:**
     - Make sure that all required Python libraries, including `oauth2client`, `PyDrive`, and `google-auth`, are installed in your environment. You can usually install these using `pip install`.

   - **Use the Credentials in the Script:**
     - In the script, ensure that the `upload_to_google_drive` function is correctly configured to authenticate with Google using the service account credentials.

   - **Test the Setup:**
     - Run your script in a secure, local development environment first to ensure the Google Drive API is being called correctly and the file is being uploaded.
     - Make sure to handle the `credentials_dict` properly without exposing your private keys in the source code if you're going to share the script or use it in a public setting.

6. **Supabase database setup**

   - **Sign Up or Log In to Supabase**
      - Navigate to [Supabase](https://supabase.io) and sign in or create a new account.
      - Once logged in, create a new project by clicking on the 'New Project' button.

   - **Project Configuration**
      - Fill in the necessary details for your project, such as the name and password.
      - Wait for the project to be fully deployed. This might take a couple of minutes.

   - **Database Setup**
      - Once the project is ready, go to the SQL editor in the Supabase dashboard of your project.
      - You can run SQL commands here to set up your database schemas and extensions.

   - **Install pgvector Extension**
      - Execute the following SQL command to add the `pgvector` extension to your database:
        ```sql
        CREATE EXTENSION IF NOT EXISTS vector;
        ```
      - This command sets up the database to handle vector data types which are required for the embeddings.

   - **Create Table with Vector Column**
      - Create a table that will store your embeddings with a vector column by running:
        ```sql
        CREATE TABLE pdf_holder (
            id SERIAL PRIMARY KEY,
            text TEXT,
            embedding VECTOR(3072)
        );
        ```
      - This table will be used to store the text from the PDFs and their corresponding embeddings.

   - **Retrieve Supabase Credentials**
      - After setting up your table, go to the 'Settings' > 'Database' section of your project's dashboard.
      - Here you can find the `SUPABASE_POSTGRES_URL` which is required for connecting to the database from your application.

   - **Set Up Environment Variables**
      - In your application environment, set the `SUPABASE_POSTGRES_URL` as an environment variable.
      - This is essential for your application to connect and interact with your Supabase database securely.

   - **Integrate with the Application**
      - Use the `create_engine` function from the `sqlalchemy` library to connect to your Supabase database using the URL from the previous step.
      - Utilize the database session to execute your operations, such as storing and retrieving vector data.

   - **Test the Database Connection**
      - Before proceeding, ensure that your application can connect to the Supabase database and perform operations.
      - Try inserting a dummy record or retrieving data from the `pdf_holder` table as a test.

   - **Deploy Your Application**
       - After confirming the database connection, you can proceed to deploy your application.
       - Monitor the application logs to ensure there are no connection issues with the Supabase database.
7. **OpenAI API Setup**

    - Obtain your OpenAI API key from the OpenAI API platform.
    - Fill in the `OPENAI_API_KEY` in your `.env` file with your key.

8. **Run the app locally**

    Go to the directory that contains the app and run

   ```bash
   streamlit run streamlit_app.py
   ```

9. **Testing and Validation**

    To verify your setup:

    - Perform a test upload to Google Drive through the app.
    - Ensure the app can process queries about the uploaded PDFs correctly.

10. **Set up deploy and set up the Streamlit secrets**

    If the app is running fine locally you can deploy it on Streamlit share and add your OpenAI API key, Supabase URL, and Google drive credentials (JSON file from your service account) to the TOML placeholder. Your TOML key-value pairs should look like this

    ```toml
        SUPABASE_POSTGRES_URL="postgresql://<USERNAME>:<PASSWORD>@<HOST>:<PORT>/<DATABASE>"
        OPENAI_API_KEY="<OPENAI_API_KEY_PLACEHOLDER>"
        [google_credentials]
        type = "service_account"
        project_id = "<PROJECT_ID_PLACEHOLDER>"
        private_key_id = "<PRIVATE_KEY_ID_PLACEHOLDER>"
        private_key = """
        -----BEGIN PRIVATE KEY-----
        <PRIVATE_KEY_CONTENTS_PLACEHOLDER>
        -----END PRIVATE KEY-----
        """
        client_email = "<CLIENT_EMAIL_PLACEHOLDER>"
        client_id = "<CLIENT_ID_PLACEHOLDER>"
        auth_uri = "https://accounts.google.com/o/oauth2/auth"
        token_uri = "https://oauth2.googleapis.com/token"
        auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
        client_x509_cert_url = "<CLIENT_X509_CERT_URL_PLACEHOLDER>"
        universe_domain = "googleapis.com"
    ```

11. **Deploying and using the Application**

    Now the app should be deployed to the Streamlit share link, upload PDF files and explore the application's features by asking questions related to the PDF content.

## App deployed on Streamlit

![Streamlit GIF](https://github.com/semasuka/Talk-to-your-PDF/blob/main/assets/git_streamlit.gif)

Video to gif [tool](https://www.img2go.com/)


## Repository structure

```

├── assets
│   ├── gif_streamlit.gif                         <- gif file used in the README.
│   ├── how_it_works.png                          <- a diagram picture to show how the app works and how different services interact with each other.
│   ├── rag_explained.jpeg                        <- a picture with RAG explanation.
│   ├── talk_to_your_pdf_banner.png               <- banner image used in the README.
│
│
├── notebook_repository
│   ├── information_retrieval_service.ipynb       <- contains all the logic for information retrieval.
│   ├── intent_service.ipynb                      <- contains all the logic for question intent check.
│   ├── main.ipynb                                <- the final file that calls all the other notebooks that holds all the services.
│   ├── pre_run_service.ipynb                     <- contains all the pre-run processes.
│   ├── response_service.ipynb                    <- contains all the logic for response process.
│
│
├── .gitignore                                    <- used to ignore certain folder and files that won't be commit to git.
│
│
├── LICENSE                                       <- license file.
│
│
├── README.md                                     <- this readme file.
│
│
├── requirements.txt                              <- list of all the dependencies (used for Streamlit).
│
│
├── streamlit_app.py                              <- file with the all codes and Streamlit component for rendering the interface.


```

## Contributing

Contributions are welcome! For major changes, please open an issue first to discuss what you would like to change. Please ensure to update tests as appropriate.

## License

MIT License

Copyright (c) 2024 Stern Semasuka

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Learn more about [MIT](https://choosealicense.com/licenses/mit/) license




