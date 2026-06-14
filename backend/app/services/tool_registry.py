# Simple in-memory tool registry for Week 1
tools = {}

def register_tool(name: str, description: str, parameters: dict):
    tools[name] = {
        "description": description,
        "parameters": parameters
    }
    return {"status": "ok"}