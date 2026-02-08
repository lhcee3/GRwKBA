import os
from typing import List, Dict
from pathlib import Path
from neo4j import GraphDatabase
from langchain_groq import ChatGroq
from langchain.text_splitter import RecursiveCharacterTextSplitter
import PyPDF2
from docx import Document as DocxDocument
from config import settings

class GraphRAGPipeline:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        
        if not settings.groq_api_key:
            raise Exception("GROQ_API_KEY required")
        
        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0
        )
    
    def extract_text_from_file(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        
        if ext == '.pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return '\n'.join([page.extract_text() for page in reader.pages])
        
        elif ext in ['.docx', '.doc']:
            doc = DocxDocument(file_path)
            return '\n'.join([para.text for para in doc.paragraphs])
        
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        return ""
    
    def extract_entities(self, text: str) -> List[Dict]:
        prompt = f"""Extract key entities and their relationships from this text.

Text: {text[:2000]}

Extract facts in this exact format (one per line):
Entity1|relationship|Entity2

Examples:
John Smith|works at|Google
Python|is a|programming language
New York|located in|United States

Now extract from the text above:"""

        response = self.llm.invoke(prompt)
        entities = []
        
        for line in response.content.split('\n'):
            line = line.strip()
            if '|' in line and not line.startswith('Example'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3 and parts[0] and parts[1] and parts[2]:
                    entities.append({
                        'subject': parts[0],
                        'predicate': parts[1],
                        'object': parts[2]
                    })
        
        return entities
    
    def build_graph(self, entities: List[Dict], doc_name: str):
        with self.driver.session() as session:
            for entity in entities:
                session.run("""
                    MERGE (s:Entity {name: $subject})
                    MERGE (o:Entity {name: $object})
                    MERGE (s)-[r:RELATION {type: $predicate, source: $doc}]->(o)
                """, subject=entity['subject'], 
                     object=entity['object'],
                     predicate=entity['predicate'],
                     doc=doc_name)
    
    def clear_graph(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    def delete_document(self, doc_name: str):
        with self.driver.session() as session:
            session.run("""
                MATCH ()-[r:RELATION {source: $doc}]->()
                DELETE r
            """, doc=doc_name)
            session.run("""
                MATCH (n:Entity)
                WHERE NOT (n)-[:RELATION]-()
                DELETE n
            """)
    
    def process_document(self, file_path: str) -> Dict:
        text = self.extract_text_from_file(file_path)
        doc_name = Path(file_path).name
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap
        )
        chunks = splitter.split_text(text)
        
        all_entities = []
        for chunk in chunks[:3]:
            entities = self.extract_entities(chunk)
            all_entities.extend(entities)
            if len(all_entities) > 20:
                break
        
        self.build_graph(all_entities, doc_name)
        
        return {
            'doc_name': doc_name,
            'chunks': len(chunks),
            'entities': len(all_entities),
            'text_preview': text[:500]
        }
    
    def query_graph(self, question: str, doc_filter: str = None) -> str:
        with self.driver.session() as session:
            count_result = session.run("MATCH (n:Entity) RETURN count(n) as count").single()
            node_count = count_result["count"] if count_result else 0
            
            if node_count == 0:
                return "No documents have been processed yet. Please upload a document first."
            
            query = """
                MATCH (s:Entity)-[r:RELATION]->(o:Entity)
                WHERE $doc_filter IS NULL OR r.source = $doc_filter
                RETURN s.name as subject, r.type as relation, o.name as object, r.source as source
                LIMIT 50
            """
            
            result = session.run(query, doc_filter=doc_filter)
            
            facts = []
            sources = set()
            for record in result:
                facts.append(f"{record['subject']} {record['relation']} {record['object']}")
                sources.add(record['source'])
            
            if not facts:
                return "No relationships found. The document might not have been processed correctly."
            
            graph_context = '\n'.join(facts)
            source_info = f"\n\nSources: {', '.join(sources)}"
        
        prompt = f"""Answer the question using ONLY the facts from the knowledge graph below.

Knowledge Graph Facts:
{graph_context}

Question: {question}

Provide a clear answer based on these facts:"""
        
        response = self.llm.invoke(prompt)
        return response.content + source_info
    
    def close(self):
        self.driver.close()
