# Chatbot Framework Backend Skeleton

This directory contains the FastAPI backend skeleton for the MCP-enabled chatbot framework. It features basic API structures, configs, CORS middleware, and endpoint stubs for messaging, tool registration/execution, resource ingestion, and feedback collection.

---

## 1. Prerequisites
Make sure you have python installed (Python 3.10+ is recommended).
- **Windows**: [Python for Windows](https://www.python.org/downloads/windows/)
- **macOS/Linux**: Pre-installed or install via `brew` / `apt`.

---

## 2. Setup Instructions

Follow these steps to set up and run the backend locally:

### Step 1: Navigate to the backend directory
Open your terminal and navigate to the backend folder:
```bash
cd backend
```

### Step 2: Create a virtual environment
Create a virtual environment (`venv`) to keep your dependencies isolated:
```bash
# Windows (Command Prompt or PowerShell)
python -m venv venv

# macOS / Linux
python3 -m venv venv
```

### Step 3: Activate the virtual environment
Activate the environment to use the local context:
```bash
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.\venv\Scripts\activate.bat

# macOS / Linux
source venv/bin/activate
```
*(You should see `(venv)` prepended to your command prompt).*

### Step 4: Install dependencies
Install the required Python packages from the requirements list:
```bash
pip install -r requirements.txt
```

### Step 5: Configure environment variables
Copy the example environment file into a local configuration:
```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# Windows (Command Prompt)
copy .env.example .env

# macOS / Linux
cp .env.example .env
```
Open `.env` in your editor to change configuration defaults (e.g. database URLs or LLM API hosts) if necessary.

### Step 6: Start the development server
Run the FastAPI application with `uvicorn` and hot-reloads enabled:
```bash
uvicorn app.main:app --reload --port 8000
```
- `--reload`: Auto-reloads the server when you change backend code.
- `--port 8000`: Runs the server on local port `8000`.

---

## 3. What & How to Test

Once the server is running on `http://localhost:8000`, there are multiple ways to test the application endpoints.

### Option A: The Interactive Swagger UI (Recommended)
FastAPI automatically generates interactive API documentation. 
1. Open your browser and navigate to: **[http://localhost:8000/docs](http://localhost:8000/docs)**
2. You will see a web interface listing all endpoints grouped by tags (Chat, Tools, Resources, Feedback).
3. Click on any endpoint, click the **"Try it out"** button in the upper right, fill in the parameters, and click **"Execute"**. You will see the server request URL, response headers, and response payload.

### Option B: Terminal testing via `curl`
You can test each endpoint directly using terminal commands.

#### 1. Uptime / Health Checks
- **Health Endpoint**:
  ```bash
  curl http://localhost:8000/health
  ```
  *Expected Output:* `{"status":"healthy"}`

- **Root Landing Endpoint**:
  ```bash
  curl http://localhost:8000/
  ```
  *Expected Output:* `{"message":"Chatbot Framework API is running. Visit /docs for Swagger UI"}`

#### 2. Chat Endpoint (`/chat/`)
This is the main conversation route.
```bash
curl -X POST http://localhost:8000/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Chatbot!", "session_id": "test-session-001"}'
```
*Expected Output:*
```json
{
  "response": "Echo: Hello Chatbot!. (Skeleton - LLM integration coming in Week 2)",
  "session_id": "test-session-001",
  "tool_calls": []
}
```

#### 3. Tool Ingestion & Executions (`/tool/...`)
- **Register a tool description**:
  ```bash
  curl -X POST http://localhost:8000/tool/register \
    -H "Content-Type: application/json" \
    -d '{"name": "fetch_weather", "description": "Fetches current temperature", "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}'
  ```
  *Expected Output:* `{"status": "registered", "tool": "fetch_weather"}`

- **Execute a tool target**:
  ```bash
  curl -X POST http://localhost:8000/tool/execute \
    -H "Content-Type: application/json" \
    -d '{"tool_name": "fetch_weather", "parameters": {"city": "New York"}}'
  ```
  *Expected Output:* `{"result": "Executed fetch_weather with params {'city': 'New York'}"}`

#### 4. Document Ingestion / RAG uploads (`/resource/...`)
Tests upload functionality of file context vectors. Create a temporary text file (e.g. `test.txt`) and run:
```bash
# Windows PowerShell
New-Item -Path . -Name "test.txt" -ItemType "file" -Value "Sample Knowledge Text"
curl -Method Post -Uri http://localhost:8000/resource/upload -Form "file=@test.txt"
Remove-Item test.txt

# macOS / Linux / Bash
echo "Sample Knowledge Text" > test.txt
curl -X POST http://localhost:8000/resource/upload -F "file=@test.txt"
rm test.txt
```
*Expected Output:* `{"filename":"test.txt","status":"uploaded (stub)"}`

#### 5. Chat Response Feedback (`/feedback/`)
Submit feedback for quality assessment:
```bash
curl -X POST http://localhost:8000/feedback/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-session-001", "rating": 5, "comment": "Excellent answer!"}'
```
*Expected Output:* `{"status": "feedback received", "rating": 5}`

---

## 4. Troubleshooting
- **Port already in use**: If port 8000 is occupied, you will see a `Bind for 0.0.0.0:8000 failed` error. You can run uvicorn on another port, for example: `uvicorn app.main:app --reload --port 8080`.
- **Imports failure**: Ensure you activated the virtual environment and ran `pip install -r requirements.txt` prior to booting uvicorn. Always run `uvicorn` from the `backend/` directory so the package resolver finds the `app/` modules correctly.
