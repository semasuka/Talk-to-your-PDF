#!/usr/bin/env python
# coding: utf-8

# In[1]:


import openai, glob, os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pdfminer.high_level import extract_text as pdf_extract_text


# In[2]:


class PreRunProcessor:
    def __init__(self):
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        db_password = os.getenv("POSTGRES_PASSWORD")
        self.engine = create_engine(f'postgresql://postgres:{db_password}@localhost:5432/pdf_db')
        self.Session = sessionmaker(bind=self.engine)

    def pdf_to_text(self, pdf_path: str, chunk_length: int = 1000) -> list:
        # Use pdfminer's extract_text function
        text = pdf_extract_text(pdf_path)
        chunks = [text[i:i + chunk_length].replace('\n', '') for i in range(0, len(text), chunk_length)]
        return self._generate_embeddings(chunks)

    def define_vector_store(self, embeddings: list) -> bool:
        session = self.Session()  # Create session instance
        try:
            # Truncate table and insert new embeddings
            session.execute(text("TRUNCATE TABLE pdf_holder RESTART IDENTITY"))
            for embedding in embeddings:
                session.execute(text("INSERT INTO pdf_holder (text, embedding) VALUES (:text, :embedding)"),
                                {"text": embedding["text"], "embedding": embedding["vector"]})
            session.commit()  # Commit the transaction
            print("Embeddings successfully stored in the database.")
            return True  # Return True on success
        except Exception as e:
            session.rollback()  # Rollback in case of an error
            print(f"An error occurred while storing embeddings: {e}")
            return False  # Return False on failure
        finally:
            session.close()  # Ensure the session is closed

    def _generate_embeddings(self, chunks: list) -> list:
        try:
            response = openai.embeddings.create(model='text-embedding-3-large', input=chunks)
            return [{"vector": embedding_info.embedding, "text": chunks[embedding_info.index]}
                    for embedding_info in response.data]
        except Exception as e:
            print(f"An error occurred during embeddings generation: {e}")
            return []


# In[3]:


def process_pre_run(pdf_folder_path: str) -> bool:
    processor = PreRunProcessor()
    
    # Use glob to get all PDF files in the directory
    pdf_file_paths = glob.glob(os.path.join(pdf_folder_path, '*.pdf'))
    
    if not pdf_file_paths:
        print("No PDF files found in the specified directory.")
        return False

    for pdf_file_path in pdf_file_paths:
        # Pass each file to the pdf_to_text function
        embeddings = processor.pdf_to_text(pdf_file_path)
        if not embeddings or not processor.define_vector_store(embeddings):
            print(f"Failed to store embeddings for {pdf_file_path}.")
            return False  # Return False if storing embeddings fails for any PDF

    return True  # Return True if all embeddings are successfully stored


