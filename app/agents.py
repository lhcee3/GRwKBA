"""
AI Agents with LangChain/LangGraph - Graph DB + SQL DB + Research
"""
from typing import List, Dict, Any, Optional
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from config import settings
import json
import sqlite3
import os


class GraphAgent:
    """
    Agent for querying Neo4j knowledge graph
    """
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0.3
        )
    
    def query_knowledge_graph(self, question: str) -> str:
        """Query the knowledge graph with a question"""
        try:
            result = self.pipeline.query_graph(question)
            return result
        except Exception as e:
            return f"Error querying graph: {str(e)}"
    
    def search_entities(self, entity_name: str) -> str:
        """Search for specific entities in the knowledge graph"""
        try:
            with self.pipeline.driver.session() as session:
                result = session.run("""
                    MATCH (e:Entity)
                    WHERE toLower(e.name) CONTAINS toLower($entity)
                    OPTIONAL MATCH (e)-[r:RELATION]->(target:Entity)
                    RETURN e.name as entity, 
                           collect(DISTINCT {relation: r.type, target: target.name}) as connections
                    LIMIT 10
                """, entity=entity_name)
                
                entities = []
                for record in result:
                    connections = [f"{c['relation']} -> {c['target']}" 
                                 for c in record['connections'] if c['target']]
                    entities.append({
                        'entity': record['entity'],
                        'connections': connections
                    })
                
                if not entities:
                    return f"No entities found matching '{entity_name}'"
                
                return json.dumps(entities, indent=2)
        except Exception as e:
            return f"Error searching entities: {str(e)}"
    
    def get_graph_statistics(self) -> str:
        """Get statistics about the knowledge graph"""
        try:
            with self.pipeline.driver.session() as session:
                stats = {}
                
                nodes = session.run("MATCH (n:Entity) RETURN count(n) as count").single()
                stats['total_entities'] = nodes["count"] if nodes else 0
                
                rels = session.run("MATCH ()-[r:RELATION]->() RETURN count(r) as count").single()
                stats['total_relationships'] = rels["count"] if rels else 0
                
                rel_types = session.run("""
                    MATCH ()-[r:RELATION]->()
                    RETURN r.type as type, count(*) as count
                    ORDER BY count DESC
                    LIMIT 10
                """)
                stats['top_relationship_types'] = [
                    {'type': record['type'], 'count': record['count']}
                    for record in rel_types
                ]
                
                top_entities = session.run("""
                    MATCH (e:Entity)-[r:RELATION]->()
                    RETURN e.name as entity, count(r) as connections
                    ORDER BY connections DESC
                    LIMIT 5
                """)
                stats['most_connected_entities'] = [
                    {'entity': record['entity'], 'connections': record['connections']}
                    for record in top_entities
                ]
                
                return json.dumps(stats, indent=2)
        except Exception as e:
            return f"Error getting statistics: {str(e)}"
    
    def run(self, query: str, chat_history: Optional[List] = None) -> Dict[str, Any]:
        """Run the graph agent"""
        try:
            query_lower = query.lower()
            
            if "statistic" in query_lower or "how many" in query_lower or "count" in query_lower:
                context = self.get_graph_statistics()
                tool_used = "get_graph_statistics"
            elif "search" in query_lower or "find entity" in query_lower:
                words = query.split()
                entity_words = [w for w in words if w.lower() not in ["search", "find", "entity", "for", "the", "a", "an"]]
                entity_name = " ".join(entity_words[:2]) if entity_words else query
                context = self.search_entities(entity_name)
                tool_used = "search_entities"
            else:
                context = self.query_knowledge_graph(query)
                tool_used = "query_knowledge_graph"
            
            messages = []
            if chat_history:
                messages.extend(chat_history[-6:])
            
            prompt = f"""You are a helpful AI assistant analyzing a knowledge graph.

Question: {query}

Knowledge Graph Data:
{context}

Based on the knowledge graph data above, provide a clear and helpful answer.
If the data is empty, let the user know they need to upload documents first."""

            messages.append(HumanMessage(content=prompt))
            response = self.llm.invoke(messages)
            
            return {
                "output": response.content,
                "success": True,
                "tool_used": tool_used
            }
        except Exception as e:
            return {
                "output": f"Graph agent error: {str(e)}",
                "success": False
            }


class SQLAgent:
    """
    Agent for text-to-SQL queries on relational database
    Uses LangChain SQL chain for natural language to SQL conversion
    """
    def __init__(self, db_path: str = None):
        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0
        )
        
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data.db")
        
        self.db_path = db_path
        self._initialize_database()
        self.db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")
    
    def _initialize_database(self):
        """Initialize SQLite database with sample schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                product TEXT,
                amount DECIMAL(10,2),
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                price DECIMAL(10,2),
                stock INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("SELECT COUNT(*) FROM customers")
        if cursor.fetchone()[0] == 0:
            cursor.executemany(
                "INSERT INTO customers (name, email) VALUES (?, ?)",
                [
                    ("John Doe", "john@example.com"),
                    ("Jane Smith", "jane@example.com"),
                    ("Bob Johnson", "bob@example.com"),
                ]
            )
            
            cursor.executemany(
                "INSERT INTO orders (customer_id, product, amount) VALUES (?, ?, ?)",
                [
                    (1, "Laptop", 999.99),
                    (1, "Mouse", 29.99),
                    (2, "Keyboard", 79.99),
                    (3, "Monitor", 299.99),
                ]
            )
            
            cursor.executemany(
                "INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)",
                [
                    ("Laptop", "Electronics", 999.99, 50),
                    ("Mouse", "Electronics", 29.99, 200),
                    ("Keyboard", "Electronics", 79.99, 150),
                    ("Monitor", "Electronics", 299.99, 75),
                    ("Desk", "Furniture", 399.99, 30),
                ]
            )
        
        conn.commit()
        conn.close()
    
    def get_schema(self) -> str:
        """Get database schema information"""
        try:
            return self.db.get_table_info()
        except Exception as e:
            return f"Error getting schema: {str(e)}"
    
    def execute_query(self, sql_query: str) -> str:
        """Execute SQL query and return results"""
        try:
            result = self.db.run(sql_query)
            return result
        except Exception as e:
            return f"Error executing query: {str(e)}"
    
    def text_to_sql(self, question: str) -> str:
        """Convert natural language question to SQL query"""
        try:
            sql_chain = create_sql_query_chain(self.llm, self.db)
            sql_query = sql_chain.invoke({"question": question})
            return sql_query
        except Exception as e:
            return f"Error generating SQL: {str(e)}"
    
    def run(self, query: str, chat_history: Optional[List] = None) -> Dict[str, Any]:
        """Run the SQL agent with text-to-SQL capability"""
        try:
            query_lower = query.lower()
            
            if "schema" in query_lower or "tables" in query_lower or "structure" in query_lower:
                schema = self.get_schema()
                return {
                    "output": f"Database Schema:\n\n{schema}",
                    "success": True,
                    "tool_used": "get_schema"
                }
            
            sql_query = self.text_to_sql(query)
            results = self.execute_query(sql_query)
            
            messages = []
            if chat_history:
                messages.extend(chat_history[-6:])
            
            prompt = f"""You are a helpful AI assistant that helps users query a SQL database.

User Question: {query}

Generated SQL Query:
{sql_query}

Query Results:
{results}

Provide a clear, natural language answer to the user's question based on the query results.
Format numbers and data in a user-friendly way."""

            messages.append(HumanMessage(content=prompt))
            response = self.llm.invoke(messages)
            
            return {
                "output": response.content,
                "success": True,
                "tool_used": "text_to_sql",
                "sql_query": sql_query,
                "raw_results": results
            }
        except Exception as e:
            return {
                "output": f"SQL agent error: {str(e)}",
                "success": False
            }


class ResearchAgent:
    """
    Agent for research and document analysis
    """
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0.7
        )
    
    def analyze_document_topics(self) -> str:
        """Analyze main topics in knowledge base"""
        try:
            with self.pipeline.driver.session() as session:
                result = session.run("""
                    MATCH (e:Entity)-[r:RELATION]->(target:Entity)
                    RETURN e.name as entity, 
                           collect(DISTINCT r.type) as relationship_types,
                           count(*) as connections,
                           r.source as source
                    ORDER BY connections DESC
                    LIMIT 20
                """)
                
                topics = []
                for record in result:
                    topics.append({
                        'entity': record['entity'],
                        'relationship_types': record['relationship_types'],
                        'connections': record['connections'],
                        'source': record['source']
                    })
                
                return json.dumps(topics, indent=2)
        except Exception as e:
            return f"Error analyzing topics: {str(e)}"
    
    def compare_documents(self) -> str:
        """Compare different documents"""
        try:
            with self.pipeline.driver.session() as session:
                result = session.run("""
                    MATCH ()-[r:RELATION]->()
                    WITH r.source as document, count(*) as fact_count
                    RETURN document, fact_count
                    ORDER BY fact_count DESC
                """)
                
                docs = [{'document': record['document'], 
                        'facts': record['fact_count']} 
                       for record in result]
                
                return json.dumps(docs, indent=2)
        except Exception as e:
            return f"Error comparing documents: {str(e)}"
    
    def run(self, query: str, chat_history: Optional[List] = None) -> Dict[str, Any]:
        """Run the research agent"""
        try:
            query_lower = query.lower()
            
            if "compare" in query_lower or "difference" in query_lower:
                context = self.compare_documents()
                tool_used = "compare_documents"
            elif "topic" in query_lower or "theme" in query_lower or "analyze" in query_lower:
                context = self.analyze_document_topics()
                tool_used = "analyze_topics"
            else:
                context = self.pipeline.query_graph(query)
                tool_used = "deep_query"
            
            messages = []
            if chat_history:
                messages.extend(chat_history[-6:])
            
            prompt = f"""You are a research-focused AI assistant analyzing documents.

Research Question: {query}

Data:
{context}

Provide a detailed, well-researched answer. Identify patterns, themes, and insights.
If the data is empty, let the user know they need to upload documents first."""

            messages.append(HumanMessage(content=prompt))
            response = self.llm.invoke(messages)
            
            return {
                "output": response.content,
                "success": True,
                "tool_used": tool_used
            }
        except Exception as e:
            return {
                "output": f"Research agent error: {str(e)}",
                "success": False
            }


class AgentOrchestrator:
    """
    Orchestrates multiple agents: Graph, SQL, Research
    Routes queries to the appropriate agent based on intent
    """
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.graph_agent = GraphAgent(pipeline)
        self.sql_agent = SQLAgent()
        self.research_agent = ResearchAgent(pipeline)
        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0
        )
    
    def route_query(self, query: str) -> str:
        """Determine which agent should handle the query"""
        query_lower = query.lower()
        
        sql_keywords = ["customer", "order", "product", "price", "total", "sum", "average", 
                       "count", "table", "schema", "database", "sql", "select", "buy", "purchase"]
        research_keywords = ["analyze", "compare", "summarize", "theme", "topic", "research", "findings"]
        graph_keywords = ["entity", "relationship", "connection", "path", "knowledge graph", "search", "find"]
        
        if any(keyword in query_lower for keyword in sql_keywords):
            return "sql"
        if any(keyword in query_lower for keyword in research_keywords):
            return "research"
        if any(keyword in query_lower for keyword in graph_keywords):
            return "graph"
        
        if query.startswith(("How many", "What is the total", "Show me", "List all")):
            return "sql"
        elif query.startswith(("What are", "Analyze", "Compare", "Summarize")):
            return "research"
        else:
            return "graph"
    
    def run(self, query: str, chat_history: Optional[List] = None, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Run the appropriate agent based on query type"""
        if agent_type is None:
            agent_type = self.route_query(query)
        
        if agent_type == "sql":
            result = self.sql_agent.run(query, chat_history)
            result["agent_used"] = "sql"
        elif agent_type == "research":
            result = self.research_agent.run(query, chat_history)
            result["agent_used"] = "research"
        else:
            result = self.graph_agent.run(query, chat_history)
            result["agent_used"] = "graph"
        
        return result
