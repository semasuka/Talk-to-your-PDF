import streamlit as st
import numpy as np
import openai, os, requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from pdfminer.high_level import extract_text as pdf_extract_text
from streamlit_lottie import st_lottie_spinner



##### Animation #####

@st.cache_data
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()


lottie_animation = load_lottieurl('https://lottie.host/5ac92c74-1a02-40ff-ac96-947c14236db1/u4nCMW6fXU.json')


##### Pre-run services #####

class PreRunProcessor:
    def __init__(self):
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        db_password = os.getenv("POSTGRES_PASSWORD")
        self.engine = create_engine(f'postgresql://postgres:{db_password}@localhost:5432/pdf_db')
        self.Session = sessionmaker(bind=self.engine)

    def pdf_to_text(self, uploaded_file, chunk_length: int = 1000) -> list:

        # Use pdfminer's extract_text function
        text = pdf_extract_text(uploaded_file)
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
            return True  # Return True on success
        except Exception as e:
            session.rollback()  # Rollback in case of an error
            return False  # Return False on failure
        finally:
            session.close()  # Ensure the session is closed

    def _generate_embeddings(self, chunks: list) -> list:
        try:
            response = openai.embeddings.create(model='text-embedding-3-large', input=chunks)
            return [{"vector": embedding_info.embedding, "text": chunks[embedding_info.index]}
                    for embedding_info in response.data]
        except Exception as e:
            st.error(f"An error occurred during embeddings generation: {e}")
            return []

def process_pre_run(uploaded_file):
    processor_class = PreRunProcessor()
    # Pass each file to the pdf_to_text function
    embeddings = processor_class.pdf_to_text(uploaded_file)
    if not embeddings or not processor_class.define_vector_store(embeddings):
        st.error("Failed to store the PDF embedding.")
    else:
        st.success("PDF successfully uploaded. We can proceed now...")




##### Intent services #####


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
            if is_flagged:
                return is_flagged, "This question has been flagged for malicious or inappropriate content."
            else:
                return is_flagged, "No malicious intent detected."
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



def intent_orchestrator(service_class, user_question):
    """Orchestrates the process of checking if a question is related to any PDF content."""
    is_flagged, flag_message = service_class.detect_malicious_intent(user_question)
    st.write(flag_message)

    if is_flagged:
        st.error("Your question was not processed. Please try a different question...")
        return None

    related, relatedness_message = service_class.check_relatedness_to_pdf_content(user_question)

    if related:
        vectorized_question = service_class.question_to_embeddings(user_question)
        st.write(relatedness_message)
        st.success("Your question was processed successfully. Now fetching an answer...")
        return vectorized_question, user_question
    else:
        st.write(relatedness_message)
        st.error("Your question was not processed. Please try a different question...")
        return None

def process_user_question(service_class, user_question):
    """Main function to start the question processing workflow."""
    result = intent_orchestrator(service_class, user_question)

    if result:
        vectorized_question, question = result
        # Implement what should happen once the question is processed
        # ...
        
        
def main():
    st.title("Talk to Your PDF")

    uploaded_file = st.file_uploader("Upload your PDF", type=["pdf"])
    if uploaded_file is not None:
        with st_lottie_spinner(lottie_animation, quality='high', height='100px', width='100px'):
            process_pre_run(uploaded_file)

        service_class = IntentService()  # Create an instance of the service class

        # Create a form for question input and submission
        with st.form(key='question_form'):
            user_question = st.text_input("Ask a question about the PDF content:", key="question_input")
            submit_button = st.form_submit_button(label='Ask')

        if submit_button:
            process_user_question(service_class, user_question)

# Run the app
if __name__ == '__main__':
    main()
