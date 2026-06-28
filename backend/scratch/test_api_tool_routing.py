import httpx
import json

def test_chat_api(prompt: str):
    url = "http://localhost:8001/chat/"
    payload = {
        "message": prompt,
        "provider": "ollama",
        "model": "llama3.2:3b"
    }
    
    try:
        r = httpx.post(url, json=payload, timeout=60.0)
        print(f"\nPrompt: '{prompt}'")
        print("Status Code:", r.status_code)
        if r.status_code == 200:
            data = r.json()
            print("Response:", json.dumps(data.get("response"), indent=2))
            print("Tool Calls Executed:", json.dumps(data.get("tool_calls_executed"), indent=2))
        else:
            print("Error Text:", r.text)
    except Exception as e:
        print("Request failed:", e)

if __name__ == "__main__":
    print("Testing Live Chat API endpoints on port 8001...")
    test_chat_api("Don't use rag lookup, web search or calculator. Tell me a joke.")
    test_chat_api("Tell me a joke.")
    test_chat_api("Who won the FIFA World Cup in 2022?")
    test_chat_api("What is 25 * 36?")
