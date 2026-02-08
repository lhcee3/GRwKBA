"""
Memory management for maintaining conversation context
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_groq import ChatGroq
from config import settings
import json


class ConversationMemory:
    """
    Manages conversation history with memory buffer
    """
    def __init__(self, session_id: str, max_messages: int = 10):
        self.session_id = session_id
        self.max_messages = max_messages
        self.messages: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "message_count": 0
        }
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.messages.append(message)
        self.metadata["message_count"] += 1
        
        # Keep only the last N messages to prevent memory overflow
        if len(self.messages) > self.max_messages * 2:  # *2 for user + assistant pairs
            self.messages = self.messages[-self.max_messages * 2:]
    
    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation messages"""
        if limit:
            return self.messages[-limit:]
        return self.messages
    
    def get_langchain_messages(self, limit: Optional[int] = None) -> List[BaseMessage]:
        """Convert messages to LangChain format"""
        messages = self.get_messages(limit)
        langchain_messages = []
        
        for msg in messages:
            if msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))
        
        return langchain_messages
    
    def clear(self):
        """Clear conversation history"""
        self.messages = []
        self.metadata["message_count"] = 0
        self.metadata["cleared_at"] = datetime.now().isoformat()
    
    def get_summary(self) -> str:
        """Get a summary of the conversation"""
        if not self.messages:
            return "No conversation history"
        
        summary = f"Session: {self.session_id}\n"
        summary += f"Messages: {self.metadata['message_count']}\n"
        summary += f"Created: {self.metadata['created_at']}\n"
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Export memory to dictionary"""
        return {
            "session_id": self.session_id,
            "messages": self.messages,
            "metadata": self.metadata
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Import memory from dictionary"""
        self.session_id = data.get("session_id", self.session_id)
        self.messages = data.get("messages", [])
        self.metadata = data.get("metadata", self.metadata)


class SummarizedMemory:
    """
    Memory with automatic summarization for long conversations
    """
    def __init__(self, session_id: str, max_tokens: int = 2000):
        self.session_id = session_id
        self.max_tokens = max_tokens
        self.llm = ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0
        )
        self.summary = ""
        self.recent_messages: List[Dict[str, Any]] = []
        self.message_count = 0
    
    def add_message(self, role: str, content: str):
        """Add message and summarize if needed"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        self.recent_messages.append(message)
        self.message_count += 1
        
        # Summarize if we have too many recent messages
        if len(self.recent_messages) > 10:
            self._summarize_and_prune()
    
    def _summarize_and_prune(self):
        """Summarize old messages and keep recent ones"""
        if len(self.recent_messages) <= 6:
            return
        
        # Take older messages for summarization
        messages_to_summarize = self.recent_messages[:-4]
        
        # Create conversation text
        conversation = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in messages_to_summarize
        ])
        
        # Generate summary
        prompt = f"""Summarize this conversation concisely, capturing key topics and important information:

{conversation}

Provide a brief summary (2-3 sentences):"""
        
        response = self.llm.invoke(prompt)
        new_summary = response.content
        
        # Update summary
        if self.summary:
            self.summary += "\n\n" + new_summary
        else:
            self.summary = new_summary
        
        # Keep only recent messages
        self.recent_messages = self.recent_messages[-4:]
    
    def get_context(self) -> str:
        """Get full context including summary and recent messages"""
        context_parts = []
        
        if self.summary:
            context_parts.append(f"Previous conversation summary:\n{self.summary}")
        
        if self.recent_messages:
            recent = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in self.recent_messages
            ])
            context_parts.append(f"Recent conversation:\n{recent}")
        
        return "\n\n".join(context_parts)
    
    def get_langchain_messages(self) -> List[BaseMessage]:
        """Get recent messages in LangChain format"""
        messages = []
        for msg in self.recent_messages:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        return messages
    
    def clear(self):
        """Clear all memory"""
        self.summary = ""
        self.recent_messages = []
        self.message_count = 0


class MemoryManager:
    """
    Manages multiple conversation sessions
    """
    def __init__(self):
        self.sessions: Dict[str, ConversationMemory] = {}
        self.summarized_sessions: Dict[str, SummarizedMemory] = {}
    
    def get_session(self, session_id: str, use_summarization: bool = False) -> Any:
        """Get or create a conversation session"""
        if use_summarization:
            if session_id not in self.summarized_sessions:
                self.summarized_sessions[session_id] = SummarizedMemory(session_id)
            return self.summarized_sessions[session_id]
        else:
            if session_id not in self.sessions:
                self.sessions[session_id] = ConversationMemory(session_id)
            return self.sessions[session_id]
    
    def delete_session(self, session_id: str):
        """Delete a conversation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.summarized_sessions:
            del self.summarized_sessions[session_id]
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions"""
        sessions = []
        
        for session_id, memory in self.sessions.items():
            sessions.append({
                "session_id": session_id,
                "type": "buffer",
                "message_count": memory.metadata["message_count"],
                "created_at": memory.metadata["created_at"]
            })
        
        for session_id, memory in self.summarized_sessions.items():
            sessions.append({
                "session_id": session_id,
                "type": "summarized",
                "message_count": memory.message_count,
                "has_summary": bool(memory.summary)
            })
        
        return sessions
    
    def clear_all(self):
        """Clear all sessions"""
        self.sessions.clear()
        self.summarized_sessions.clear()


# Global memory manager instance
memory_manager = MemoryManager()
