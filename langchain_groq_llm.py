import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# Load environment variables
load_dotenv()

def get_llm(model_name):
    """
    Returns a configured ChatGroq LLM instance.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables.")

    # Initialize Groq LLM
    llm = ChatGroq(
        groq_api_key=api_key,
        model_name=model_name,
        temperature=0, # Deterministic for SQL generation
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
    return llm
