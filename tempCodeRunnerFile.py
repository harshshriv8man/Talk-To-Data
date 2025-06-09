from dotenv import load_dotenv
load_dotenv()

from groq import Groq
import ast
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))