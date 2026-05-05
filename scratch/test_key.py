import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

key = os.environ.get("GROQ_API_KEY")
print(f"Testing key: {key[:10]}...{key[-5:]}")

client = Groq(api_key=key)

try:
    models = client.models.list()
    print("SUCCESS: Key is valid!")
except Exception as e:
    print(f"FAILURE: Key is invalid: {e}")
