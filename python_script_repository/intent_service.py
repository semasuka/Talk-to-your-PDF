#!/usr/bin/env python
# coding: utf-8

# In[62]:


import os, openai
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import text, create_engine
from IPython.display import clear_output


# In[64]:


class IntentService:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Get database password from environment variable
        self.engine = create_engine(f'postgresql://postgres:{os.getenv("POSTGRES_PASSWORD")}@localhost:5432/pdf_db')

    def detect_malicious_intent(self, question):
        """Uses OpenAI's moderation model to detect malicious intent in a question."""
        try:
            response = openai.moderations.create(
                model="text-moderation-latest",
                input=question,
            )
            is_flagged = response.results[0].flagged
            return is_flagged, "This question has been flagged for malicious content and cannot be processed." if is_flagged else "No malicious intent detected."
        except Exception as e:
            return None, f"Error in moderation: {str(e).split('. ')[0]}."
        
    def query_database(self, query):
        """Executes a given query on the database."""
        with self.engine.connect() as connection:
            result = connection.execute(text(query)).fetchone()
            return result if result else None
    
    def question_to_embeddings(self, question):
        """Converts a question to embeddings."""
        try:
            response = openai.embeddings.create(input=question, model="text-embedding-3-large")
            embedded_query = response.data[0].embedding
            # Ensure the embedding matches the expected dimensionality of 3072
            if len(embedded_query) != 3072:
                raise ValueError("The dimensionality of the question embedding does not match the expected 3072 dimensions.")
            else:
                question_vectorized = np.array(embedded_query, dtype=np.float64).tolist()
                return question_vectorized
        except Exception as e:
            print(f"Error embedding the question: {e}")
            return [] # Return an empty list if no data is found in the response

    def check_relatedness_to_pdf_content(self, question):
        """Checks if the question is related to the PDF content by querying a database."""
        question_vectorized = self.question_to_embeddings(question)

        try:

            with self.engine.connect() as conn:
                # Use the vector in your query with the <=> operator for cosine distance
                result = conn.execute(text("""
                    SELECT id, text, embedding <=> CAST(:question_vector AS VECTOR) AS distance 
                    FROM pdf_holder
                    ORDER BY distance ASC
                    LIMIT 1;
                """), {'question_vector': question_vectorized}).fetchone()

                if result:
                    closest_id, _, distance = result
                    threshold = 0.5  # albritrary threshold that works well with my PDF, needs to test it out accordingly 
                    if distance < threshold:
                        return True, "Question is related to the PDF content."
                    else:
                        return False, "Question is not related to the PDF content."
                else:
                    return False, "No match found in the database."
        except Exception as e:
            print(f"Error searching the database: {e}")
            return False, f"Error searching the database: {e}"


# In[65]:


def intent_orchestrator(service):
    """Orchestrates the process of checking if a question is related to any PDF content."""

    while True:
        clear_output(wait=True)
        question = input("Enter your question or type 'exit' to quit: ").strip()
        if question.lower() == 'exit':
            print("Exiting...")
            return None
        

        is_flagged, message = service.detect_malicious_intent(question)
        print(message)
        if is_flagged or is_flagged is None:  # Continue loop if flagged or an error occurred
            continue

        related, message = service.check_relatedness_to_pdf_content(question)
        print(message)
        vectorized_question = service.question_to_embeddings(question)
        if related:
            return vectorized_question, question
        else:
            print("Please try a different question...")


# In[66]:


def process_user_question():
    """Main function to start the question processing workflow."""
    service = IntentService()
    vectorized_question, question = intent_orchestrator(service)
    if not vectorized_question:
        print("No question was processed successfully.")
    else:
        return vectorized_question, question

