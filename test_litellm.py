import litellm
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    try:
        resp = await litellm.acompletion(
            model="gemini/gemini-2.0-flash",
            messages=[{"role": "user", "content": "hi"}],
        )
        print("Success:", resp.choices[0].message.content)
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
