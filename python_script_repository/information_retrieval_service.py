#!/usr/bin/env python
# coding: utf-8

# In[38]:


from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os, openai


# In[ ]:


class InformationRetrievalService:
    def __init__(self):
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        db_password = os.getenv("POSTGRES_PASSWORD")
        self.engine = create_engine(f'postgresql://postgres:{db_password}@localhost:5432/pdf_db')
        self.Session = sessionmaker(bind=self.engine)

    def search_in_vector_store(self, vectorized_question: str, k: int = 1) -> str:
        sql_query = text("""
            SELECT id, text, embedding <=> CAST(:query_vector AS VECTOR) AS distance
            FROM pdf_holder
            ORDER BY distance
            LIMIT :k
        """)
        with self.engine.connect() as conn:
            results = conn.execute(sql_query, {'query_vector': vectorized_question, 'k': k}).fetchall()
            if results:
                # Accessing the 'text' column correctly in the first result row
                return results[0].text
            else:
                print("No matching documents found.")


# In[ ]:


def process_retrieval(vectorized_question: str) -> tuple:
    service = InformationRetrievalService()
    retrieved_info = service.search_in_vector_store(vectorized_question)
    return retrieved_info

