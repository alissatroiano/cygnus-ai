import asyncio
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

async def test():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"), http_options={'api_version': 'v1beta'})
    try:
        async with client.aio.live.connect(model="gemini-2.0-flash-exp") as session:
            print("Connected!")
            # Just test if receive() exists and is an async iterator
            it = session.receive()
            print(f"Receive type: {type(it)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
