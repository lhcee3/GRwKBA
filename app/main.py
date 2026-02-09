import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import shutil
from pathlib import Path
from rag_pipeline import GraphRAGPipeline
from agents import AgentOrchestrator
from memory import memory_manager
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

app = FastAPI(title="GraphRAG API with AI Agents")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = GraphRAGPipeline()
orchestrator = AgentOrchestrator(pipeline)

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default"
    use_memory: Optional[bool] = True
    agent_type: Optional[str] = None  # "graph", "research", or None for auto

class QueryResponse(BaseModel):
    answer: str
    sources: List[str] = []
    agent_used: Optional[str] = None
    session_id: Optional[str] = None

class AgentState(TypedDict):
    question: str
    context: Annotated[list, operator.add]
    answer: str

def retrieve_context(state: AgentState):
    question = state["question"]
    context = pipeline.query_graph(question)
    return {"context": [context]}

def generate_answer(state: AgentState):
    context = "\n".join(state["context"])
    answer = f"Based on the graph: {context}"
    return {"answer": answer}

workflow = StateGraph(AgentState)
workflow.add_node("retrieve", retrieve_context)
workflow.add_node("generate", generate_answer)
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)
workflow.set_entry_point("retrieve")
agent = workflow.compile()

@app.get("/")
def root():
    return {"status": "GraphRAG API running"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        file_path = Path("/docs") / file.filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        result = pipeline.process_document(str(file_path))
        return {"message": "File processed", "details": result}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query with AI agents and memory context
    Supports different agent types and conversation memory
    """
    try:
        # Get conversation memory if enabled
        chat_history = []
        if request.use_memory and request.session_id:
            memory = memory_manager.get_session(request.session_id)
            chat_history = memory.get_langchain_messages(limit=10)
        
        # Run the appropriate agent
        result = orchestrator.run(
            query=request.question,
            chat_history=chat_history,
            agent_type=request.agent_type
        )
        
        # Store conversation in memory
        if request.use_memory and request.session_id:
            memory = memory_manager.get_session(request.session_id)
            memory.add_message("user", request.question)
            memory.add_message("assistant", result["output"], {"agent": result.get("agent_used")})
        
        return QueryResponse(
            answer=result["output"],
            sources=[],
            agent_used=result.get("agent_used"),
            session_id=request.session_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/stats")
def graph_stats():
    """Get graph database statistics"""
    try:
        with pipeline.driver.session() as session:
            nodes = session.run("MATCH (n:Entity) RETURN count(n) as count").single()["count"]
            rels = session.run("MATCH ()-[r:RELATION]->() RETURN count(r) as count").single()["count"]
        
        return {"nodes": nodes, "relationships": rels}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/graph/visualize")
def get_graph_data():
    """Get graph data for visualization"""
    try:
        with pipeline.driver.session() as session:
            # Get all nodes
            nodes_result = session.run("""
                MATCH (n:Entity)
                RETURN id(n) as id, n.name as name
            """)
            nodes = [{"id": str(record["id"]), "label": record["name"]} for record in nodes_result]
            
            # Get all relationships
            edges_result = session.run("""
                MATCH (s:Entity)-[r:RELATION]->(t:Entity)
                RETURN id(s) as source, id(t) as target, r.type as type, r.source as doc
            """)
            edges = [
                {
                    "source": str(record["source"]),
                    "target": str(record["target"]),
                    "type": record["type"],
                    "label": record["type"],
                    "document": record["doc"]
                }
                for record in edges_result
            ]
            
        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/graph/clear")
def clear_graph():
    """Clear all data from the graph database"""
    try:
        pipeline.clear_graph()
        return {"message": "Graph cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/document/{filename}")
def delete_document(filename: str):
    """Delete a specific document from the graph"""
    try:
        pipeline.delete_document(filename)
        return {"message": f"Document {filename} removed from graph"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/sessions")
def list_memory_sessions():
    """List all active conversation sessions"""
    try:
        sessions = memory_manager.list_sessions()
        return {"sessions": sessions, "total": len(sessions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/session/{session_id}")
def get_session_history(session_id: str):
    """Get conversation history for a session"""
    try:
        memory = memory_manager.get_session(session_id)
        messages = memory.get_messages()
        summary = memory.get_summary()
        return {
            "session_id": session_id,
            "messages": messages,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/memory/session/{session_id}")
def clear_session(session_id: str):
    """Clear a specific conversation session"""
    try:
        memory_manager.delete_session(session_id)
        return {"message": f"Session {session_id} cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/memory/clear-all")
def clear_all_sessions():
    """Clear all conversation sessions"""
    try:
        memory_manager.clear_all()
        return {"message": "All sessions cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agent/test")
async def test_agent(agent_type: str = "graph"):
    """Test agent functionality"""
    try:
        test_query = "What information is available in the knowledge base?"
        result = orchestrator.run(test_query, agent_type=agent_type)
        return {
            "agent_type": agent_type,
            "test_query": test_query,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

