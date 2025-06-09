import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential
import os
import pandas as pd
from dotenv import load_dotenv

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1))
def configure_gemini_model():
    load_dotenv()
    API_KEY = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=API_KEY)
    """Configura o modelo Gemini com retentativas"""
    return genai.GenerativeModel(
        model_name="models/gemini-2.5-flash-preview-05-20",
        generation_config={
            "temperature": 0.0,
            "top_p": 0.95,
            "response_mime_type": "application/json"
        }
    )
