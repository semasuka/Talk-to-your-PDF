import streamlit as st
import os, sys

# Assuming your Python conversion scripts are correctly placed in 'python_script_repository'
sys.path.append('python_script_repository')

from pre_run_service import process_pre_run
from intent_service import IntentService, process_user_question
from information_retrieval_service import process_retrieval
from response_service import process_response

def save_uploaded_file(uploaded_file):
    try:
        with open(os.path.join("pdf_folder", uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except Exception as e:
        st.error(f"An error occurred while saving the file: {e}")
        return False

def main():
    st.title("Talk to Your PDF")

    uploaded_file = st.file_uploader("Upload your PDF", type=["pdf"])

    if uploaded_file is not None:
        if save_uploaded_file(uploaded_file):
            st.success("File uploaded successfully.")
            if process_pre_run("pdf_folder"):
                user_question = st.text_input("Ask a question about the PDF content:")
                ask_button = st.button('Ask')
                if ask_button and user_question:
                    # logic here

# Run the app
if __name__ == '__main__':
    main()

