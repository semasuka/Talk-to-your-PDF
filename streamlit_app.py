import streamlit as st
import numpy as np
import openai, os, requests, dropbox
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError
from pdfminer.high_level import extract_text as pdf_extract_text
from streamlit_lottie import st_lottie_spinner
from dropbox.exceptions import ApiError




##### Animation #####

@st.cache_data
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()


loading_animation = load_lottieurl('https://lottie.host/5ac92c74-1a02-40ff-ac96-947c14236db1/u4nCMW6fXU.json')

##### Environment variables are loaded #####

load_dotenv()

##### Pre-run services #####

class PreRunProcessor:
    def __init__(self):
        openai.api_key = os.getenv("OPENAI_API_KEY")
        # Get PostgreSQL database from supabase platform
        self.engine = create_engine(os.getenv("SUPABASE_POSTGRES_URL"), echo=True, client_encoding='utf8')
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
            session.execute(text("TRUNCATE TABLE pdf_holder RESTART IDENTITY CASCADE;"))
            for embedding in embeddings:
                session.execute(text("INSERT INTO pdf_holder (text, embedding) VALUES (:text, :embedding)"),
                                {"text": embedding["text"], "embedding": embedding["vector"]})
            session.commit()  # Commit the transaction
            return True  # Return True on success
        except ProgrammingError as e:
            if 'relation "pdf_holder" does not exist' in str(e.orig.pgerror):
                session.rollback()  # Rollback in case of an error
                # create the vector extension in Supabase
                session.execute(text("""
                    CREATE EXTENSION IF NOT EXISTS vector;
                """))
                # Create the table if it doesn't exist
                session.execute(text("""
                    CREATE TABLE pdf_holder (
                        id SERIAL PRIMARY KEY,
                        text TEXT,
                        embedding VECTOR(3072)
                    );
                """))
                session.commit()
                return False  # Return False on failure
            else:
                raise
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
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Get PostgreSQL database from Supabase platform
        self.engine = create_engine(os.getenv("SUPABASE_POSTGRES_URL"), echo=True, client_encoding='utf8')



    def detect_malicious_intent(self, question):
        """Uses OpenAI's moderation model to detect malicious intent in a question."""
        try:
            response = openai.moderations.create(
                model="text-moderation-latest",
                input=question,
            )
            is_flagged = response.results[0].flagged
            if is_flagged:
                return is_flagged, "This question has been flagged for malicious or inappropriate content..."
            else:
                return is_flagged, "No malicious intent detected..."
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
                    _, _, distance = result
                    threshold = 0.5  # albritrary threshold that works well with my PDF, needs to test it out accordingly 
                    if distance < threshold:
                        return True, "Question is related to the PDF content..."
                    else:
                        return False, "Question is not related to the PDF content..."
                else:
                    return False, "No match found in the database."
        except Exception as e:
            print(f"Error searching the database: {e}")
            return False, f"Error searching the database: {e}"
        
        
##### Information retrieval service #####

class InformationRetrievalService:
    def __init__(self):
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        db_password = os.getenv("POSTGRES_PASSWORD")
        self.engine = create_engine(os.getenv("SUPABASE_POSTGRES_URL"), echo=True, client_encoding='utf8')
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
                st.error("No matching documents found.")

##### Response service #####

class ResponseService:
    """Handles generating responses based on user questions and provided facts."""
    
    def __init__(self):
        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def generate_response(self, question, retrieved_info):
        """Generates a response from OpenAI's ChatCompletion based on facts and a user question."""
        # call the openai ChatCompletion endpoint
        response = openai.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
                {"role": "user", "content": 'Based on the FACTS, give a concise and detailed answer to the QUESTION.'+ 
                f'QUESTION: {question}. FACTS: {retrieved_info}'}
            ]
        )

        if response.choices and response.choices:
            return response.choices[0].message.content
        st.error("No content available.")
        
###### Independant & dependant of the function's class ######


def refresh_dropbox_access_token(refresh_token, app_key, app_secret):
    """Function to refresh Dropbox access token"""
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": app_key,
        "client_secret": app_secret,
    }
    response = requests.post('https://api.dropboxapi.com/oauth2/token', data=data)
    if response.status_code == 200:
        new_access_token = response.json()['access_token']
        # Optionally update the environment variable or store the new token as needed
        os.environ["DROPBOX_ACCESS_TOKEN"] = new_access_token
        return new_access_token
    else:
        raise Exception("Could not refresh the access token.")

def upload_to_dropbox(file_stream, file_name):
    """function to handle all the upload to Dropbox"""
    DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")
    APP_KEY = os.getenv("DROPBOX_APP_KEY")
    APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
    ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")

    try:
        dbx = dropbox.Dropbox(ACCESS_TOKEN)
        # Check if a shared link already exists for the file
        existing_links = dbx.sharing_list_shared_links(path='/' + file_name).links
        if existing_links:
            # If links exist, return the URL of the first link
            return existing_links[0].url
        else:
            # If no link exists, upload the file and create a new shared link
            dbx.files_upload(file_stream.read(), '/' + file_name, mode=dropbox.files.WriteMode.overwrite)
            shared_link_metadata = dbx.sharing_create_shared_link_with_settings('/' + file_name)
            return shared_link_metadata.url
    except dropbox.exceptions.AuthError:
        # Refresh the access token if it has expired and retry
        print("Access token expired, refreshing...")
        new_access_token = refresh_dropbox_access_token(DROPBOX_REFRESH_TOKEN, APP_KEY, APP_SECRET)
        dbx = dropbox.Dropbox(new_access_token)
        # After refreshing the token, check again for existing shared links
        existing_links = dbx.sharing_list_shared_links(path='/' + file_name).links
        if existing_links:
            return existing_links[0].url
        else:
            dbx.files_upload(file_stream.read(), '/' + file_name, mode=dropbox.files.WriteMode.overwrite)
            shared_link_metadata = dbx.sharing_create_shared_link_with_settings('/' + file_name)
            return shared_link_metadata.url
    
    except ApiError as api_error:
        st.error(f"Dropbox API Error: {api_error}")
        # Optionally, re-raise the error or handle it based on your app's needs
        raise


def intent_orchestrator(service_class, user_question):
    """Orchestrates the process of checking if a question is related to any PDF content."""
    is_flagged, flag_message = service_class.detect_malicious_intent(user_question)
    st.write(flag_message)

    if is_flagged:
        st.error("Your question was not processed. Please try a different question.")
        return (None, None)

    related, relatedness_message = service_class.check_relatedness_to_pdf_content(user_question)

    if related:
        vectorized_question = service_class.question_to_embeddings(user_question)
        st.write(relatedness_message)
        st.success("Your question was processed successfully. Now fetching an answer...")
        return (vectorized_question, user_question)
    else:
        st.write(relatedness_message)
        st.error("Your question was not processed. Please try a different question.")
        return (None, None)

def process_user_question(service_class, user_question):
    """Main function to start the question processing workflow."""
    result = intent_orchestrator(service_class, user_question)
    if result:
        return result
        

def process_retrieval(vectorized_question: str) -> tuple:
    """Function to start the question processing workflow."""
    service = InformationRetrievalService()
    retrieved_info = service.search_in_vector_store(vectorized_question)
    return retrieved_info


def process_response(retrieved_info, question):
    """Function to return a well formatted question."""
    response_service_processor = ResponseService()
    final_response = response_service_processor.generate_response(question, retrieved_info)
    return final_response
        
        
def main():
    st.title("Talk to your PDF")

    
    uploaded_file = st.file_uploader("Upload your PDF", type=["pdf"])
    if uploaded_file is not None:
        # animation while uploading the PDF and processing the question
        with st_lottie_spinner(loading_animation, quality='high', height='100px', width='100px'):
            process_pre_run(uploaded_file)
        
        share_link = upload_to_dropbox(uploaded_file, uploaded_file.name)
        # Use markdown to display the hyperlink
        st.markdown(f'PDF file can be found [here]({share_link}).', unsafe_allow_html=True)
            

        service_class = IntentService()  # Create an instance of the service class

        # Create a form for question input and submission
        with st.form(key='question_form'):
            user_question = st.text_input("Ask a question about the PDF content:", key="question_input")
            submit_button = st.form_submit_button(label='Ask')

        if submit_button:
            result = process_user_question(service_class, user_question)
            if result[0] is not None:  # Check if the first element of the tuple is not None
                vectorized_question, question = result
                with st_lottie_spinner(loading_animation, quality='high', height='100px', width='100px'):
                    retrieved_info = process_retrieval(vectorized_question)
                    final_response = process_response(retrieved_info, question)
                    st.write(final_response)
            

            
# Run the app
if __name__ == '__main__':
    main()
