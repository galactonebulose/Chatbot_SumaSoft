import asyncio
from app.services.llm_service import LLMService

async def test_llm():
    print("Testing LLM Service...\n")
    
    # Use the model you actually have
    llm = LLMService.get_provider("ollama", model_name="llama3.2:3b")
    
    print(f"✅ Provider initialized: {llm.get_config()}")
    
    # Test simple generate
    try:
        print("\n🤖 Generating response...")
        response = await llm.generate("Hello, who are you? Reply in one short sentence.")
        print("Response:", response.strip())
        print("\n✅ Success! LLM is working.")
    except Exception as e:
        print("❌ Error:", str(e))

if __name__ == "__main__":
    asyncio.run(test_llm())