from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from models import (
    UserCreate, UserLogin, Token, User,
    ProjectCreate, Project,
    Document, QueryRequest, QueryResponse,
    GraphVisualization
)
from database import db
from auth import create_access_token, get_current_user, verify_project_access, ACCESS_TOKEN_EXPIRE_MINUTES
from rag_pipeline import rag_pipeline

app = FastAPI(
    title="Multi-Tenant GraphRAG API",
    description="Scalable RAG system with user authentication and project-based knowledge bases",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create necessary directories
Path("data").mkdir(exist_ok=True)
Path("uploads").mkdir(exist_ok=True)

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/")
async def root():
    """API Health check"""
    return {"status": "ok", "message": "GraphRAG API is running"}

@app.get("/api")
async def api_root():
    """API Root endpoint"""
    return {"status": "ok", "version": "2.0.0", "message": "Multi-Tenant GraphRAG API"}

# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.post("/api/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    Register a new user
    
    - Creates a new user account
    - Returns JWT access token
    """
    # Check if user already exists
    existing_user = db.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Create user
        user = db.create_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password
        )
        
        # Create access token
        access_token = create_access_token(
            data={"sub": user["id"], "email": user["email"]},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=User(**user)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

@app.post("/api/auth/login", response_model=Token)
async def login(credentials: UserLogin):
    """
    Login with email and password
    
    - Authenticates user credentials
    - Returns JWT access token
    """
    # Get user
    user = db.get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not db.verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user["id"], "email": user["email"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    # Remove password hash from response
    user_response = {k: v for k, v in user.items() if k != "password_hash"}
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=User(**user_response)
    )

@app.get("/api/auth/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    user_response = {k: v for k, v in current_user.items() if k != "password_hash"}
    return User(**user_response)

# ============================================================================
# PROJECT ROUTES
# ============================================================================

@app.post("/api/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new project
    
    - Each project has its own isolated knowledge base
    - Users can have multiple projects
    """
    try:
        project = db.create_project(
            user_id=current_user["id"],
            name=project_data.name,
            description=project_data.description
        )
        return Project(**project)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating project: {str(e)}"
        )

@app.get("/api/projects", response_model=List[Project])
async def get_user_projects(current_user: dict = Depends(get_current_user)):
    """Get all projects for the current user"""
    projects = db.get_user_projects(current_user["id"])
    return [Project(**p) for p in projects]

@app.get("/api/projects/{project_id}", response_model=Project)
async def get_project(
    project_id: str,
    project: dict = Depends(verify_project_access)
):
    """Get details of a specific project"""
    return Project(**project)

@app.delete("/api/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    project: dict = Depends(verify_project_access)
):
    """
    Delete a project and all its data
    
    - Deletes all documents
    - Clears knowledge graph
    - Removes project record
    """
    try:
        # Clear knowledge graph
        rag_pipeline.clear_project_knowledge_base(project_id)
        
        # Delete all document files
        documents = db.get_project_documents(project_id)
        for doc in documents:
            file_path = Path(doc["file_path"])
            if file_path.exists():
                file_path.unlink()
        
        # Delete project from database
        db.delete_project(project_id)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting project: {str(e)}"
        )

# ============================================================================
# DOCUMENT ROUTES
# ============================================================================

@app.post("/api/projects/{project_id}/documents", response_model=Document)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    project: dict = Depends(verify_project_access)
):
    """
    Upload a PDF or document to a project
    
    - Supports PDF, DOCX, TXT
    - Automatically processes and adds to knowledge graph
    """
    # Validate file type
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt'}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file_ext} not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    try:
        # Create project upload directory
        upload_dir = Path("uploads") / project_id
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = upload_dir / file.filename
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Create document record
        document = db.create_document(
            project_id=project_id,
            filename=file.filename,
            file_size=file_size,
            file_path=str(file_path)
        )
        
        # Process document in background asynchronously
        import threading
        def process_in_background():
            print(f"[BACKGROUND] Starting processing for {file.filename}")
            try:
                result = rag_pipeline.process_document(
                    project_id=project_id,
                    file_path=str(file_path),
                    doc_name=file.filename
                )
                
                print(f"[BACKGROUND] Processing result: {result}")
                
                if result["status"] == "success":
                    db.mark_document_processed(document["id"])
                    print(f"[BACKGROUND] Marked {file.filename} as processed")
                else:
                    print(f"[BACKGROUND] Processing failed for {file.filename}")
            
            except Exception as e:
                print(f"[BACKGROUND] ERROR processing document {file.filename}: {e}")
                import traceback
                traceback.print_exc()
        
        # Start processing in background thread
        threading.Thread(target=process_in_background, daemon=True).start()
        
        return Document(**document)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )

@app.get("/api/projects/{project_id}/documents", response_model=List[Document])
async def get_project_documents(
    project_id: str,
    project: dict = Depends(verify_project_access)
):
    """Get all documents in a project"""
    documents = db.get_project_documents(project_id)
    return [Document(**d) for d in documents]

@app.delete("/api/projects/{project_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    project_id: str,
    document_id: str,
    project: dict = Depends(verify_project_access)
):
    """Delete a document from a project"""
    try:
        # Get document info
        documents = db.get_project_documents(project_id)
        document = next((d for d in documents if d["id"] == document_id), None)
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Delete file
        file_path = Path(document["file_path"])
        if file_path.exists():
            file_path.unlink()
        
        # Delete from database
        db.delete_document(document_id)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )

# ============================================================================
# QUERY ROUTES
# ============================================================================

@app.post("/api/query", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Query a project's knowledge base
    
    - Retrieves relevant information from the knowledge graph
    - Generates answers using LLM
    - Maintains conversation history
    """
    # Verify project access
    project = db.get_project(request.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if project["user_id"] != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this project"
        )
    
    try:
        # Query knowledge graph
        context = rag_pipeline.query_knowledge_graph(
            project_id=request.project_id,
            question=request.question
        )
        
        # Generate answer
        answer = rag_pipeline.generate_answer(
            question=request.question,
            context=context
        )
        
        # Extract sources from context
        sources = []
        for line in context.split('\n'):
            if '(Source:' in line:
                source = line.split('(Source:')[1].strip(' )')
                if source not in sources:
                    sources.append(source)
        
        session_id = request.session_id or f"{current_user['id']}_{request.project_id}"
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )

# ============================================================================
# VISUALIZATION ROUTES
# ============================================================================

@app.get("/api/projects/{project_id}/graph", response_model=GraphVisualization)
async def get_knowledge_graph_visualization(
    project_id: str,
    limit: int = 50,
    project: dict = Depends(verify_project_access)
):
    """
    Get knowledge graph data for visualization
    
    - Returns nodes and edges for graph visualization
    - Includes statistics about the knowledge base
    """
    try:
        # Get visualization data
        graph_data = rag_pipeline.get_graph_visualization_data(project_id, limit)
        
        # Get statistics
        stats = rag_pipeline.get_project_statistics(project_id)
        
        return GraphVisualization(
            nodes=graph_data["nodes"],
            edges=graph_data["edges"],
            statistics=stats
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating visualization: {str(e)}"
        )

@app.get("/api/projects/{project_id}/statistics")
async def get_project_statistics(
    project_id: str,
    project: dict = Depends(verify_project_access)
):
    """Get statistics about a project's knowledge base"""
    try:
        stats = rag_pipeline.get_project_statistics(project_id)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting statistics: {str(e)}"
        )

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "llm_provider": os.getenv("LLM_PROVIDER", "groq"),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Multi-Tenant GraphRAG API",
        "version": "2.0.0",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
