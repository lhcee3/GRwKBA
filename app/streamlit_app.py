import streamlit as st
import requests
from pathlib import Path
import time
from streamlit_agraph import agraph, Node, Edge, Config

st.set_page_config(page_title="GraphRAG", page_icon="�", layout="wide")

API_URL = "http://localhost:8000"

def check_backend():
    try:
        response = requests.get(f"{API_URL}/", timeout=2)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return False

backend_connected = check_backend()

if not backend_connected:
    st.error("Backend not connected")
    st.warning(f"Cannot connect to API at {API_URL}")
    
    with st.expander("Troubleshooting Steps", expanded=True):
        st.markdown("""
        **Backend is not running. Please follow these steps:**
        
        1. **Check if FastAPI server is running:**
           ```bash
           uvicorn app.main:app --reload
           ```
        
        2. **Verify Neo4j is running:**
           ```bash
           docker ps | grep neo4j
           docker-compose up -d neo4j
           ```
        
        3. **Test API manually:**
           - Open browser: http://localhost:8000/docs
           - Should see FastAPI docs
        
        4. **Check terminal for errors:**
           - Look for Python import errors
           - Check Neo4j connection errors
           - Verify GROQ_API_KEY is set in .env
        
        5. **Common issues:**
           - Port 8000 already in use
           - Missing dependencies: `pip install -r app/requirements.txt`
           - Neo4j not started
           - Wrong directory: Must run from gr-rag folder
        """)
        
        if st.button("Retry Connection"):
            st.rerun()
    
    st.stop()
else:
    st.success("Backend connected")

st.title("GraphRAG Knowledge Base")

with st.sidebar:
    st.header("Upload Documents")
    
    if st.button("Clear All Knowledge", type="secondary", use_container_width=True):
        try:
            response = requests.delete(f"{API_URL}/graph/clear")
            if response.status_code == 200:
                if 'processed_files' in st.session_state:
                    st.session_state.processed_files = []
                st.success("Graph cleared successfully!")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    st.divider()
    
    uploaded_files = st.file_uploader(
        "Upload PDF/DOCX/TXT",
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True
    )
    
    if 'processed_files' not in st.session_state:
        st.session_state.processed_files = []
    
    if uploaded_files:
        for file in uploaded_files:
            if st.button(f"Process {file.name}"):
                with st.spinner(f"Processing {file.name}..."):
                    try:
                        files = {"file": (file.name, file, file.type)}
                        response = requests.post(f"{API_URL}/upload", files=files)
                        
                        if response.status_code == 200:
                            data = response.json()
                            st.success(f"Processed {file.name}")
                            st.json(data["details"])
                            
                            if file.name not in st.session_state.processed_files:
                                st.session_state.processed_files.append(file.name)
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")
    
    if st.session_state.processed_files:
        st.divider()
        st.subheader("Connected Files")
        for filename in st.session_state.processed_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(filename)
            with col2:
                if st.button("Delete", key=f"del_{filename}"):
                    try:
                        response = requests.delete(f"{API_URL}/document/{filename}")
                        if response.status_code == 200:
                            st.session_state.processed_files.remove(filename)
                            st.rerun()
                    except:
                        pass
    
    st.divider()
    
    try:
        stats = requests.get(f"{API_URL}/graph/stats").json()
        st.metric("Graph Nodes", stats["nodes"])
        st.metric("Relationships", stats["relationships"])
    except:
        pass

# Create tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["Chat", "Force Graph", "Hierarchical View", "Neo4j Browser"])

with tab4:
    st.header("Neo4j Browser Access")
    st.markdown("""
    ### Access Neo4j Browser directly
    
    Neo4j Browser provides advanced graph querying and visualization capabilities.
    
    **Connection Details:**
    - **URL:** [http://localhost:7474](http://localhost:7474)
    - **Username:** `neo4j`
    - **Password:** `password123`
    
    **Useful Cypher Queries:**
    ```cypher
    // View all nodes and relationships
    MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50
    
    // View all entities
    MATCH (n:Entity) RETURN n
    
    // Find relationships by document
    MATCH (s)-[r:RELATION]->(t) 
    WHERE r.source = 'your_document.pdf' 
    RETURN s, r, t
    
    // Find entities connected to a specific entity
    MATCH (n:Entity {name: 'EntityName'})-[r]-(connected)
    RETURN n, r, connected
    ```
    """)
    st.info("Click the URL above to open Neo4j Browser in a new tab")

with tab3:
    st.header("Hierarchical Graph View")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Refresh", key="refresh_hierarchical", use_container_width=True):
            st.rerun()
    
    try:
        response = requests.get(f"{API_URL}/graph/visualize")
        if response.status_code == 200:
            graph_data = response.json()
            
            if graph_data["nodes"] and graph_data["edges"]:
                # Create nodes for hierarchical view
                nodes = []
                for idx, node in enumerate(graph_data["nodes"]):
                    nodes.append(
                        Node(
                            id=node["id"],
                            label=node["label"],
                            size=350,
                            color="#00D9FF",
                            shape="box",
                            font={"size": 14, "color": "#FFFFFF", "face": "monospace", "bold": True}
                        )
                    )
                
                # Create edges
                edges = []
                for edge in graph_data["edges"]:
                    edges.append(
                        Edge(
                            source=edge["source"],
                            target=edge["target"],
                            label=edge["type"],
                            color="#666666",
                            width=2
                        )
                    )
                
                # Hierarchical layout configuration
                config = Config(
                    width=1200,
                    height=700,
                    directed=True,
                    physics=False,
                    hierarchical=True,
                    nodeHighlightBehavior=True,
                    highlightColor="#FF6B6B",
                    node={
                        'labelProperty': 'label',
                        'renderLabel': True
                    },
                    link={
                        'labelProperty': 'label', 
                        'renderLabel': True,
                        'fontSize': 12,
                        'fontColor': '#CCCCCC'
                    }
                )
                
                st.markdown("""
                    <style>
                        iframe {
                            background-color: #0f0f23 !important;
                            border-radius: 10px;
                            border: 2px solid #444;
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                agraph(nodes=nodes, edges=edges, config=config)
                
                st.divider()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Entities", len(nodes))
                with col2:
                    st.metric("Total Relationships", len(edges))
                with col3:
                    docs = set(edge["document"] for edge in graph_data["edges"])
                    st.metric("Documents Connected", len(docs))
            else:
                st.info("No graph data available yet. Upload documents to build your knowledge graph!")
        else:
            st.error("Failed to fetch graph data")
    except Exception as e:
        st.error(f"Error loading graph: {str(e)}")

with tab2:
    st.header("Force-Directed Graph View")
    
    st.info("Interactive force-directed layout with physics simulation. Drag nodes to reorganize.")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("Refresh", key="refresh_force", use_container_width=True):
            st.rerun()
    
    try:
        response = requests.get(f"{API_URL}/graph/visualize")
        if response.status_code == 200:
            graph_data = response.json()
            
            if graph_data["nodes"] and graph_data["edges"]:
                # Color palette for better visibility
                node_colors = ["#00E676", "#FF6B6B", "#4ECDC4", "#FFD93D", "#A78BFA", "#F472B6", "#60A5FA", "#FB923C"]
                
                # Create nodes for visualization with varied colors
                nodes = []
                for idx, node in enumerate(graph_data["nodes"]):
                    nodes.append(
                        Node(
                            id=node["id"],
                            label=node["label"],
                            size=400,  # Larger nodes for better visibility
                            color=node_colors[idx % len(node_colors)],
                            shape="dot",
                            font={"size": 16, "color": "#FFFFFF", "face": "arial", "bold": True}
                        )
                    )
                
                # Create edges for visualization with colors
                edges = []
                edge_colors = ["#FFD700", "#00CED1", "#FF69B4", "#32CD32", "#FF4500"]
                for idx, edge in enumerate(graph_data["edges"]):
                    edges.append(
                        Edge(
                            source=edge["source"],
                            target=edge["target"],
                            label=edge["type"],
                            type="CURVE_SMOOTH",
                            color=edge_colors[idx % len(edge_colors)],
                            width=3
                        )
                    )
                
                # Configure graph appearance with dark background
                config = Config(
                    width=1200,
                    height=700,
                    directed=True,
                    physics=True,
                    hierarchical=False,
                    nodeHighlightBehavior=True,
                    highlightColor="#FFEB3B",
                    collapsible=True,
                    node={
                        'labelProperty': 'label',
                        'renderLabel': True
                    },
                    link={
                        'labelProperty': 'label', 
                        'renderLabel': True,
                        'fontSize': 14,
                        'fontColor': '#FFFFFF'
                    },
                    # Dark background for better contrast
                    d3={
                        'linkLength': 150,
                        'charge': -800,
                        'gravity': 0.1
                    }
                )
                
                # Add dark theme styling for better visibility
                st.markdown("""
                    <style>
                        iframe {
                            background-color: #1a1a2e !important;
                            border-radius: 10px;
                            border: 2px solid #00D9FF;
                        }
                    </style>
                """, unsafe_allow_html=True)
                
                # Display the graph
                agraph(nodes=nodes, edges=edges, config=config)
                
                # Display graph statistics
                st.divider()
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Entities", len(nodes))
                with col2:
                    st.metric("Total Relationships", len(edges))
                with col3:
                    # Count unique documents
                    docs = set(edge["document"] for edge in graph_data["edges"])
                    st.metric("Documents Connected", len(docs))
                
                # Visual guide
                with st.expander("Visual Guide"):
                    st.markdown("""
                    **Graph Features:**
                    - **Colorful Nodes** - Each entity has a unique vibrant color
                    - **Colored Edges** - Relationships shown with bright connecting lines
                    - **Large Labels** - Bold white text for easy reading
                    - **Dark Background** - High contrast for better visibility
                    - **Interactive** - Drag nodes, zoom in/out, hover for details
                    - **Physics Enabled** - Nodes repel each other for optimal spacing
                    
                    **Tips:**
                    - Drag any node to reorganize the layout
                    - Zoom with mouse wheel
                    - Hover over connections to see relationship types
                    - Yellow highlight appears when you click a node
                    """)
                
                # Show relationship details
                with st.expander("Relationship Details"):
                    st.write("**Connections in your knowledge graph:**")
                    for edge in graph_data["edges"][:20]:  # Show first 20
                        # Find source and target names
                        source_name = next((n["label"] for n in graph_data["nodes"] if n["id"] == edge["source"]), "Unknown")
                        target_name = next((n["label"] for n in graph_data["nodes"] if n["id"] == edge["target"]), "Unknown")
                        st.text(f"• {source_name} → {edge['type']} → {target_name}")
                        st.caption(f"  Source: {edge['document']}")
                    
                    if len(graph_data["edges"]) > 20:
                        st.info(f"Showing 20 of {len(graph_data['edges'])} relationships")
            else:
                st.info("No graph data available yet. Upload documents to build your knowledge graph!")
                st.markdown("""
                **Get started:**
                1. Upload PDF, DOCX, or TXT files using the sidebar
                2. Click 'Process' to extract entities and relationships
                3. Return here to visualize the connections
                """)
        else:
            st.error("Failed to fetch graph data")
    except Exception as e:
        st.error(f"Error loading graph: {str(e)}")

with tab1:
    st.header("Ask Questions")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask about your documents..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{API_URL}/query",
                        json={"question": prompt}
                    )
                    
                    if response.status_code == 200:
                        answer = response.json()["answer"]
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        error_msg = f"Error: {response.text}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
                
                except Exception as e:
                    error_msg = f"Connection error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

