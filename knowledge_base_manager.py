"""
Knowledge Base Manager for AI Debate Agents
Manages loading and retrieval of specialized knowledge for each philosophical agent
Enhanced with Supabase integration for persistent storage and better search
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import PyPDF2
from io import BytesIO

logger = logging.getLogger(__name__)

# Global knowledge storage (local fallback)
AGENT_KNOWLEDGE_BASE: Dict[str, List[Dict]] = {
    "solon": [],      # Parliamentary procedure and moderation (DEPRECATED - moved to aristotle)
    "aristotle": [],  # Logic, analysis, parliamentary procedure, conflict resolution  
    "socrates": [],   # Socratic questioning methods
    "hermes": [],     # Systems thinking and synthesis
    "buddha": []      # Conflict resolution and mindfulness
}

class KnowledgeBase:
    """Manages knowledge base operations for AI agents with Supabase integration"""
    
    def __init__(self, knowledge_dir: str = "./knowledge_documents"):
        self.knowledge_dir = Path(knowledge_dir)
        self.loaded = False
        self.supabase_available = False
        
        # Try to import and initialize Supabase knowledge manager
        try:
            from supabase_knowledge_manager import (
                SupabaseKnowledgeManager, 
                initialize_supabase_knowledge_base,
                get_agent_knowledge_supabase,
                get_supabase_knowledge_status
            )
            self.supabase_manager = SupabaseKnowledgeManager(knowledge_dir)
            self.supabase_available = True
            logger.info("🔗 Supabase knowledge integration available")
        except ImportError as e:
            logger.warning(f"Supabase knowledge manager not available: {e}")
            self.supabase_manager = None
        except Exception as e:
            logger.error(f"Failed to initialize Supabase knowledge manager: {e}")
            self.supabase_manager = None
        
    async def initialize_all_knowledge_bases(self) -> bool:
        """Initialize knowledge bases for all agents (both local and Supabase)"""
        try:
            logger.info("🧠 Initializing AI agent knowledge bases...")
            
            if not self.knowledge_dir.exists():
                logger.warning(f"Knowledge directory not found: {self.knowledge_dir}")
                return False
            
            # Try Supabase first for persistent storage
            supabase_success = False
            if self.supabase_available and self.supabase_manager:
                try:
                    supabase_success = await self.supabase_manager.initialize_knowledge_base()
                    if supabase_success:
                        logger.info("✅ Supabase knowledge base initialized successfully")
                    else:
                        logger.warning("⚠️ Supabase knowledge base initialization failed")
                except Exception as e:
                    logger.error(f"Supabase knowledge base initialization error: {e}")
            
            # Initialize local knowledge base as backup/fallback
            local_success = await self._initialize_local_knowledge_base()
            
            # Consider success if either works
            self.loaded = supabase_success or local_success
            
            if self.loaded:
                primary_source = "Supabase" if supabase_success else "Local"
                backup_source = "Local" if supabase_success else "None"
                logger.info(f"🎉 Knowledge base ready - Primary: {primary_source}, Backup: {backup_source}")
            else:
                logger.error("❌ Failed to initialize any knowledge base")
            
            return self.loaded
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize knowledge bases: {e}")
            return False
    
    async def _initialize_local_knowledge_base(self) -> bool:
        """Initialize local in-memory knowledge base"""
        try:
            success_count = 0
            agent_dirs = ["aristotle", "socrates", "hermes", "buddha"]  # Now aristotle has local knowledge base too
            
            for agent_name in agent_dirs:
                agent_dir = self.knowledge_dir / agent_name
                if agent_dir.exists():
                    count = await self._load_agent_knowledge(agent_name, agent_dir)
                    if count > 0:
                        success_count += 1
                        logger.info(f"✅ Local {agent_name.title()}: {count} documents loaded")
                    else:
                        logger.warning(f"⚠️ Local {agent_name.title()}: No documents found")
                else:
                    logger.warning(f"⚠️ Local {agent_name.title()}: Directory not found")
            
            local_success = success_count > 0
            logger.info(f"📁 Local knowledge base: {success_count}/{len(agent_dirs)} agents ready")
            
            return local_success
            
        except Exception as e:
            logger.error(f"Failed to initialize local knowledge base: {e}")
            return False
    
    async def _load_agent_knowledge(self, agent_name: str, agent_dir: Path) -> int:
        """Load all PDF documents for a specific agent (local storage)"""
        try:
            pdf_files = list(agent_dir.glob("*.pdf"))
            loaded_count = 0
            
            for pdf_file in pdf_files:
                try:
                    text_content = await self._extract_pdf_text(pdf_file)
                    if text_content and len(text_content.strip()) > 100:  # Minimum content check
                        
                        # Create knowledge entry
                        knowledge_entry = {
                            "source": pdf_file.name,
                            "content": text_content,
                            "file_path": str(pdf_file),
                            "agent": agent_name,
                            "summary": self._create_summary(text_content, pdf_file.name)
                        }
                        
                        AGENT_KNOWLEDGE_BASE[agent_name].append(knowledge_entry)
                        loaded_count += 1
                        
                        logger.debug(f"Loaded {pdf_file.name} for {agent_name}: {len(text_content)} characters")
                    else:
                        logger.warning(f"Insufficient content in {pdf_file.name}")
                        
                except Exception as e:
                    logger.error(f"Failed to load {pdf_file.name}: {e}")
                    continue
            
            return loaded_count
            
        except Exception as e:
            logger.error(f"Error loading knowledge for {agent_name}: {e}")
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
            "mindful": "Mindful communication and peace-making approaches"
        }
        
        filename_lower = filename.lower()
        for key, description in name_map.items():
            if key in filename_lower:
                return description
        
        return f"Knowledge document: {filename}"

    async def get_agent_knowledge_enhanced(
        self, 
        agent_name: str, 
        query_context: str, 
        max_items: int = 3
    ) -> List[Dict]:
        """
        Enhanced knowledge retrieval with Supabase integration
        
        Args:
            agent_name: Name of the agent (solon, aristotle, socrates, hermes, buddha)
            query_context: Context or topic to search for relevant knowledge
            max_items: Maximum number of knowledge items to return
        
        Returns:
            List of relevant knowledge items with content and sources
        """
        try:
            # Try Supabase first for better search capabilities
            if self.supabase_available and self.supabase_manager:
                try:
                    supabase_results = await self.supabase_manager.get_agent_knowledge(
                        agent_name, query_context, max_items
                    )
                    if supabase_results:
                        logger.debug(f"Retrieved {len(supabase_results)} items from Supabase for {agent_name}")
                        return supabase_results
                except Exception as e:
                    logger.warning(f"Supabase knowledge retrieval failed for {agent_name}: {e}")
            
            # Fallback to local knowledge base
            return await self._get_local_agent_knowledge(agent_name, query_context, max_items)
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge for {agent_name}: {e}")
            return []

    async def _get_local_agent_knowledge(
        self, 
        agent_name: str, 
        query_context: str, 
        max_items: int = 3
    ) -> List[Dict]:
        """Get agent knowledge from local storage (fallback method)"""
        try:
            if agent_name not in AGENT_KNOWLEDGE_BASE:
                logger.warning(f"Unknown agent: {agent_name}")
                return []
            
            knowledge_items = AGENT_KNOWLEDGE_BASE[agent_name]
            
            if not knowledge_items:
                logger.debug(f"No local knowledge available for {agent_name}")
                return []
            
            # Simple keyword matching for local search
            query_keywords = query_context.lower().split()
            scored_items = []
            
            for item in knowledge_items:
                score = 0
                content_lower = item.get('content', '').lower()
                summary_lower = item.get('summary', '').lower()
                
                # Calculate relevance score based on keyword matches
                for keyword in query_keywords:
                    if len(keyword) > 2:  # Skip very short words
                        score += content_lower.count(keyword) * 2
                        score += summary_lower.count(keyword) * 3
                
                if score > 0:
                    scored_items.append((score, item))
            
            # Sort by score and return top items
            scored_items.sort(key=lambda x: x[0], reverse=True)
            result = [item for score, item in scored_items[:max_items]]
            
            logger.debug(f"Retrieved {len(result)} local items for {agent_name} (query: {query_context[:50]}...)")
            return result
            
        except Exception as e:
            logger.error(f"Error in local knowledge retrieval for {agent_name}: {e}")
            return []

# Global knowledge base instance
_knowledge_base = KnowledgeBase()

async def initialize_knowledge_bases() -> bool:
    """Initialize knowledge bases for all agents (called by AI agents system)"""
    global _knowledge_base
    return await _knowledge_base.initialize_all_knowledge_bases()

async def get_agent_knowledge(agent_name: str, query_context: str, max_items: int = 3) -> List[Dict]:
    """
    Retrieve relevant knowledge for an agent based on query context
    Uses enhanced retrieval with Supabase integration and local fallback
    
    Args:
        agent_name: Name of the agent (solon, aristotle, socrates, hermes, buddha)
        query_context: Context or topic to search for relevant knowledge
        max_items: Maximum number of knowledge items to return
    
    Returns:
        List of relevant knowledge items with content and sources
    """
    global _knowledge_base
    
    # Ensure knowledge base is initialized
    if not _knowledge_base.loaded:
        logger.warning("Knowledge base not initialized, attempting initialization...")
        await initialize_knowledge_bases()
    
    return await _knowledge_base.get_agent_knowledge_enhanced(agent_name, query_context, max_items)

def get_knowledge_status() -> Dict:
    """
    Get the current status of the knowledge base system
    
    Returns:
        Dictionary with status information for debugging and monitoring
    """
    global _knowledge_base
    
    try:
        # Count local knowledge items
        local_counts = {}
        total_local = 0
        for agent, items in AGENT_KNOWLEDGE_BASE.items():
            count = len(items)
            local_counts[agent] = count
            total_local += count
        
        status = {
            "loaded": _knowledge_base.loaded,
            "supabase_available": _knowledge_base.supabase_available,
            "local_knowledge": {
                "total_documents": total_local,
                "agents": local_counts
            },
            "knowledge_directory": str(_knowledge_base.knowledge_dir),
            "directory_exists": _knowledge_base.knowledge_dir.exists()
        }
        
        # Add Supabase status if available
        if _knowledge_base.supabase_available and _knowledge_base.supabase_manager:
            try:
                # Note: This would need to be async in a real scenario
                status["supabase_status"] = "available"
            except Exception as e:
                status["supabase_status"] = f"error: {e}"
        else:
            status["supabase_status"] = "unavailable"
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting knowledge status: {e}")
        return {"status": "error", "error": str(e)} 
