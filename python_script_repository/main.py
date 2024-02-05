#!/usr/bin/env python
# coding: utf-8

# In[4]:


import import_ipynb
from pre_run_service import process_pre_run
from intent_service import process_user_question
from information_retrieval_service import process_retrieval
from response_service import process_response


# In[5]:


def main():
    # Define the directory path containing PDFs
    DIRECTORY_PATH = '/Users/sternsemasuka/Desktop/ML/Project/Talk-to-your-PDF/pdf_folder/'
    
    # Start the pre-run service and proceed only if it returns True
    if process_pre_run(DIRECTORY_PATH):
        # Retrieve the vectorized question and original question from the intent service
        vectorized_question, original_question = process_user_question()

        # Retrieve information based on the vectorized question
        retrieved_info = process_retrieval(vectorized_question)

        # Generate the final response using the retrieved information
        final_response = process_response(original_question, retrieved_info)

        # Print the final response with start lines around the question and answer
        print("\n") 
        print("********** Question **********")  # Start line for the question
        print("\n") 
        print(f"{original_question}")  # The question itself
        print("\n") 
        print("********** Answer **********")  # Start line for the answer
        print("\n") 
        print(f"{final_response}")  # The answer

    else:
        print("Pre-run service failed. Please check the setup and try again.")


# In[6]:


# Ensure this script runs as the main program
if __name__ == "__main__":
    main()


# In[ ]:




