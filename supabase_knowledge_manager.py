"""
Supabase Knowledge Base Manager for AI Debate Agents
Handles persistent knowledge storage and retrieval with semantic search
"""

import os
import logging
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from supabase import create_client, Client
from dotenv import load_dotenv
import PyPDF2
import re
import hashlib

load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseKnowledgeManager:
    """Manages knowledge base operations in Supabase for AI agents"""
    
    def __init__(self, knowledge_dir: str = "./knowledge_documents"):
        self.knowledge_dir = Path(knowledge_dir)
        
        # Supabase configuration - use service role for backend operations
        self.supabase_url = os.getenv("SUPABASE_URL", "https://zpfouxphwgtqhgalzyqk.supabase.co")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpwZm91eHBod2d0cWhnYWx6eXFrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk1OTc5MTYsImV4cCI6MjA2NTE3MzkxNn0.uzlPeumvFwJKdGR5rHyclBkc5ZMFH5NhJ41iROfRZmU")
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("Supabase credentials not found in environment")
            self.client = None
        else:
            try:
                self.client: Client = create_client(self.supabase_url, self.supabase_key)
                logger.info(f"✅ Supabase Knowledge Manager initialized (using {'service_role' if 'SUPABASE_SERVICE_ROLE_KEY' in os.environ else 'anon'} key)")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.client = None
        
        self.chunk_size = 1000  # Characters per chunk
        self.overlap_size = 200  # Overlap between chunks
        
    async def initialize_knowledge_base(self) -> bool:
        """Initialize knowledge base by loading documents from files into Supabase"""
        if not self.client:
            logger.error("Supabase client not available")
            return False
            
        try:
            logger.info("🧠 Initializing Supabase knowledge base...")
            
            if not self.knowledge_dir.exists():
                logger.warning(f"Knowledge directory not found: {self.knowledge_dir}")
                return False
            
            success_count = 0
            agent_dirs = ["aristotle", "socrates"]  # Available agent directories
            
            for agent_name in agent_dirs:
                agent_dir = self.knowledge_dir / agent_name
                if agent_dir.exists():
                    count = await self._load_agent_documents(agent_name, agent_dir)
                    if count > 0:
                        success_count += 1
                        logger.info(f"✅ {agent_name.title()}: {count} documents loaded to Supabase")
                    else:
                        logger.warning(f"⚠️ {agent_name.title()}: No documents processed")
                else:
                    logger.warning(f"⚠️ {agent_name.title()}: Directory not found")
            
            logger.info(f"🎉 Supabase knowledge base initialization complete: {success_count}/{len(agent_dirs)} agents ready")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase knowledge base: {e}")
            return False
    
    async def _load_agent_documents(self, agent_name: str, agent_dir: Path) -> int:
        """Load all PDF documents for a specific agent into Supabase"""
        try:
            pdf_files = list(agent_dir.glob("*.pdf"))
            loaded_count = 0
            
            for pdf_file in pdf_files:
                try:
                    # Extract text content
                    text_content = await self._extract_pdf_text(pdf_file)
                    if not text_content or len(text_content.strip()) < 100:
                        logger.warning(f"Insufficient content in {pdf_file.name}")
                        continue
                    
                    # Create summary
                    summary = self._create_summary(text_content, pdf_file.name)
                    
                    # Extract keywords
                    keywords = self._extract_keywords(text_content)
                    
                    # Get file stats
                    file_stats = pdf_file.stat()
                    
                    # Store document in Supabase
                    document_id = await self._store_document(
                        agent_name=agent_name,
                        document_name=pdf_file.name,
                        file_path=str(pdf_file),
                        content_text=text_content,
                        summary=summary,
                        keywords=keywords,
                        file_size_bytes=file_stats.st_size
                    )
                    
                    if document_id:
                        # Create and store chunks
                        chunks = self._create_chunks(text_content)
                        chunk_count = await self._store_chunks(document_id, chunks)
                        
                        if chunk_count > 0:
                            loaded_count += 1
                            logger.debug(f"Stored {pdf_file.name} for {agent_name}: {len(text_content)} chars, {chunk_count} chunks")
                        else:
                            logger.warning(f"Failed to store chunks for {pdf_file.name}")
                    else:
                        logger.warning(f"Failed to store document {pdf_file.name}")
                        
                except Exception as e:
                    logger.error(f"Failed to process {pdf_file.name}: {e}")
                    continue
            
            return loaded_count
            
        except Exception as e:
            logger.error(f"Error loading documents for {agent_name}: {e}")
            return 0
    
    async def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text content from PDF file"""
        try:
            text_content = ""
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            text_content += f"\n--- Page {page_num + 1} ---\n{page_text}"
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num + 1} from {pdf_path.name}: {e}")
                        continue
            
            # Clean up the text
            text_content = self._clean_text(text_content)
            return text_content
            
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]  # Remove empty lines
        
        # Join with single spaces, but preserve paragraph breaks
        cleaned_text = ""
        for i, line in enumerate(lines):
            if i > 0 and not line.startswith('---'):
                # Add space between lines, double space for new sections
                if lines[i-1].endswith('.') or lines[i-1].startswith('---'):
                    cleaned_text += "\n\n" + line
                else:
                    cleaned_text += " " + line
            else:
                cleaned_text += line
        
        return cleaned_text.strip()
    
    def _create_summary(self, content: str, filename: str) -> str:
        """Create a brief summary of the document content"""
        # Extract first meaningful paragraph as summary
        paragraphs = content.split('\n\n')
        
        for paragraph in paragraphs:
            if len(paragraph.strip()) > 50 and not paragraph.startswith('---'):
                # Take first 200 characters of substantial content
                summary = paragraph.strip()[:200]
                if len(paragraph) > 200:
                    summary += "..."
                return summary
        
        # Fallback to filename-based description
        name_map = {
            "parliamentary": "Parliamentary procedure and meeting management",
            "socratic": "Socratic questioning techniques and critical thinking",
            "systems": "Systems thinking frameworks and analysis tools", 
            "buddhist": "Buddhist meditation and conflict resolution methods",
            "mindful": "Mindful communication and peace-making approaches",
            "conflicts": "Conflict resolution and mediation techniques"
        }
        
        filename_lower = filename.lower()
        for key, description in name_map.items():
            if key in filename_lower:
                return description
        
        return f"Knowledge document: {filename}"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text"""
        # Simple keyword extraction - in production, could use more sophisticated NLP
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        
        # Common important terms for debate context
        important_terms = [
            'debate', 'argument', 'logic', 'reasoning', 'question', 'answer',
            'socratic', 'aristotelian', 'philosophical', 'ethics', 'morality',
            'parliamentary', 'procedure', 'meeting', 'moderation', 'facilitation',
            'conflict', 'resolution', 'mediation', 'mindfulness', 'communication'
        ]
        
        # Find keywords that appear frequently or are contextually important
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Prioritize important terms and frequent words
        keywords = []
        for term in important_terms:
            if term in word_counts:
                keywords.append(term)
        
        # Add most frequent words not already included
        frequent_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        for word, count in frequent_words:
            if word not in keywords and count > 3:
                keywords.append(word)
        
        return keywords[:15]  # Limit to 15 keywords
    
    def _create_chunks(self, text: str) -> List[Dict]:
        """Create chunks from text for better search granularity"""
        chunks = []
        text_length = len(text)
        start_pos = 0
        chunk_index = 0
        
        while start_pos < text_length:
            # Calculate end position
            end_pos = min(start_pos + self.chunk_size, text_length)
            
            # Try to end at a sentence boundary if possible
            if end_pos < text_length:
                # Look for sentence endings within the last 100 characters
                search_start = max(end_pos - 100, start_pos)
                sentence_end = text.rfind('.', search_start, end_pos)
                if sentence_end > start_pos:
                    end_pos = sentence_end + 1
            
            # Extract chunk text
            chunk_text = text[start_pos:end_pos].strip()
            
            if chunk_text:
                # Create chunk summary (first sentence or first 100 chars)
                first_sentence = chunk_text.split('.')[0]
                if len(first_sentence) > 100:
                    chunk_summary = chunk_text[:100] + "..."
                else:
                    chunk_summary = first_sentence + "."
                
                # Extract keywords for this chunk
                chunk_keywords = self._extract_keywords(chunk_text)
                
                chunks.append({
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                    "chunk_summary": chunk_summary,
                    "context_keywords": chunk_keywords
                })
                
                chunk_index += 1
            
            # Move start position, with overlap
            start_pos = max(end_pos - self.overlap_size, start_pos + 1)
            
            # Prevent infinite loop
            if start_pos >= end_pos:
                start_pos = end_pos
        
        return chunks
    
    async def _store_document(
        self, 
        agent_name: str, 
        document_name: str, 
        file_path: str, 
        content_text: str, 
        summary: str,
        keywords: List[str],
        file_size_bytes: int
    ) -> Optional[str]:
        """Store document in Supabase knowledge_documents table"""
        if not self.client:
            return None
            
        try:
            # Calculate page count (rough estimate)
            estimated_pages = max(1, len(content_text) // 3000)
            
            result = self.client.rpc('upsert_knowledge_document', {
                'p_agent_name': agent_name,
                'p_document_name': document_name,
                'p_file_path': file_path,
                'p_content_text': content_text,
                'p_summary': summary,
                'p_document_type': 'pdf',
                'p_keywords': json.dumps(keywords),
                'p_file_size_bytes': file_size_bytes,
                'p_page_count': estimated_pages
            }).execute()
            
            if result.data:
                return result.data
            else:
                logger.error(f"Failed to store document {document_name}: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error storing document {document_name}: {e}")
            return None
    
    async def _store_chunks(self, document_id: str, chunks: List[Dict]) -> int:
        """Store document chunks in Supabase knowledge_chunks table"""
        if not self.client:
            return 0
            
        try:
            result = self.client.rpc('store_knowledge_chunks', {
                'p_document_id': document_id,
                'p_chunks': json.dumps(chunks)
            }).execute()
            
            if result.data is not None:
                return result.data
            else:
                logger.error(f"Failed to store chunks for document {document_id}: {result}")
                return 0
                
        except Exception as e:
            logger.error(f"Error storing chunks for document {document_id}: {e}")
            return 0
    
    async def search_knowledge(
        self, 
        agent_name: str, 
        query_terms: List[str], 
        max_results: int = 5
    ) -> List[Dict]:
        """Search knowledge base for relevant information"""
        if not self.client:
            logger.warning("Supabase client not available for knowledge search")
            return []
            
        try:
            result = self.client.rpc('search_agent_knowledge', {
                'p_agent_name': agent_name,
                'p_search_terms': query_terms,
                'p_limit': max_results
            }).execute()
            
            if result.data:
                # Format results for consistency with original interface
                formatted_results = []
                for item in result.data:
                    formatted_results.append({
                        'source': item['document_name'],
                        'content': item['chunk_text'],
                        'summary': item['chunk_summary'] or '',
                        'relevance_score': float(item['relevance_score'])
                    })
                
                # Sort by relevance score
                formatted_results.sort(key=lambda x: x['relevance_score'], reverse=True)
                return formatted_results
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error searching knowledge for {agent_name}: {e}")
            return []
    
    async def get_agent_knowledge(
        self, 
        agent_name: str, 
        query_context: str, 
        max_items: int = 3
    ) -> List[Dict]:
        """
        Retrieve relevant knowledge for an agent based on query context
        Compatible with original interface for backward compatibility
        """
        # Extract search terms from query context
        query_terms = self._extract_search_terms(query_context)
        
        # Search knowledge base
        results = await self.search_knowledge(agent_name, query_terms, max_items)
        
        if not results:
            logger.debug(f"No knowledge found for {agent_name} with query: {query_context}")
        
        return results
    
    def _extract_search_terms(self, query_context: str) -> List[str]:
        """Extract meaningful search terms from a query context"""
        # Simple term extraction - could be enhanced with NLP
        words = re.findall(r'\b[a-zA-Z]{3,}\b', query_context.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'this', 'that', 'these', 'those', 'is', 'are', 'was', 'were',
            'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'can', 'may', 'might', 'must', 'shall'
        }
        
        meaningful_terms = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Limit to most relevant terms
        return meaningful_terms[:8]
    
    async def get_knowledge_status(self) -> Dict:
        """Get status of knowledge base in Supabase"""
        if not self.client:
            return {"status": "unavailable", "reason": "Supabase client not initialized"}
            
        try:
            # Get document counts by agent
            docs_result = self.client.table("knowledge_documents").select(
                "agent_name", count="exact"
            ).execute()
            
            # Get chunk counts
            chunks_result = self.client.table("knowledge_chunks").select(
                "id", count="exact"
            ).execute()
            
            agent_counts = {}
            if docs_result.data is not None:
                # Count documents per agent
                agent_docs = self.client.table("knowledge_documents").select(
                    "agent_name"
                ).execute()
                
                for doc in agent_docs.data or []:
                    agent = doc['agent_name']
                    agent_counts[agent] = agent_counts.get(agent, 0) + 1
            
            return {
                "status": "ready",
                "backend": "supabase",
                "total_documents": docs_result.count or 0,
                "total_chunks": chunks_result.count or 0,
                "agents": agent_counts,
                "features": ["semantic_search", "chunked_retrieval", "persistent_storage"]
            }
            
        except Exception as e:
            logger.error(f"Error getting knowledge status: {e}")
            return {"status": "error", "reason": str(e)}

# Global instance
_supabase_knowledge_manager = SupabaseKnowledgeManager()

# Compatibility functions for existing code
async def initialize_supabase_knowledge_base() -> bool:
    """Initialize Supabase knowledge base (called by AI agents system)"""
    return await _supabase_knowledge_manager.initialize_knowledge_base()

async def get_agent_knowledge_supabase(agent_name: str, query_context: str, max_items: int = 3) -> List[Dict]:
    """Get agent knowledge from Supabase (enhanced version)"""
    return await _supabase_knowledge_manager.get_agent_knowledge(agent_name, query_context, max_items)

async def get_supabase_knowledge_status() -> Dict:
    """Get Supabase knowledge base status"""
    return await _supabase_knowledge_manager.get_knowledge_status() 