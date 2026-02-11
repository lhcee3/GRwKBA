# GraphRAG Multi-Tenant Knowledge Base

A multi-tenant RAG (Retrieval Augmented Generation) system with user authentication, project-based knowledge bases, and knowledge graph visualization.

## Features

- Multi-Tenant Architecture - Each user can create multiple isolated projects
- JWT Authentication - Secure user registration and login
- Project-Based Knowledge Bases - Separate knowledge graphs per project
- PDF/Document Processing - Upload and process PDF, DOCX, TXT files
- Interactive Chat - Ask questions about your documents using AI
- Knowledge Graph Visualization - Visual representation of entities and relationships
- Flexible LLM Support - Use Groq API (cloud) or Ollama (local)

## Prerequisites

- Python 3.11+
- Node.js 18+
- Neo4j database
- Groq API key (get from https://console.groq.com)

## Setup Instructions

### 1. Start Neo4j

**Option A: Using Docker (Easiest)**
```bash
docker run -d --name graphrag-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password123 \
  neo4j:5.15
```

**Option B: Install Neo4j Desktop**
- Download from https://neo4j.com/download/
- Create a database with password `password123`
- Start the database

### 2. Configure Environment

Create `.env` file in project root:
```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password123

# LLM Provider
LLM_PROVIDER=groq
GROQ_API_KEY=your-groq-api-key-here
GROQ_MODEL=llama-3.3-70b-versatile

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-secret-key-here
```

### 3. Start Backend

```bash
cd backend
pip install -r requirements.txt
python main.py
```

Backend will run on http://localhost:8000

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will run on http://localhost:5173

### 5. Use the Application

1. Open http://localhost:5173 in your browser
2. Register a new account
3. Create a project
4. Upload documents (PDF, DOCX, or TXT)
5. Wait for processing to complete
6. Ask questions in the chat interface

## Project Structure

```
gr-rag/
├── backend/          # FastAPI backend
│   ├── main.py       # API endpoints
│   ├── auth.py       # JWT authentication
│   ├── database.py   # SQLite operations
│   ├── rag_pipeline.py  # Document processing & RAG
│   └── requirements.txt
├── frontend/         # React frontend
│   └── src/
│       ├── components/  # UI components
│       └── api.js       # API client
└── docker-compose.yml   # Optional Docker setup
```

## API Documentation

Once backend is running, visit:
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/api

## Troubleshooting

**Backend won't start**
- Check if port 8000 is available: `netstat -ano | findstr :8000`
- Verify Neo4j is running: `netstat -ano | findstr :7687`

**Neo4j connection failed**
- Ensure Neo4j is running on port 7687
- Verify password matches NEO4J_PASSWORD in .env

**Documents stuck in "Processing"**
- Check backend terminal for error messages
- Verify GROQ_API_KEY is valid
- Ensure Neo4j connection is working

**Frontend can't connect to backend**
- Verify backend is running on port 8000
- Check that API_URL in frontend/src/api.js is correct

## Technology Stack

**Backend**
- FastAPI - Web framework
- SQLite - User/project data
- Neo4j - Knowledge graph storage
- LangChain - RAG pipeline
- Groq/Ollama - LLM inference

**Frontend**
- React - UI framework
- Vite - Build tool
- Tailwind CSS - Styling
- Axios - HTTP client

### Queries
- `POST /api/query` - Ask a question

## 🗂️ Project Structure

```
gr-rag/
├── backend/
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic models
│   ├── database.py       # SQLite operations
│   ├── auth.py           # JWT authentication
│   ├── rag_pipeline.py   # Multi-tenant RAG logic
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Login.jsx
│   │   │   ├── Register.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ProjectView.jsx
│   │   │   └── GraphVisualization.jsx
│   │   ├── App.jsx
│   │   ├── AuthContext.jsx
│   │   └── api.js
│   └── package.json
├── docker-compose.yml
├── .env
└── README.md
```

## 🔧 Troubleshooting

### Ollama Connection Issues
```bash
# Check Ollama is running
docker exec -it graphrag-ollama ollama list

# Pull a model
docker exec -it graphrag-ollama ollama pull llama3.2

# Check logs
docker logs graphrag-ollama
```

### Backend Errors
```bash
# Check backend logs
docker logs graphrag-backend

# Restart backend
docker-compose restart backend
```

### Neo4j Connection Issues
```bash
# Check Neo4j is running
docker logs graphrag-neo4j

# Access Neo4j browser
open http://localhost:7474
```

## 🚀 Production Deployment

1. **Generate strong JWT secret**:
```bash
openssl rand -hex 32
```

2. **Update environment variables**:
```env
JWT_SECRET_KEY=<generated-secret>
```

3. **Configure CORS** in `backend/main.py`:
```python
allow_origins=["https://yourdomain.com"]
```

4. **Use production builds**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📝 License

MIT License - feel free to use this project for learning or commercial purposes.

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues or questions, please open an issue on GitHub.

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
  - Chat interface for Q&A
  - Interactive graph visualization
  - Document upload and management
- **API Documentation**: http://localhost:8000/docs
- **Neo4j Browser**: http://localhost:7474
  - Username: neo4j
  - Password: password123
  - Advanced Cypher query interface

## Graph Visualization

The application provides multiple ways to visualize and explore your knowledge graph:

### 1. Built-in Interactive Visualization (Streamlit)
The Streamlit interface includes a dedicated "Graph Visualization" tab that displays:
- **Interactive node-edge graph**: Drag, zoom, and explore entities and relationships
- **Real-time statistics**: Track entities, relationships, and connected documents
- **Relationship details**: View all connections with source document information
- **Auto-refresh**: Update visualization as you add new documents

**Features:**
- Color-coded entities
- Labeled relationships showing connection types
- Physics-enabled layout for optimal viewing
- Click nodes to highlight connections

### 2. Neo4j Browser (Advanced)
Access Neo4j Browser at http://localhost:7474 for:
- Writing custom Cypher queries
- Advanced graph analytics
- Database management
- Export capabilities

**Useful Cypher Queries:**
```cypher
// View all nodes and relationships
MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50

// Find relationships from a specific document
MATCH (s)-[r:RELATION]->(t) 
WHERE r.source = 'your_document.pdf' 
RETURN s, r, t

// Find entity connections
MATCH (n:Entity {name: 'EntityName'})-[r]-(connected)
RETURN n, r, connected

// Get graph statistics
MATCH (n:Entity) RETURN count(n) as entities
MATCH ()-[r:RELATION]->() RETURN count(r) as relationships
```

### How the Graph is Built

When you upload a document:
1. Text is extracted from PDF/DOCX/TXT files
2. LLM analyzes content to extract entities and relationships
3. Entities become nodes in the graph
4. Relationships become edges connecting the nodes
5. Each relationship is tagged with the source document

**Example:**
If your document states "Python is a programming language used by Google", the system creates:
- Node: `Python`
- Node: `programming language`
- Node: `Google`
- Edge: `Python` → `is a` → `programming language`
- Edge: `Python` → `used by` → `Google`

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

