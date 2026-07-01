# ==========================================
# Stage 1: Build the React Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy dependencies manifest
COPY frontend/package*.json ./

# Install npm packages
RUN npm install

# Copy frontend source files
COPY frontend/ ./

# Build the frontend to /app/frontend/dist
RUN npm run build

# ==========================================
# Stage 2: Final Python environment (Backend + Frontend)
# ==========================================
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Set python environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system packages (build tools, pg libs, and curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set backend working directory
WORKDIR /app/backend

# Copy requirements
COPY backend/requirements.txt .

# Install dependencies and PostgreSQL adapter
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir psycopg2-binary

# Copy backend files
COPY backend/ .

# Copy built frontend assets from Stage 1 into /app/frontend/dist
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Expose backend port (which now hosts both frontend and backend)
EXPOSE 8001

# Command to run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
