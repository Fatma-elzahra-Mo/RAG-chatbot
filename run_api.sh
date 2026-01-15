#!/bin/bash

# Start the Arabic RAG Chatbot API
echo "Starting Arabic RAG Chatbot API..."
echo "API will be available at: http://localhost:8000"
echo "Docs available at: http://localhost:8000/docs"
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

# Run with uvicorn
.venv/bin/uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
