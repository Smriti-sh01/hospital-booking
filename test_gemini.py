import asyncio
import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    try:
        resp = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents="hello",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        print("SUCCESS:", resp.text)
    except Exception as e:
        print("ERROR:", repr(e))

asyncio.run(main())
