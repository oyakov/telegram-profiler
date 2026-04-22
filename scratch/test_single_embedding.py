import asyncio
import os
import sys
sys.path.append(os.getcwd())
from src.ai.embeddings import generate_embedding

async def main():
    print("Testing single embedding generation...")
    # Override for host execution
    os.environ["LMSTUDIO_BASE_URL"] = "http://localhost:1234/v1"
    try:
        text = "Hello Belgrade, this is a test for embedding generation stability."
        vector = await generate_embedding(text)
        print(f"Success! Vector length: {len(vector)}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
