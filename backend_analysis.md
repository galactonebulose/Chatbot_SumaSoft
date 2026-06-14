# Backend Architecture Analysis & Explanation Guide

This guide provides a comprehensive walkthrough of the backend codebase, structured to help you understand the architecture from a high level, followed by a detailed file-by-file analysis. Use this to prepare for reviews or presentations.

---

## 1. High-Level Architecture Overview

The backend is structured as a **FastAPI** web application designed as a skeleton for a Chatbot Framework supporting:
1. **Tool Calling (MCP - Model Context Protocol)**: Dynamically exposing capabilities (tools) to a Large Language Model (LLM).
2. **RAG (Retrieval-Augmented Generation)**: Ingesting and querying documents (PDF, DOCX, etc.) to ground the chatbot's answers.
3. **Multi-Database Configuration**: Incorporating both **PostgreSQL** (relational database for chat sessions, feedback, and user profiles) and **MongoDB** (document database for chat logs, messages, and unstructured tool executions/RAG chunks).

### Core Design Patterns
- **Separation of Concerns (MVC-like / Router-Service-Model)**: Routes are separated into the [app/api/](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/api) directory. Business logic is placed in [app/services/](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/services), configurations in [app/core/](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/core), and database schemas in [app/models/](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/models).
- **Dependency Injection**: Utilizes FastAPI's `Depends` mechanism (to be fully integrated with DB sessions and authentication in subsequent weeks).
- **Settings Management**: Employs Pydantic's `BaseSettings` for strongly typed configuration validation via environment variables (`.env`).

---

## 2. Detailed File-by-File Breakdown

### 2.1. Project Roots & Configuration

#### `[config.py]`([backend/app/core/config.py](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/core/config.py))
This file defines the configuration system of the application using `pydantic-settings`.
- **`Settings` class**: Inherits from `BaseSettings`. It defines configuration variables with default values.
  - `PROJECT_NAME`: Title of the application.
  - `API_V1_STR`: The prefix version.
  - `POSTGRES_URL` & `MONGO_URL`: Connection strings for PostgreSQL and MongoDB databases, allowing the application to persist data across dual storage systems.
  - `LLM_API_BASE`: Endpoint for LLM interaction (e.g., local Ollama instance running at `http://localhost:11434`).
  - `OPENAI_COMPATIBLE_API_KEY`: API key if utilizing cloud LLM providers.
- **`Config` sub-class**: Configured to load variables from a `.env` file and enforce case-sensitivity.
- **`settings` instance**: Instantiated globally, serving as a singleton config object imported by other files.

#### `[main.py]`([backend/app/main.py](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/main.py))
The entry point of the FastAPI application.
1. **FastAPI Initialization**: Creates the `app` instance, defining metadata such as the API title, description, and version.
2. **CORS Middleware**: Adds `CORSMiddleware` to allow cross-origin requests. It is set to `allow_origins=["*"]` (wildcard) for development ease, enabling frontends (e.g., React/Vue) running on different ports to communicate with this API.
3. **Router Inclusions**: Registers routers for each logic area under a specific URL prefix and Swagger tag:
   - `/chat` -> `chat.router`
   - `/tool` -> `tools.router`
   - `/resource` -> `resources.router`
   - `/feedback` -> `feedback.router`
4. **Utility Routes**:
   - `GET /`: Root message directing developers to `/docs` for the Swagger UI documentation.
   - `GET /health`: Basic health-check endpoint returning `{"status": "healthy"}`.

---

### 2.2. API Routers (`app/api/`)

#### `[chat.py]`([backend/app/api/chat.py](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/api/chat.py))
Handles chatbot messaging endpoints.
- **Data Models**:
  - `ChatRequest`: Validates client payload. Expects `message` (string) and an optional `session_id` (string).
  - `ChatResponse`: Standardizes JSON response back to the client. Contains `response` (string), `session_id` (string), and `tool_calls` (list).
- **`POST /chat/`**: Currently acts as a placeholder stub. It returns an "Echo" message to verify communication between frontend and backend. In the future, this endpoint will process history, search database contexts (RAG), trigger tools, and call LLMs.

#### `[tools.py]`([backend/app/api/tools.py](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/api/tools.py))
Exposes endpoints to register and execute agentic tools.
- **Data Models**:
  - `ToolRegisterRequest`: Validates tool registrations. Expects `name`, `description`, and a schema map of its `parameters`.
  - `ToolExecuteRequest`: Validates execution requests. Expects the target `tool_name` and execution argument `parameters` dictionary.
- **`POST /tool/register`**: Endpoint designed for registering new system or MCP tools.
- **`POST /tool/execute`**: Endpoint designed to execute a specific tool with parameters dynamically supplied by the model during a chat invocation.

#### `[resources.py]`([backend/app/api/resources.py](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/api/resources.py))
Manages content uploads for Retrieval-Augmented Generation (RAG).
- **`POST /resource/upload`**: Takes an uploaded file (`UploadFile`) through `multipart/form-data` format. This will eventually feed into a file parsing pipeline (PDF, DOCX text extraction), chunking process, and vector insertion logic.

#### `[feedback.py]`([backend/app/api/feedback.py](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/api/feedback.py))
Enables quality analysis of chatbot responses.
- **Data Models**:
  - `FeedbackRequest`: Validates client feedback inputs. Expects `session_id` (string), `rating` (integer - e.g., thumbs-up/down or 1 to 5), and an optional text `comment`.
- **`POST /feedback/`**: Stub endpoint that intercepts user responses for storage in PostgreSQL/MongoDB to enable analytical reporting.

---

### 2.3. Models & Services

#### `[base.py]`([backend/app/models/base.py](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/models/base.py))
Defines the base class for relational database schemas.
- **`Base` Class**: Inherits from SQLAlchemy's `DeclarativeBase`. In SQLAlchemy 2.0+, `DeclarativeBase` is the recommended way to declare models. Any database schema defined later (e.g. `User`, `ChatSession`, `Feedback`) will inherit from this `Base` class, ensuring database engine engines can detect table metadata automatically.

#### `[tool_registry.py]`([backend/app/services/tool_registry.py](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/services/tool_registry.py))
Implements a simple service module.
- **In-Memory Registry**: Uses a global dictionary `tools = {}` to store tool definitions temporarily.
- **`register_tool()`**: Service function that populates the in-memory cache with tool metadata. Note: Being in-memory, the list is reset upon application restart. A database layer or dynamic directory scan will replace this in subsequent project phases.

---

## 3. Complete API Specifications

The following table summarizes the existing endpoints defined in this skeleton app:

| Endpoint | Method | Input Model / Format | Output Format | Purpose | Status (Week 1) |
|---|---|---|---|---|---|
| `GET /` | GET | None | `{"message": "..."}` | Root landing message | Functional |
| `GET /health` | GET | None | `{"status": "healthy"}` | Health & uptime checker | Functional |
| `POST /chat/` | POST | `ChatRequest` | `ChatResponse` | Start conversation / chat message | Echo Stub |
| `POST /tool/register` | POST | `ToolRegisterRequest` | `{"status": "...", "tool": "..."}` | Register capability/tool parameters | Stub |
| `POST /tool/execute` | POST | `ToolExecuteRequest` | `{"result": "..."}` | Run tool with user parameters | Stub |
| `POST /resource/upload` | POST | `Multipart/Form-Data` | `{"filename": "...", "status": "..."}` | Upload files (PDF/DOCX) for RAG context | Stub |
| `POST /feedback/` | POST | `FeedbackRequest` | `{"status": "...", "rating": ...}` | Capture user response evaluation | Stub |

---

## 4. Architectural Roadmap (How Everything Fits Together Later)

When explaining this codebase to your reviewer, it's critical to show that you understand **where** the code is going, not just what it is now:

1. **How the LLM integrates (Week 2)**:
   In `app/api/chat.py`, when a user posts a message:
   - We will fetch the chat history for that `session_id`.
   - We will query the LLM configured in `settings.LLM_API_BASE`.
   - If the LLM determines a tool is needed, it returns a tool call request.
   
2. **How Tool calling executes (Week 2)**:
   - The backend checks the `tool_registry.py` cache to verify if the tool name requested by the LLM is registered.
   - The system invokes the tool internally or reaches out to an external MCP (Model Context Protocol) server over a transport layer.
   - The results of the tool execution are sent back to the LLM so it can formulate the final answer.

3. **How RAG works (Week 3)**:
   - When a user uploads a PDF using `POST /resource/upload`, the backend will chunk the document and generate vector embeddings.
   - These embeddings are stored in a Vector DB (e.g. PgVector or Chroma).
   - During `POST /chat/`, we search this database first for context, prepend it to the LLM prompt, and then query the model (Semantic Search Retrieval).

4. **How Database connections are managed**:
   - PostgreSQL will be bound using SQLAlchemy engine pools, exposing database sessions via FastAPI dependencies (`Depends`).
   - MongoDB will store raw unstructured logs (like LLM input/output payloads and tool logs) which are natural document shapes.

---

## 5. Quick Verification Commands

To run this backend application locally:
```powershell
# Navigate to the backend folder
cd backend

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt

# Run the developer server
uvicorn app.main:app --reload --port 8000
```
Once started, the reviewer can visit `http://localhost:8000/docs` to see the interactive Swagger UI testing environment generated directly from the Pydantic schemas.
