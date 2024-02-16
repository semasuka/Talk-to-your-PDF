# Import necessary libraries
import streamlit as st
import numpy as np
import openai, os, requests, tempfile
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError
from pdfminer.high_level import extract_text as pdf_extract_text
from streamlit_lottie import st_lottie_spinner
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()

# Function to load Lottie animations using URL
@st.cache_data
def load_lottieurl(url):
    """
    Fetches and caches a Lottie animation from a provided URL.

    Args:
    url (str): The URL of the Lottie animation.

    Returns:
    dict: The Lottie animation JSON or None if the request fails.
    """
    r = requests.get(url)  # Perform the GET request
    if r.status_code != 200:
        return None  # Return None if request failed
    return r.json()  # Return the JSON content of the Lottie animation

# Load a specific Lottie animation to be used in the app
loading_animation = load_lottieurl('https://lottie.host/5ac92c74-1a02-40ff-ac96-947c14236db1/u4nCMW6fXU.json')

# Class for processing uploaded PDFs before user interaction
class PreRunProcessor:
    """
    Processes uploaded PDF files by extracting text and generating embeddings.
    """
    def __init__(self):
        """
        Initializes the processor with an OpenAI API key and a connection to a PostgreSQL database.
        """
        # Load OpenAI API key from environment variables
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Establish connection to the PostgreSQL database from the Supabase platform
        self.engine = create_engine(os.getenv("SUPABASE_POSTGRES_URL"), echo=True, client_encoding='utf8')
        # Create a session maker bound to this engine
        self.Session = sessionmaker(bind=self.engine)

    def pdf_to_text(self, uploaded_file, chunk_length: int = 1000) -> list:
        """
        Extracts text from the uploaded PDF and splits it into manageable chunks.

        Args:
        uploaded_file (UploadedFile): The PDF file uploaded by the user.
        chunk_length (int): The desired length of each text chunk.

        Returns:
        list: A list of text chunks ready for embedding generation.
        """
        # Extract text from the uploaded PDF
        text = pdf_extract_text(uploaded_file)
        # Split the text into chunks
        chunks = [text[i:i + chunk_length].replace('\n', '') for i in range(0, len(text), chunk_length)]
        return self._generate_embeddings(chunks)

    def define_vector_store(self, embeddings: list) -> bool:
        """
        Stores the generated embeddings in the database.

        Args:
        embeddings (list): A list of dictionaries containing text and their corresponding embeddings.

        Returns:
        bool: True if the operation succeeds, False otherwise.
        """
        session = self.Session()  # Create a new database session
        try:
            # Truncate the existing table and insert new embeddings
            session.execute(text("TRUNCATE TABLE pdf_holder RESTART IDENTITY CASCADE;"))
            for embedding in embeddings:
                # Insert each embedding into the pdf_holder table
                session.execute(text("INSERT INTO pdf_holder (text, embedding) VALUES (:text, :embedding)"), {"text": embedding["text"], "embedding": embedding["vector"]})
            session.commit()  # Commit the changes
            return True
        except ProgrammingError as e:
            if 'relation "pdf_holder" does not exist' in str(e.orig.pgerror):
                # If the table doesn't exist, create it and the necessary extension
                session.rollback()
                session.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                session.execute(text("""
                    CREATE TABLE pdf_holder (
                        id SERIAL PRIMARY KEY,
                        text TEXT,
                        embedding VECTOR(3072)
                    );
                """))
                session.commit()
                return False
            else:
                raise
        finally:
            session.close()  # Close the session

    def _generate_embeddings(self, chunks: list) -> list:
        """
        Generates embeddings for each text chunk using the OpenAI API.

        Args:
        chunks (list): A list of text chunks.

        Returns:
        list: A list of dictionaries containing text chunks and their corresponding embeddings.
        """
        try:
            # Generate embeddings for the text chunks
            response = openai.embeddings.create(model='text-embedding-3-large', input=chunks)
            return [{"vector": embedding_info.embedding, "text": chunks[embedding_info.index]} for embedding_info in response.data]
        except Exception as e:
            st.error(f"An error occurred during embeddings generation: {e}")
            return []

# Function to process the uploaded PDF before any user interaction
def process_pre_run(uploaded_file):
    """
    Orchestrates the preprocessing of the uploaded PDF file, including text extraction and embedding generation.

    Args:
    uploaded_file (UploadedFile): The PDF file uploaded by the user.
    """
    processor_class = PreRunProcessor()  # Instantiate the PreRunProcessor class
    embeddings = processor_class.pdf_to_text(uploaded_file)  # Extract text and generate embeddings
    if not embeddings or not processor_class.define_vector_store(embeddings):
        st.error("Failed to store the PDF embedding.")  # Notify if embedding storage fails
    else:
        st.success("PDF successfully uploaded. We can proceed now...")  # Notify on successful processing





##### Intent services #####

class IntentService:
    """
    Handles the detection of malicious intent in user queries, conversion of questions to embeddings,
    and checks the relatedness of questions to PDF content via database queries.
    """
    
    def __init__(self):
        """
        Initializes the IntentService with the OpenAI API key and a connection to a PostgreSQL database.
        """
        # Retrieve OpenAI API key from environment variables
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Establish a connection to the PostgreSQL database hosted on the Supabase platform
        self.engine = create_engine(os.getenv("SUPABASE_POSTGRES_URL"), echo=True, client_encoding='utf8')

    def detect_malicious_intent(self, question):
        """
        Uses OpenAI's moderation model to detect malicious intent in a user's question.

        Args:
            question (str): The user's question as a string.

        Returns:
            tuple: A boolean indicating if the question was flagged and a message explaining the result.
        """
        try:
            # Create a moderation request to OpenAI API with the provided question
            response = openai.moderations.create(model="text-moderation-latest", input=question)
            # Determine if the question was flagged as malicious
            is_flagged = response.results[0].flagged
            if is_flagged:
                # Return true and a message if flagged
                return is_flagged, "This question has been flagged for malicious or inappropriate content..."
            else:
                # Return false and a message if not flagged
                return is_flagged, "No malicious intent detected..."
        except Exception as e:
            # Return none and an error message in case of an exception
            return None, f"Error in moderation: {str(e).split('. ')[0]}."

    def query_database(self, query):
        """
        Executes a SQL query on the connected PostgreSQL database and returns the first result.

        Args:
            query (str): SQL query string to be executed.

        Returns:
            sqlalchemy.engine.row.RowProxy or None: The first result row of the query or None if no results.
        """
        # Connect to the database and execute the given query
        with self.engine.connect() as connection:
            result = connection.execute(text(query)).fetchone()
            # Return the result if available; otherwise, return None
            return result if result else None
    
    def question_to_embeddings(self, question):
        """
        Converts a user's question into vector embeddings using OpenAI's API.

        Args:
            question (str): The user's question as a string.

        Returns:
            list: The vectorized form of the question as a list or an empty list on failure.
        """
        try:
            # Generate embeddings for the question using OpenAI's API
            response = openai.embeddings.create(input=question, model="text-embedding-3-large")
            embedded_query = response.data[0].embedding
            # Verify the dimensionality of the embedding
            if len(embedded_query) != 3072:
                raise ValueError("The dimensionality of the question embedding does not match the expected 3072 dimensions.")
            else:
                # Convert the embedding to a numpy array and return it as a list
                return np.array(embedded_query, dtype=np.float64).tolist()
        except Exception as e:
            # Log and return an empty list in case of an error
            print(f"Error embedding the question: {e}")
            return []

    def check_relatedness_to_pdf_content(self, question):
        """
        Determines if a user's question is related to PDF content stored in the database by querying for similar embeddings.

        Args:
            question (str): The user's question as a string.

        Returns:
            tuple: A boolean indicating relatedness and a message explaining the result.
        """
        # Convert the question to vector embeddings
        question_vectorized = self.question_to_embeddings(question)
        
        try:
            # Query the database for the closest embedding to the question's embedding
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, text, embedding <=> CAST(:question_vector AS VECTOR) AS distance 
                    FROM pdf_holder
                    ORDER BY distance ASC
                    LIMIT 1;
                """), {'question_vector': question_vectorized}).fetchone()
                
                if result:
                    # Determine if the closest embedding is below a certain threshold
                    _, _, distance = result
                    threshold = 0.65  # Define a threshold for relatedness
                    if distance < threshold:
                        # Return true and a message if the question is related to the PDF content
                        return True, "Question is related to the PDF content..."
                    else:
                        # Return false and a message if the question is not sufficiently related
                        return False, "Question is not related to the PDF content..."
                else:
                    # Return false and a message if no embedding was found in the database
                    return False, "No match found in the database."
        except Exception as e:
            # Log and return false in case of an error during the database query
            print(f"Error searching the database: {e}")
            return False, f"Error searching the database: {e}"
        
        
##### Information retrieval service #####

class InformationRetrievalService:
    """
    Provides services for searching vectorized questions within a vector store in the database.
    """
    
    def __init__(self):
        """
        Initializes the InformationRetrievalService with OpenAI API key and database connection.
        """
        # Retrieve OpenAI API key from environment variables
        self.api_key = os.getenv("OPENAI_API_KEY")
        # Establish connection to the PostgreSQL database on the Supabase platform
        self.engine = create_engine(os.getenv("SUPABASE_POSTGRES_URL"), echo=True, client_encoding='utf8')
        # Create a session maker bound to this engine
        self.Session = sessionmaker(bind=self.engine)

    def search_in_vector_store(self, vectorized_question: str, k: int = 1) -> str:
        """
        Searches for the closest matching text in the vector store to a given vectorized question.
        
        Args:
            vectorized_question (str): The question converted into a vector.
            k (int): The number of top results to retrieve, defaults to 1.
        
        Returns:
            str: The text of the closest matching document or an error message if no match is found.
        """
        # SQL query to find the closest match in the vector store
        sql_query = text("""
            SELECT id, text, embedding <=> CAST(:query_vector AS VECTOR) AS distance
            FROM pdf_holder
            ORDER BY distance
            LIMIT :k
        """)
        # Execute the query with provided vectorized question and k value
        with self.engine.connect() as conn:
            results = conn.execute(sql_query, {'query_vector': vectorized_question, 'k': k}).fetchall()
            if results:
                # Return the text of the closest match if results are found
                return results[0].text
            else:
                # Display an error if no matching documents are found
                st.error("No matching documents found.")

##### Response service #####
class ResponseService:
    """
    Generates responses to user questions by integrating with OpenAI's ChatCompletion.
    """
    
    def __init__(self):
        """
        Initializes the ResponseService with the OpenAI API key.
        """
        # Load OpenAI API key from environment variables
        self.api_key = os.getenv("OPENAI_API_KEY")

    def generate_response(self, question, retrieved_info):
        """
        Generates a response using OpenAI's ChatCompletion API based on the provided question and retrieved information.
        
        Args:
            question (str): The user's question.
            retrieved_info (str): Information retrieved that is related to the question.
        
        Returns:
            str: The generated response or an error message if no response is available.
        """
        # Generate a response using the ChatCompletion API with the question and retrieved information
        response = openai.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "user", "content": 'Based on the FACTS, give a concise and detailed answer to the QUESTION.'+ 
                f'QUESTION: {question}. FACTS: {retrieved_info}'}
            ]
        )

        if response.choices and response.choices[0].message.content:
            # Return the generated response if available
            return response.choices[0].message.content
        else:
            # Display an error if no content is generated
            st.error("No content available.")
        
###### Independant & dependant of the function's class ######

# Securely uploads a file to Google Drive and ensures the temporary file is deleted after upload
def upload_to_google_drive(uploaded_file):
    """
    Uploads a file to Google Drive using service account credentials, makes it publicly viewable,
    and returns a shareable link for the uploaded file.
    
    Args:
        uploaded_file: The file uploaded by the user through the Streamlit interface.
    
    Returns:
        str: The shareable link of the uploaded file.
    """
    # Define the scope for Google Drive API access to allow file uploading and sharing.
    scope = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/drive']
    
    # Load Google Drive API credentials from Streamlit secrets (TOML format).
    # These credentials are stored securely and used to authenticate with Google Drive.
    credentials_info = st.secrets["google_credentials"]
    
    # Convert credentials info to a dictionary suitable for the oauth2client library.
    # This step formats the credentials in a way that GoogleAuth can use for authentication.
    credentials_dict = {key: value for key, value in credentials_info.items()}
    
    # Authenticate using the service account credentials to access Google Drive.
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    gauth = GoogleAuth()
    gauth.credentials = credentials  # Set the authenticated credentials
    drive = GoogleDrive(gauth)  # Create a GoogleDrive instance with authenticated GoogleAuth instance
    
    # Use a temporary file to store the uploaded file's content.
    # This approach avoids loading the entire file content into memory, which is efficient for large files.
    with tempfile.NamedTemporaryFile(delete=False, suffix='-' + uploaded_file.name) as temp_file:
        temp_file.write(uploaded_file.read())  # Write the uploaded file content to the temporary file
        temp_file_path = temp_file.name  # Store the path of the temporary file for later use in uploading
    
    try:
        # Create a new file on Google Drive using the uploaded file's name.
        file_drive = drive.CreateFile({'title': uploaded_file.name})
        # Set the content of the Google Drive file to that of the temporary file.
        file_drive.SetContentFile(temp_file_path)
        file_drive.Upload()  # Upload the file to Google Drive
        
        # Change the uploaded file's sharing settings to make it viewable by anyone with the link.
        file_drive.InsertPermission({
            'type': 'anyone',
            'value': 'anyone',
            'role': 'reader'
        })
        
        # Format the shareable link for preview.
        shareable_link = f"https://drive.google.com/file/d/{file_drive['id']}/preview"
        
        # Print the shareable link for testing purposes.
        st.write("Shareable link:", shareable_link)
        
    finally:
        # Ensure the temporary file is deleted after the upload process is complete.
        # This cleanup step prevents accumulation of temporary files on the server.
        os.unlink(temp_file_path)


# Orchestrates the processing of user questions regarding PDF content
def intent_orchestrator(service_class, user_question):
    """
    Orchestrates the process of checking a user's question for malicious intent and relevance to PDF content.
    
    Args:
        service_class: The class instance providing the services for intent detection and content relevance.
        user_question: The question posed by the user.
    
    Returns:
        A tuple containing the vectorized question and the original question if relevant, or (None, None) otherwise.
    """
    # Detect malicious intent in the user's question
    is_flagged, flag_message = service_class.detect_malicious_intent(user_question)
    st.write(flag_message)  # Display the flag message
    
    if is_flagged:
        # If the question is flagged, do not process further
        st.error("Your question was not processed. Please try a different question.")
        return (None, None)

    # Check if the question is related to the PDF content
    related, relatedness_message = service_class.check_relatedness_to_pdf_content(user_question)
    st.write(relatedness_message)  # Display the relatedness message
    
    if related:
        # If the question is related, proceed with processing
        vectorized_question = service_class.question_to_embeddings(user_question)
        st.success("Your question was processed successfully. Now fetching an answer...")
        return (vectorized_question, user_question)
    else:
        # If not related, do not process further
        st.error("Your question was not processed. Please try a different question.")
        return (None, None)

# Starts the question processing workflow
def process_user_question(service_class, user_question):
    """
    Initiates the processing of a user's question through various services.
    
    Args:
        service_class: The class instance providing services for processing the user's question.
        user_question: The question posed by the user.
    
    Returns:
        The result of the intent orchestration process.
    """
    # Orchestrates the intent processing of the user's question
    result = intent_orchestrator(service_class, user_question)
    return result

# Initiates the retrieval process for information related to the user's question
def process_retrieval(vectorized_question: str) -> tuple:
    """
    Retrieves information related to the vectorized question from the vector store.
    
    Args:
        vectorized_question (str): The vectorized form of the user's question.
    
    Returns:
        Retrieved information related to the user's question.
    """
    service = InformationRetrievalService()
    retrieved_info = service.search_in_vector_store(vectorized_question)
    return retrieved_info

# Generates a response based on the user's question and the retrieved information
def process_response(retrieved_info, question):
    """
    Generates a response to the user's question based on retrieved information.
    
    Args:
        retrieved_info: Information related to the user's question retrieved from the vector store.
        question: The original question posed by the user.
    
    Returns:
        A generated response to the user's question.
    """
    response_service_processor = ResponseService()
    final_response = response_service_processor.generate_response(question, retrieved_info)
    return final_response
        
        
def main():
    """
    The main function to run the Streamlit app, including a PDF viewer.
    """
    # Display the app's title
    st.title("Talk to your PDF")
    
    # Create a file uploader widget for PDF files
    uploaded_file = st.file_uploader("Upload your PDF", type=["pdf"])
    
    # Check if a file has been uploaded
    if uploaded_file is not None:
        # Display an animation while processing the uploaded PDF
        with st_lottie_spinner(loading_animation, quality='high', height='100px', width='100px'):
            process_pre_run(uploaded_file)  # Preprocess the uploaded file
        
        # Securely upload the processed file to Google Drive
        upload_to_google_drive(uploaded_file)
        
        # Instantiate the service class for intent processing
        service_class = IntentService()
        
        # Create a form for user's questions about the PDF content
        with st.form(key='question_form'):
            user_question = st.text_input("Ask a question about the PDF content:", key="question_input")
            submit_button = st.form_submit_button(label='Ask')
        
        # Process the question if the submit button is pressed
        if submit_button:
            result = process_user_question(service_class, user_question)
            
            if result[0] is not None:  # If the question is related to the PDF content
                vectorized_question, question = result
                
                with st_lottie_spinner(loading_animation, quality='high', height='100px', width='100px'):
                    retrieved_info = process_retrieval(vectorized_question)  # Retrieve relevant information
                    
                    final_response = process_response(retrieved_info, question)  # Generate and display response
                    st.write(final_response)

            
# Entry point of the Streamlit app
if __name__ == '__main__':
    main()
