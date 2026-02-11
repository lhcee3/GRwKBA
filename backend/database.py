import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List
from passlib.hash import bcrypt
from contextlib import contextmanager

DATABASE_URL = "data/app.db"

class Database:
    def __init__(self, db_path: str = DATABASE_URL):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            
            # Documents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    uploaded_at TEXT NOT NULL,
                    processed BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_project_id ON documents(project_id)")
    
    # User operations
    def create_user(self, email: str, username: str, password: str) -> dict:
        user_id = str(uuid.uuid4())
        # Truncate password to 72 bytes (bcrypt limit)
        password_truncated = password[:72]
        password_hash = bcrypt.hash(password_truncated)
        created_at = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (id, email, username, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, email, username, password_hash, created_at))
        
        return {
            "id": user_id,
            "email": email,
            "username": username,
            "created_at": created_at
        }
    
    def get_user_by_email(self, email: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def verify_password(self, plain_password: str, password_hash: str) -> bool:
        # Truncate password to 72 bytes (bcrypt limit) to match hashing
        password_truncated = plain_password[:72]
        return bcrypt.verify(password_truncated, password_hash)
    
    # Project operations
    def create_project(self, user_id: str, name: str, description: Optional[str] = None) -> dict:
        project_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO projects (id, user_id, name, description, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (project_id, user_id, name, description, created_at))
        
        return {
            "id": project_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "created_at": created_at,
            "document_count": 0
        }
    
    def get_user_projects(self, user_id: str) -> List[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, COUNT(d.id) as document_count
                FROM projects p
                LEFT JOIN documents d ON p.id = d.project_id
                WHERE p.user_id = ?
                GROUP BY p.id
                ORDER BY p.created_at DESC
            """, (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_project(self, project_id: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.*, COUNT(d.id) as document_count
                FROM projects p
                LEFT JOIN documents d ON p.id = d.project_id
                WHERE p.id = ?
                GROUP BY p.id
            """, (project_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def delete_project(self, project_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    
    # Document operations
    def create_document(self, project_id: str, filename: str, file_size: int, file_path: str) -> dict:
        doc_id = str(uuid.uuid4())
        uploaded_at = datetime.utcnow().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO documents (id, project_id, filename, file_size, file_path, uploaded_at, processed)
                VALUES (?, ?, ?, ?, ?, ?, FALSE)
            """, (doc_id, project_id, filename, file_size, file_path, uploaded_at))
        
        return {
            "id": doc_id,
            "project_id": project_id,
            "filename": filename,
            "file_size": file_size,
            "uploaded_at": uploaded_at,
            "processed": False
        }
    
    def get_project_documents(self, project_id: str) -> List[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM documents
                WHERE project_id = ?
                ORDER BY uploaded_at DESC
            """, (project_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_document_processed(self, doc_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE documents SET processed = TRUE WHERE id = ?", (doc_id,))
    
    def delete_document(self, doc_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

# Global database instance
db = Database()
