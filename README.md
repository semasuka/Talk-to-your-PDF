
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

## Features

- PDF text extraction and embedding generation for efficient information retrieval.
- User query processing with intent detection to ensure relevant and safe interactions.
- Database storage of PDF embeddings for quick access and response generation.
- Integration with Google Drive for secure and convenient file management.
- Clean and intuitive interface

## Tech Stack

- Python 3.8+
- Streamlit for the web interface
- OpenAI for embeddings and intent detection (using the moderation model) and response generation (using GPT-4 turbo)
- PostgreSQL with Supabase for database management
- pgvector PostgreSQL extension to handle vectors embedding
- Google Drive API for the PDF storage
- Requests and Tempfile for handling HTTP requests and temporary file management
- SQLAlchemy for connecting to the PostgreSQL database using Python to run SQL queries

## How It Works

![How it works](assets/how_it_works.png)


#### Step 1: File Upload

The user begins by uploading a PDF document through the application's interface. The backend receives this file and prepares it for text processing.

#### Step 2: Pre-run Service

The PreRunProcessor class takes charge by extracting text from the PDF. It then generates embeddings for the extracted text using the OpenAI API. These embeddings are numerical representations that encapsulate the meaning of the text segments, making them suitable for comparison and retrieval tasks.

#### Step 3: Intent Service

When the user submits a query about the PDF's content, the IntentService class performs two critical functions:

- Malicious Intent Detection: Utilizes OpenAI's moderation model to ensure the query does not contain inappropriate content.
- Relatedness Check: Converts the user's query into embeddings and checks if the query is relevant to the content of the PDF. This is done by comparing the query embeddings against the stored text embeddings from the PDF.


#### Step 4: Information Retrieval Service

Upon establishing the relevance of the query to the PDF content, the InformationRetrievalService class employs a cosine similarity search to find the most pertinent text segment that matches the query embeddings. Cosine similarity is a metric used to measure how similar the embeddings are, thus identifying the segment of the PDF that best addresses the user's query.

#### Step 5: Response Service

Finally, the ResponseService class uses the information retrieved to generate a response to the user's query. It leverages OpenAI's ChatCompletion API to formulate an answer that is not only relevant but also articulated in a clear and informative manner.

## Quick Start

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/talk-to-your-pdf.git
   cd talk-to-your-pdf
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   Create a `.env` file in the project directory and add your OpenAI API key, Supabase URL, and Google credentials.

4. **Run the app**

   ```bash
   streamlit run app.py
   ```

## Deployment

This app is deployed on Streamlit Sharing. You can access it [here](https://share.streamlit.io/yourusername/talk-to-your-pdf/main/app.py). Follow the instructions in the `Deployment on streamlit` section of this README for details on deploying your own version.

## Contributing

Contributions are welcome! For major changes, please open an issue first to discuss what you would like to change. Please ensure to update tests as appropriate.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.
