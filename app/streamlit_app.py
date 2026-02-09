import streamlit as st
import requests
from pathlib import Path
import time

st.set_page_config(page_title="GraphRAG", page_icon="🔗", layout="wide")

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

st.title("🔗 GraphRAG Knowledge Base")

with st.sidebar:
    st.header("📤 Upload Documents")
    
    if st.button("🗑️ Clear All Knowledge", type="secondary", use_container_width=True):
        try:
            response = requests.delete(f"{API_URL}/graph/clear")
            if response.status_code == 200:
                if 'processed_files' in st.session_state:
                    st.session_state.processed_files = []
                st.success("✅ Graph cleared!")
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
                            st.success(f"✅ Processed {file.name}")
                            st.json(data["details"])
                            
                            if file.name not in st.session_state.processed_files:
                                st.session_state.processed_files.append(file.name)
                        else:
                            st.error(f"Error: {response.text}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")
    
    if st.session_state.processed_files:
        st.divider()
        st.subheader("✅ Connected Files")
        for filename in st.session_state.processed_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(f"📄 {filename}")
            with col2:
                if st.button("🗑️", key=f"del_{filename}"):
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

st.header("💬 Ask Questions")

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

with st.expander("🔍 View Neo4j Browser"):
    st.markdown("[Open Neo4j Browser](http://localhost:7474)")
    st.caption("Login: neo4j / password123")
