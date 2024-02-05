import streamlit as st
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


lottie_animation = load_lottieurl('https://lottie.host/d9f965d0-4be7-4d22-a30f-6a47e4b21d21/WrGKrQJxly.json')


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
    processor = PreRunProcessor()
    # Pass each file to the pdf_to_text function
    embeddings = processor.pdf_to_text(uploaded_file)
    if not embeddings or not processor.define_vector_store(embeddings):
        st.error("Failed to store the PDF embedding.")
    else:
        st.success("PDF successfully uploaded. We can proceed now...")




#########################################################





def main():
    st.title("Talk to Your PDF")

    uploaded_file = st.file_uploader("Upload your PDF", type=["pdf"])
    if uploaded_file is not None:
        # run the animation while process_pre_run is running
        with st_lottie_spinner(lottie_animation, quality='high', height='100px', width='100px'):
            process_pre_run(uploaded_file)
        user_question = st.text_input("Ask a question about the PDF content:")
        ask_button = st.button('Ask')
        if ask_button and user_question:
            # logic here
            pass






# Run the app
if __name__ == '__main__':
    main()
