import streamlit as st
import os, sys
from pathlib import Path

# Assuming your Python conversion scripts are correctly placed in 'python_script_repository'
sys.path.append('python_script_repository')

from pre_run_service import process_pre_run
from intent_service import process_user_question
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

    # File uploader widget
    uploaded_file = st.file_uploader("Upload your PDF", type=["pdf"])
    
    # Once the file is uploaded and saved successfully, only then show the text input
    if uploaded_file is not None:
        if save_uploaded_file(uploaded_file):
            st.success("File uploaded successfully.")

            # Perform the pre-run process
            if process_pre_run("pdf_folder"):
                st.success("Pre-run processing complete.")
                
                # Only display the text input after successful upload and pre-run processing
                user_question = st.text_input("Ask a question about the PDF content:")
                
                if user_question:  # If statement to ensure that the user has entered a question
                    vectorized_question, original_question = process_user_question()
                    retrieved_info = process_retrieval(vectorized_question)
                    final_response = process_response(original_question, retrieved_info)
                    
                    if final_response:
                        st.subheader("Question:")
                        st.write(original_question)
                        st.subheader("Answer:")
                        st.write(final_response)
                    else:
                        st.error("Unable to generate a response.")
            else:
                st.error("Pre-run service failed. Please check the setup and try again.")

# Run the app
if __name__ == '__main__':
    main()
