import httpx
import json
import asyncio

async def test_query(prompt: str):
    tools = [
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Safely evaluates simple mathematical expressions (+, -, *, /, parentheses).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "The arithmetic expression to evaluate"
                        }
                    },
                    "required": ["expression"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Mocks a web search to fetch summaries on a query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The web search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "rag_lookup",
                "description": "Queries the local document knowledge base using vector semantic search.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to retrieve contextual fragments"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]

    # Detailed multiline system prompt
    system_prompt = """You are a helpful AI assistant.

You have access to these tools:

1. calculator
   Use ONLY for mathematical computations.

2. search_web
   Use ONLY for current or real-time internet information.

3. rag_lookup
   Use ONLY for uploaded documents.

IMPORTANT:
- Most user requests DO NOT require tools.
- If you can answer directly, do NOT call any tool.
- Never call calculator for jokes, greetings, explanations, coding, writing, or conversation.
- Never call search_web for general knowledge.
- Never call rag_lookup unless the answer depends on uploaded documents.

Before selecting a tool:
1. Can I answer directly? If YES, answer directly.
2. Does it require math? If YES, calculator.
3. Does it require uploaded documents? If YES, rag_lookup.
4. Does it require current internet information? If YES, search_web.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    payload = {
        "model": "llama3.2:3b",
        "messages": messages,
        "stream": False,
        "tools": tools,
        "options": {
            "temperature": 0.0  # Use low temperature for testing tool calling stability
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post("http://localhost:11434/api/chat", json=payload)
        data = response.json()
        message = data.get("message", {})
        print(f"\nPrompt: '{prompt}'")
        print("Response Content:", json.dumps(message.get("content", "")))
        print("Response Tool Calls:", json.dumps(message.get("tool_calls", []), indent=2))

async def main():
    await test_query("Don't use rag lookup, web search or calculator. Tell me a joke.")
    await test_query("Who won the FIFA World Cup in 2022?")
    await test_query("What is 25 * 36?")

if __name__ == "__main__":
    asyncio.run(main())
