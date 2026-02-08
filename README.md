# GraphRAG with AI Agents

Enterprise-grade knowledge graph and database query system powered by LangChain, LangGraph, and AI agents. Features intelligent query routing across Neo4j graph database, SQL database, and document analysis with conversation memory.

## Features

### Multi-Agent Architecture
- **Graph Agent**: Queries Neo4j knowledge graph from uploaded documents
- **SQL Agent**: Text-to-SQL natural language queries on relational database
- **Research Agent**: Document analysis and topic extraction
- **Smart Routing**: Automatic agent selection based on query intent

### Knowledge Management
- Document upload and processing (PDF, DOCX)
- Entity and relationship extraction
- Neo4j graph database storage
- SQLite relational database with sample data

### Conversation Memory
- Session-based conversation history
- Context-aware responses
- Automatic summarization for long conversations

### Developer Features
- REST API with FastAPI
- Interactive Streamlit web interface
- Comprehensive API documentation
- Docker containerization

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose
- Groq API key (get free at groq.com)

### Installation

1. Clone the repository and navigate to the project directory

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Edit `.env` and add your Groq API key:
```env
GROQ_API_KEY=your_api_key_here
```

4. Install Python dependencies:
```bash
pip install -r app/requirements.txt
```

### Starting the System

**Option A: Automated startup (Windows)**
```bash
# PowerShell
./start.ps1

# Command Prompt
start.bat
```

**Option B: Manual startup**
```bash
# Start Neo4j
docker-compose up -d neo4j

# Start API server (from project root)
cd app
uvicorn main:app --reload --port 8000

# Start Streamlit UI (optional, new terminal)
streamlit run streamlit_app.py --server.port 8501
```

### Access Points

- **Streamlit UI**: http://localhost:8501
- **API Documentation**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
  - Username: neo4j
  - Password: password123

## Technology Stack

- **Backend Framework**: FastAPI
- **AI Framework**: LangChain, LangGraph
- **Graph Database**: Neo4j
- **SQL Database**: SQLite
- **LLM Provider**: Groq (llama-3.3-70b-versatile)
- **Frontend**: Streamlit
- **Containerization**: Docker Compose

## Architecture

1. Upload document → Extract text
2. LLM extracts entities and relationships
3. Store in Neo4j graph database
4. AI agents query graph with specialized tools
5. Conversation memory maintains context

## Project Structure

```
gr-rag/
├── app/
│   ├── agents.py           # AI agents (Graph, SQL, Research)
│   ├── config.py           # Configuration and environment variables
│   ├── main.py             # FastAPI application and endpoints
│   ├── memory.py           # Conversation memory management
│   ├── rag_pipeline.py     # Document processing and Neo4j integration
│   ├── requirements.txt    # Python dependencies
│   └── streamlit_app.py    # Streamlit web interface
├── docs/                   # Document uploads directory
├── neo4j-data/            # Neo4j database storage (auto-generated)
├── docker-compose.yml     # Docker services configuration
├── start.ps1              # Windows startup script (PowerShell)
├── start.bat              # Windows startup script (CMD)
├── .env.example           # Environment variables template
└── README.md
```

## API Endpoints

### Primary Endpoints
- `POST /upload` - Upload and process documents
- `POST /query` - Query with AI agents
- `GET /` - Health check

### Memory Management
- `GET /memory/sessions` - List all conversation sessions
- `GET /memory/session/{session_id}` - Get specific session history
- `DELETE /memory/session/{session_id}` - Clear session history
- `DELETE /memory/sessions` - Clear all sessions

### Documentation
- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Usage Examples

### Python API Client

```python
import requests

BASE_URL = "http://localhost:8000"

# Simple query (auto-routing)
response = requests.post(f"{BASE_URL}/query", json={
    "question": "What programming languages are mentioned?",
    "use_memory": False
})
print(response.json()["answer"])

# Query with specific agent
response = requests.post(f"{BASE_URL}/query", json={
    "question": "How many products are in stock?",
    "agent_type": "sql",
    "use_memory": False
})
print(response.json()["answer"])

# Conversation with memory
session_id = "user_123"

response1 = requests.post(f"{BASE_URL}/query", json={
    "question": "What is the main topic of the documents?",
    "session_id": session_id,
    "use_memory": True
})

response2 = requests.post(f"{BASE_URL}/query", json={
    "question": "Tell me more about that",
    "session_id": session_id,
    "use_memory": True
})
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What is RLM?", "use_memory": false}'

# Query with SQL agent
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many customers?", "agent_type": "sql", "use_memory": false}'

# Get session history
curl http://localhost:8000/memory/session/user_123
```

## Environment Variables

### Required
```env
GROQ_API_KEY=your_groq_api_key_here
```

### Optional (defaults shown)
```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# LLM Model
GROQ_MODEL=llama-3.3-70b-versatile
```

## Architecture Overview

1. **Document Upload**: PDF/DOCX files are uploaded via API or Streamlit
2. **Text Extraction**: Documents are parsed and text is extracted
3. **Entity Extraction**: LLM analyzes text and extracts entities and relationships
4. **Graph Storage**: Entities stored as nodes, relationships as edges in Neo4j
5. **Query Processing**: User queries are routed to appropriate agent
6. **Response Generation**: Agent queries databases and generates natural language responses

## Development

### Running Tests
```bash
# Test imports
cd app
python -c "from agents import AgentOrchestrator; from memory import memory_manager; print('OK')"

# Test API endpoints
curl http://localhost:8000/
```

### Code Structure
- `agents.py`: Three AI agent classes (Graph, SQL, Research) and orchestrator
- `memory.py`: Conversation memory with session management and summarization
- `rag_pipeline.py`: Document processing, entity extraction, Neo4j operations
- `main.py`: FastAPI routes and application initialization
- `streamlit_app.py`: Web interface with file upload and chat

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Backend not connecting | Check if Neo4j is running: `docker ps` |
| Import errors | Install dependencies: `pip install -r app/requirements.txt` |
| Port already in use | Stop existing services or change ports in config |
| Groq API errors | Verify `GROQ_API_KEY` is set in `.env` file |
| Neo4j connection failed | Ensure Neo4j container is running and ports 7474, 7687 are available |
| No documents found | Upload documents first via `/upload` endpoint or Streamlit UI |

## Key Technologies

**GraphRAG**: Retrieval-Augmented Generation using knowledge graphs instead of vector embeddings for more accurate context retrieval

**Neo4j**: Property graph database storing entities as nodes and relationships as directed edges with properties

**LangChain**: Framework for building LLM applications with chains, agents, and tools

**LangGraph**: State machine and workflow orchestration for complex agentic systems

**Text-to-SQL**: Natural language to SQL conversion using LLM contextual understanding of database schema

## License

This project is provided as-is for educational and commercial use.

