# 🌟 Multi-Agent Chatbot Framework with Tool Calling & RAG

Welcome to the **Chatbot Framework** application. This is a fully featured, production-ready implementation of a multi-agent chatbot system supporting:
- **Model Context Protocol (MCP) & Tool Calling**: Enables LLMs to dynamically run local or remote capabilities (such as built-in calculators, web searches, or custom APIs).
- **Retrieval-Augmented Generation (RAG)**: Allows users to ingest documents (PDFs, text files), parse and chunk them, compute vector embeddings, and store/retrieve relevant segments to ground chat conversations.
- **Flexible LLM Provider Configuration**: Hot-swappable AI provider settings, with support for local models via **Ollama**, or cloud providers including **OpenAI**, **Anthropic**, and **Groq**.
- **Dual database + Vector storage**: Uses **PostgreSQL** for relational metadata (sessions, tools, feedback, config), **MongoDB** for unstructured message streams, and **Qdrant** for semantic vector indices.

For architectural diagrams and specs, see the [docs/](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/docs) directory:
- [API Specification](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/docs/API_SPEC.md)
- [Architecture diagram.svg](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/docs/Architecture%20diagram.svg)
- [Final Chatbot Architecture.svg](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/docs/Final%20Chatbot%20Architechture.svg)

---

## 🛠️ Architecture & Tech Stack

```mermaid
graph TD
    User([User Browser]) <-->|WebSockets & HTTP| FE[React + Vite Frontend]
    FE <-->|API Calls| BE[FastAPI Backend]
    
    subgraph Data Layer
        BE <-->|Metadata & Setup| PG[(PostgreSQL)]
        BE <-->|Chat Logs & History| MG[(MongoDB)]
        BE <-->|Document Embeddings| QD[(Qdrant Vector DB)]
    end
    
    subgraph AI & Tooling
        BE <-->|Generate / Stream| LLM[LLM Service: Ollama/OpenAI/Groq]
        BE <-->|Parse / Chunk| Parser[Chunking Parser]
        BE <-->|Run Capabilities| Exec[Tool Calling Executor]
    end
```

### Components
*   **Frontend**: React 18, Vite (for fast dev builds and HMR), Material UI (MUI) for a premium, clean design. Communication occurs via REST APIs and real-time WebSockets.
*   **Backend**: FastAPI (Python 3.10+) utilizing asynchronous routers, Dependency Injection (SQLAlchemy DB sessions), and standard schemas via Pydantic.
*   **Relational Storage (PostgreSQL)**: Handles structured tables for `tools`, `chat_sessions`, `feedbacks`, and `llm_configs` inside [schemas.py](file:///c:/SDriveStuff/Internship/SumaSoft/chatbot-framework-skeleton-final-v2/chatbot-framework/backend/app/models/schemas.py).
*   **Document Storage (MongoDB)**: Saves detailed message histories (`chat_messages`) in standard JSON document structures.
*   **Vector Search (Qdrant)**: High-performance vector database to index and search RAG chunks.

---

## 📋 Prerequisites

Before running the project, make sure you have the following installed on your machine:
*   [Git](https://git-scm.com/downloads)
*   [Python 3.10+](https://www.python.org/downloads/)
*   [Node.js v18+](https://nodejs.org/) & `npm`
*   [Docker](https://www.docker.com/products/docker-desktop/) (recommended for database engines and containerized deployment)
*   [Ollama](https://ollama.com/) (if running models locally)

---

## 🚀 Getting Started: Step-by-Step Setup

Follow these setup steps in order to download, install, configure, and launch the application.

### Step 1: Clone the Git Repository

Open your terminal and clone the repository to your local machine, then navigate to the root directory of the project:

```bash
# Clone the repository
git clone <repository_url>

# Navigate into the project folder
cd chatbot-framework
```

---

### Step 2: Spin Up Infrastructure (Databases)

The application relies on **PostgreSQL**, **MongoDB**, and **Qdrant**. The repository includes a `docker-compose.yml` file to quickly spin these services up in Docker.

#### 1. The `docker-compose.yml` Configuration
The following compose setup defines the containers, ports, and volumes:

```yaml
version: '3.8'

services:
  # Relational Database (PostgreSQL)
  postgres:
    image: postgres:15-alpine
    container_name: chatbot-postgres
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: chatbot
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  # Document Database (MongoDB)
  mongodb:
    image: mongo:latest
    container_name: chatbot-mongo
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db
    restart: unless-stopped

  # Vector Database (Qdrant)
  qdrant:
    image: qdrant/qdrant:latest
    container_name: chatbot-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local
  mongo_data:
    driver: local
  qdrant_data:
    driver: local
```

#### 2. Start the Databases
In the root directory, start the services in detached mode:

```bash
docker compose up -d
```
*This command pulls the lightweight alpine images, starts them in the background, maps database ports, and mounts local volumes to ensure all data is permanently persisted on your disk.*

#### 3. Configure Local LLM (Ollama)
If you intend to use a local LLM, install Ollama and pull your target model:

```bash
ollama pull llama3.2:3b
```
Ensure Ollama is running in the background (accessible at `http://localhost:11434`).

---

### Step 3: Backend Setup

Navigate to the `backend/` directory, set up your Python virtual environment, install dependencies, and configure the environment variables.

#### 1. Set Up Virtual Environment & Dependencies
```bash
# Navigate to the backend directory
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On Windows (Command Prompt):
.\venv\Scripts\activate.bat
# On macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configure Environment Variables
Copy the template `.env.example` file to `.env`:
```bash
# On Windows (PowerShell):
Copy-Item .env.example .env
# On Windows (Command Prompt/Bash):
copy .env.example .env
# On macOS / Linux:
cp .env.example .env
```

Open the created `.env` file in your text editor. Ensure it points to your local database URLs:
```env
POSTGRES_URL=postgresql://user:pass@localhost:5432/chatbot
MONGO_URL=mongodb://localhost:27017/chatbot
QDRANT_URL=http://localhost:6333
LLM_API_BASE=http://localhost:11434
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_MODEL_NAME=llama3.2:3b

# For cloud model testing (optional):
# OPENAI_API_KEY=sk-proj-YOURKEYHERE...
# GROQ_API_KEY=gsk_YOURKEYHERE...
```

#### 3. Start the Backend Server
Run the FastAPI development server with `uvicorn`:
```bash
uvicorn app.main:app --reload --port 8000
```
> [!NOTE]
> On startup, the backend automatically connects to PostgreSQL and runs migrations/initializations (`Base.metadata.create_all`) to create relational tables. If PostgreSQL is offline, it will output a warning and fall back to a local SQLite database file `chatbot.db`.

---

### Step 4: Frontend Setup

Open a new terminal window to set up and run the React client.

```bash
# Navigate to the frontend directory
cd frontend

# Install Node modules
npm install

# Start the Vite development server
npm run dev
```

The frontend will run at **[http://localhost:5173](http://localhost:5173)**. 
Vite is preconfigured in `vite.config.js` to proxy calls from `/api`, `/chat`, `/tool`, `/resource`, and `/feedback` to the backend running at `http://localhost:8000`.

---

## 🐳 Dockerization & Containerized Execution

If you prefer to run the entire backend and frontend inside containers rather than local installations, you can use the configured `Dockerfile`s in each directory.

### 1. Backend Dockerfile (`backend/Dockerfile`)
The backend is packaged into a lightweight Python image:
```dockerfile
# Use official lightweight Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Frontend Dockerfile (`frontend/Dockerfile`)
The frontend uses a multi-stage build, generating production assets and serving them via Nginx:
```dockerfile
# Build stage
FROM node:18-alpine AS build

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy project files
COPY . .

# Build app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets from build stage to nginx server directory
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 3. Full-Stack Docker Compose (Optional Build Configuration)
To build and run the entire stack (FastAPI + React + Databases) in Docker Compose, you can append the following service blocks to your root `docker-compose.yml`:

```yaml
  # Backend FastAPI service
  backend:
    build: ./backend
    container_name: chatbot-backend
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_URL=postgresql://user:pass@postgres:5432/chatbot
      - MONGO_URL=mongodb://mongodb:27017/chatbot
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - postgres
      - mongodb
      - qdrant

  # Frontend React (Vite/Nginx) service
  frontend:
    build: ./frontend
    container_name: chatbot-frontend
    ports:
      - "80:80"
    depends_on:
      - backend
```

---

## 🧪 Testing & Verification Guide

Once both servers and databases are running, use the following methods to verify the setup:

### A. Run Automated Diagnostics Suite
In your backend virtual environment, run the integration diagnostic tool:
```bash
python test_integration.py
```
*This validates:*
*   PostgreSQL connectivity and database tables (`users`, `tools`, `chat_sessions`, `resources`, `feedbacks`, etc.).
*   MongoDB connectivity and document read/write capability.
*   Qdrant Vector DB connection and collection status.
*   Document chunking parser and RAG pipeline components.
*   Tool execution routers.

To verify LLM text generation capabilities:
```bash
python test_llm.py
```

### B. Test via the Interactive Web UI
Open your browser to `http://localhost:5173` to interact with the full web app UI.
1.  **Sidebar**: Swap between **Chat**, **Tool Manager**, **Knowledge Hub (RAG)**, and **Settings** views.
2.  **Settings**: Choose model providers and save credentials.
3.  **Tool Manager**: Declare/register custom REST APIs as LLM-executable tools.
4.  **Knowledge Hub**: Upload documents and watch logs process chunking, embedding, and vectorizing.
5.  **Chat Interface**: Test real-time streaming tokens and agentic tool actions. Try: *"Calculate 2 * (3 + 5)"*.

### C. Test via OpenAPI Swagger UI
FastAPI automatically publishes interactive endpoint documentation at:
**[http://localhost:8000/docs](http://localhost:8000/docs)**.

---

## 🔍 Troubleshooting & FAQs

*   **Port 8000 or 5173 is already in use**:
    *   *Backend*: Start uvicorn on another port: `uvicorn app.main:app --reload --port 8080`.
    *   *Frontend*: Vite will automatically prompt you to use another port, or configure `server.port` in `vite.config.js`.
*   **PostgreSQL Connection Failed**:
    Ensure the postgres docker container is running. Check your `.env` connection string (`POSTGRES_URL=postgresql://user:pass@localhost:5432/chatbot`).
*   **Ollama is slow or timing out**:
    Make sure Ollama is active. Verify the model is downloaded by running `ollama list` in your shell.