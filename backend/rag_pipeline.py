import os
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from neo4j import GraphDatabase
from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatOllama
from langchain.text_splitter import RecursiveCharacterTextSplitter
import PyPDF2
from docx import Document as DocxDocument

# Load environment variables
load_dotenv()

class MultiTenantGraphRAG:
    """
    Multi-tenant GraphRAG pipeline where each project has its own knowledge base in Neo4j
    Supports both Groq API and local Ollama models
    """
    
    def __init__(self):
        # Neo4j connection
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "password123")
            )
        )
        
        # LLM configuration - supports both Groq and Ollama
        self.llm_provider = os.getenv("LLM_PROVIDER", "groq")  # 'groq' or 'ollama'
        
        if self.llm_provider == "ollama":
            # Use local Ollama model
            self.llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )
        else:
            # Use Groq API
            groq_api_key = os.getenv("GROQ_API_KEY", "")
            if not groq_api_key:
                raise Exception("GROQ_API_KEY required when using Groq provider")
            
            self.llm = ChatGroq(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                api_key=groq_api_key,
                temperature=0
            )
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
    
    def _get_project_label(self, project_id: str) -> str:
        """Generate a unique Neo4j label for a project's knowledge base"""
        return f"Project_{project_id.replace('-', '_')}"
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text content from a PDF file"""
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            return '\n'.join([page.extract_text() for page in reader.pages if page.extract_text()])
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text content from a DOCX file"""
        doc = DocxDocument(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from various file formats"""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return self.extract_text_from_docx(file_path)
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def extract_entities_and_relations(self, text: str, max_chars: int = 2000) -> List[Dict]:
        """
        Use LLM to extract entities and relationships from text
        
        Args:
            text: Text to analyze
            max_chars: Maximum characters to send to LLM per chunk
        
        Returns:
            List of entity-relation-entity triples
        """
        # Split text into chunks if too long
        text_chunk = text[:max_chars] if len(text) > max_chars else text
        
        prompt = f"""Extract key entities and their relationships from this text.

Text: {text_chunk}

Extract facts in this exact format (one per line):
Entity1|relationship|Entity2

Examples:
John Smith|works at|Google
Python|is a|programming language
Machine Learning|is part of|Artificial Intelligence

Rules:
- Extract only factual relationships
- Use clear, specific entity names
- Use descriptive relationship types
- One triple per line

Now extract from the text above:"""

        try:
            response = self.llm.invoke(prompt)
            entities = []
            
            for line in response.content.split('\n'):
                line = line.strip()
                if '|' in line and not line.lower().startswith('example'):
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3 and all(parts[:3]):
                        entities.append({
                            'subject': parts[0],
                            'predicate': parts[1],
                            'object': parts[2]
                        })
            
            return entities
        except Exception as e:
            print(f"Error extracting entities: {e}")
            return []
    
    def build_knowledge_graph(self, project_id: str, entities: List[Dict], doc_name: str):
        """
        Build a knowledge graph for a specific project
        Each project has isolated nodes and relationships
        
        Args:
            project_id: Unique project identifier
            entities: List of extracted entity triples
            doc_name: Source document name
        """
        project_label = self._get_project_label(project_id)
        
        with self.driver.session() as session:
            for entity in entities:
                try:
                    # Create nodes and relationships with project-specific labels
                    session.run(f"""
                        MERGE (s:{project_label}:Entity {{name: $subject, project_id: $project_id}})
                        MERGE (o:{project_label}:Entity {{name: $object, project_id: $project_id}})
                        MERGE (s)-[r:RELATION {{
                            type: $predicate, 
                            source: $doc,
                            project_id: $project_id
                        }}]->(o)
                    """, 
                        subject=entity['subject'],
                        object=entity['object'],
                        predicate=entity['predicate'],
                        doc=doc_name,
                        project_id=project_id
                    )
                except Exception as e:
                    print(f"Error creating relationship: {e}")
    
    def query_knowledge_graph(self, project_id: str, question: str, limit: int = 10) -> str:
        """
        Query the knowledge graph for a specific project
        
        Args:
            project_id: Project identifier
            question: User's question
            limit: Maximum number of results to return
        
        Returns:
            Context string from the knowledge graph
        """
        project_label = self._get_project_label(project_id)
        
        # Extract key terms from question
        key_terms = [word.lower() for word in question.split() if len(word) > 3]
        
        with self.driver.session() as session:
            # Search for relevant entities and relationships
            results = []
            for term in key_terms[:3]:  # Use top 3 key terms
                result = session.run(f"""
                    MATCH (s:{project_label})-[r:RELATION]->(o:{project_label})
                    WHERE toLower(s.name) CONTAINS $term 
                       OR toLower(o.name) CONTAINS $term 
                       OR toLower(r.type) CONTAINS $term
                    RETURN s.name as subject, r.type as relation, o.name as object, r.source as source
                    LIMIT $limit
                """, term=term, limit=limit)
                results.extend(list(result))
            
            if not results:
                return "No relevant information found in the knowledge graph."
            
            # Format results as context
            context_parts = []
            seen = set()
            for record in results:
                triple = f"{record['subject']} {record['relation']} {record['object']}"
                if triple not in seen:
                    context_parts.append(f"- {triple} (Source: {record['source']})")
                    seen.add(triple)
            
            return "\n".join(context_parts[:limit])
    
    def generate_answer(self, question: str, context: str) -> str:
        """
        Generate an answer using LLM based on retrieved context
        
        Args:
            question: User's question
            context: Retrieved context from knowledge graph
        
        Returns:
            Generated answer
        """
        prompt = f"""Answer the following question based on the provided context.

Context:
{context}

Question: {question}

Answer (be specific and cite sources when possible):"""

        try:
            response = self.llm.invoke(prompt)
            return response.content
        except Exception as e:
            return f"Error generating answer: {str(e)}"
    
    def process_document(self, project_id: str, file_path: str, doc_name: str) -> Dict:
        """
        Process a document and add it to the project's knowledge base
        
        Args:
            project_id: Project identifier
            file_path: Path to the document file
            doc_name: Name to identify the document
        
        Returns:
            Processing results dictionary
        """
        try:
            # Extract text
            text = self.extract_text_from_file(file_path)
            
            if not text.strip():
                return {"status": "error", "message": "No text extracted from document"}
            
            # Split into chunks
            chunks = self.text_splitter.split_text(text)
            
            # Extract entities from each chunk
            all_entities = []
            for chunk in chunks[:5]:  # Process first 5 chunks to avoid rate limits
                entities = self.extract_entities_and_relations(chunk)
                all_entities.extend(entities)
            
            # Build knowledge graph
            if all_entities:
                self.build_knowledge_graph(project_id, all_entities, doc_name)
            
            return {
                "status": "success",
                "message": f"Processed {len(chunks)} chunks, extracted {len(all_entities)} entity relationships",
                "chunks": len(chunks),
                "entities": len(all_entities)
            }
        
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_project_statistics(self, project_id: str) -> Dict:
        """
        Get statistics about a project's knowledge graph
        
        Args:
            project_id: Project identifier
        
        Returns:
            Statistics dictionary
        """
        project_label = self._get_project_label(project_id)
        
        with self.driver.session() as session:
            # Count nodes
            node_count = session.run(f"""
                MATCH (n:{project_label})
                RETURN count(n) as count
            """).single()
            
            # Count relationships
            rel_count = session.run(f"""
                MATCH (:{project_label})-[r:RELATION]->(:{project_label})
                WHERE r.project_id = $project_id
                RETURN count(r) as count
            """, project_id=project_id).single()
            
            # Get unique sources
            sources = session.run(f"""
                MATCH (:{project_label})-[r:RELATION]->(:{project_label})
                WHERE r.project_id = $project_id
                RETURN DISTINCT r.source as source
            """, project_id=project_id)
            
            return {
                "nodes": node_count["count"] if node_count else 0,
                "relationships": rel_count["count"] if rel_count else 0,
                "documents": len(list(sources))
            }
    
    def get_graph_visualization_data(self, project_id: str, limit: int = 50) -> Dict:
        """
        Get data for visualizing the knowledge graph
        
        Args:
            project_id: Project identifier
            limit: Maximum number of nodes/edges to return
        
        Returns:
            Dictionary with nodes and edges for visualization
        """
        project_label = self._get_project_label(project_id)
        
        with self.driver.session() as session:
            result = session.run(f"""
                MATCH (s:{project_label})-[r:RELATION]->(o:{project_label})
                WHERE r.project_id = $project_id
                RETURN s.name as source, o.name as target, r.type as relation
                LIMIT $limit
            """, project_id=project_id, limit=limit)
            
            nodes = {}
            edges = []
            
            for record in result:
                source = record["source"]
                target = record["target"]
                
                if source not in nodes:
                    nodes[source] = {"id": source, "label": source}
                if target not in nodes:
                    nodes[target] = {"id": target, "label": target}
                
                edges.append({
                    "source": source,
                    "target": target,
                    "label": record["relation"]
                })
            
            return {
                "nodes": list(nodes.values()),
                "edges": edges
            }
    
    def clear_project_knowledge_base(self, project_id: str):
        """
        Clear all data for a specific project
        
        Args:
            project_id: Project identifier
        """
        project_label = self._get_project_label(project_id)
        
        with self.driver.session() as session:
            # Delete all relationships first
            session.run(f"""
                MATCH (:{project_label})-[r:RELATION]->(:{project_label})
                WHERE r.project_id = $project_id
                DELETE r
            """, project_id=project_id)
            
            # Delete all nodes
            session.run(f"""
                MATCH (n:{project_label})
                WHERE n.project_id = $project_id
                DELETE n
            """, project_id=project_id)
    
    def close(self):
        """Close database connection"""
        self.driver.close()

# Global RAG instance
rag_pipeline = MultiTenantGraphRAG()
