#!/usr/bin/env python
# coding: utf-8

# In[34]:


import openai, os
from dotenv import load_dotenv


# In[43]:


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
        print("No content available.")


# In[ ]:


def process_response(question, retrieved_info):
    response_service_processor = ResponseService()
    final_response = response_service_processor.generate_response(question, retrieved_info)
    return final_response

