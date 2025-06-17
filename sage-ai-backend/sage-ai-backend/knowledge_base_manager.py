"""
Knowledge Base Manager for AI Debate Agents
Manages loading and retrieval of specialized knowledge for each philosophical agent
"""

import os
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import PyPDF2
from io import BytesIO

logger = logging.getLogger(__name__)

# Global knowledge storage
AGENT_KNOWLEDGE_BASE: Dict[str, List[Dict]] = {
    "solon": [],      # Parliamentary procedure and moderation
    "aristotle": [],  # Logic, analysis, and fact-checking  
    "socrates": [],   # Socratic questioning methods
    "hermes": [],     # Systems thinking and synthesis
    "buddha": []      # Conflict resolution and mindfulness
}

class KnowledgeBase:
    """Manages knowledge base operations for AI agents"""
    
    def __init__(self, knowledge_dir: str = "./knowledge_documents"):
        self.knowledge_dir = Path(knowledge_dir)
        self.loaded = False
        
    async def initialize_all_knowledge_bases(self) -> bool:
        """Initialize knowledge bases for all agents"""
        try:
            logger.info("🧠 Initializing AI agent knowledge bases...")
            
            if not self.knowledge_dir.exists():
                logger.warning(f"Knowledge directory not found: {self.knowledge_dir}")
                return False
            
            success_count = 0
            agent_dirs = ["solon", "socrates", "hermes", "buddha"]  # aristotle uses online research, not local PDFs
            
            for agent_name in agent_dirs:
                agent_dir = self.knowledge_dir / agent_name
                if agent_dir.exists():
                    count = await self._load_agent_knowledge(agent_name, agent_dir)
                    if count > 0:
                        success_count += 1
                        logger.info(f"✅ {agent_name.title()}: {count} documents loaded")
                    else:
                        logger.warning(f"⚠️ {agent_name.title()}: No documents found")
                else:
                    logger.warning(f"⚠️ {agent_name.title()}: Directory not found")
            
            self.loaded = success_count > 0
            logger.info(f"🎉 Knowledge base initialization complete: {success_count}/{len(agent_dirs)} agents ready")
            
            return self.loaded
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize knowledge bases: {e}")
            return False
    
    async def _load_agent_knowledge(self, agent_name: str, agent_dir: Path) -> int:
        """Load all PDF documents for a specific agent"""
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

# Global knowledge base instance
_knowledge_base = KnowledgeBase()

async def initialize_knowledge_bases() -> bool:
    """Initialize knowledge bases for all agents (called by AI agents system)"""
    global _knowledge_base
    return await _knowledge_base.initialize_all_knowledge_bases()

async def get_agent_knowledge(agent_name: str, query_context: str, max_items: int = 3) -> List[Dict]:
    """
    Retrieve relevant knowledge for an agent based on query context
    
    Args:
        agent_name: Name of the agent (solon, aristotle, socrates, hermes, buddha)
        query_context: Context or topic to search for relevant knowledge
        max_items: Maximum number of knowledge items to return
    
    Returns:
        List of relevant knowledge items with content and sources
    """
    try:
        if agent_name not in AGENT_KNOWLEDGE_BASE:
            logger.warning(f"Unknown agent: {agent_name}")
            return []
        
        agent_knowledge = AGENT_KNOWLEDGE_BASE[agent_name]
        
        if not agent_knowledge:
            logger.warning(f"No knowledge loaded for agent: {agent_name}")
            return []
        
        # Simple relevance scoring based on keyword matching
        query_keywords = query_context.lower().split()
        scored_items = []
        
        for item in agent_knowledge:
            content_lower = item['content'].lower()
            summary_lower = item['summary'].lower()
            
            # Calculate relevance score
            score = 0
            for keyword in query_keywords:
                if len(keyword) > 2:  # Skip very short words
                    # Weight summary matches higher
                    score += summary_lower.count(keyword) * 3
                    score += content_lower.count(keyword)
            
            if score > 0:
                scored_items.append((score, item))
        
        # Sort by relevance and return top items
        scored_items.sort(reverse=True, key=lambda x: x[0])
        
        relevant_items = []
        for score, item in scored_items[:max_items]:
            relevant_items.append({
                "source": item["source"],
                "summary": item["summary"],
                "content": item["content"][:1000] + "..." if len(item["content"]) > 1000 else item["content"],
                "relevance_score": score
            })
        
        logger.info(f"📚 Retrieved {len(relevant_items)} knowledge items for {agent_name}")
        return relevant_items
        
    except Exception as e:
        logger.error(f"Failed to retrieve knowledge for {agent_name}: {e}")
        return []

def get_knowledge_status() -> Dict:
    """Get status of loaded knowledge bases"""
    status = {
        "loaded": _knowledge_base.loaded,
        "agents": {}
    }
    
    for agent_name, knowledge_list in AGENT_KNOWLEDGE_BASE.items():
        status["agents"][agent_name] = {
            "document_count": len(knowledge_list),
            "sources": [item["source"] for item in knowledge_list] if knowledge_list else []
        }
    
    return status 
