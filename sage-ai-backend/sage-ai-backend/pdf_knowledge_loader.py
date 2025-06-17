"""
PDF Knowledge Loader for AI Debate Agents
Processes PDFs and adds content to agent-specific knowledge bases
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import PyPDF2
    import fitz  # PyMuPDF
    PDF_PROCESSING_AVAILABLE = True
except ImportError:
    PDF_PROCESSING_AVAILABLE = False
    logging.warning("PDF processing libraries not available. Install PyPDF2 and PyMuPDF.")

from knowledge_base_manager import knowledge_manager

logger = logging.getLogger(__name__)

class PDFKnowledgeLoader:
    """Loads PDF content into agent knowledge bases"""
    
    def __init__(self):
        self.chunk_size = 1000  # Characters per chunk
        self.overlap_size = 200  # Character overlap between chunks
    
    async def load_pdf_for_agent(
        self, 
        agent_name: str, 
        pdf_path: str, 
        category: str = "document",
        source_description: str = None
    ) -> bool:
        """Load a PDF file into a specific agent's knowledge base"""
        
        if not PDF_PROCESSING_AVAILABLE:
            logger.error("PDF processing libraries not available")
            return False
            
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return False
        
        try:
            # Extract text from PDF
            text_content = self._extract_pdf_text(pdf_path)
            
            if not text_content:
                logger.warning(f"No text extracted from {pdf_path}")
                return False
            
            # Split into chunks for better retrieval
            chunks = self._split_text_into_chunks(text_content)
            
            # Prepare metadata
            source_name = source_description or Path(pdf_path).stem
            
            # Add each chunk to the agent's knowledge base
            for i, chunk in enumerate(chunks):
                metadata = {
                    "source": source_name,
                    "source_file": pdf_path,
                    "type": "pdf_content",
                    "category": category,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
                
                await knowledge_manager.add_knowledge_to_agent(
                    agent_name=agent_name,
                    content=chunk,
                    metadata=metadata
                )
            
            logger.info(f"Successfully loaded {len(chunks)} chunks from {pdf_path} to {agent_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load PDF {pdf_path} for {agent_name}: {e}")
            return False
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF using multiple methods"""
        text = ""
        
        # Try PyMuPDF first (better for complex layouts)
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text()
            doc.close()
            
            if text.strip():
                return text
                
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
        
        # Fallback to PyPDF2
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text()
                    
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
        
        return text
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks for better retrieval"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                sentence_end = max(
                    text.rfind('.', start, end),
                    text.rfind('!', start, end),
                    text.rfind('?', start, end)
                )
                
                if sentence_end > start + self.chunk_size // 2:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.overlap_size
            
        return chunks

# Convenience functions for specific agent types

async def load_moderation_guide(pdf_path: str, description: str = None):
    """Load a moderation guide for Solon"""
    loader = PDFKnowledgeLoader()
    return await loader.load_pdf_for_agent(
        agent_name="solon",
        pdf_path=pdf_path,
        category="moderation_guide",
        source_description=description
    )

async def load_logic_textbook(pdf_path: str, description: str = None):
    """Load a logic/reasoning textbook for Aristotle"""
    loader = PDFKnowledgeLoader()
    return await loader.load_pdf_for_agent(
        agent_name="aristotle",
        pdf_path=pdf_path,
        category="logic_textbook",
        source_description=description
    )

async def load_socratic_dialogue(pdf_path: str, description: str = None):
    """Load Socratic dialogue examples for Socrates"""
    loader = PDFKnowledgeLoader()
    return await loader.load_pdf_for_agent(
        agent_name="socrates",
        pdf_path=pdf_path,
        category="dialogue_examples",
        source_description=description
    )

async def load_synthesis_guide(pdf_path: str, description: str = None):
    """Load synthesis/communication guide for Hermes"""
    loader = PDFKnowledgeLoader()
    return await loader.load_pdf_for_agent(
        agent_name="hermes",
        pdf_path=pdf_path,
        category="synthesis_guide",
        source_description=description
    )

async def load_mindfulness_text(pdf_path: str, description: str = None):
    """Load mindfulness/compassion text for Buddha"""
    loader = PDFKnowledgeLoader()
    return await loader.load_pdf_for_agent(
        agent_name="buddha",
        pdf_path=pdf_path,
        category="mindfulness_text",
        source_description=description
    )

# Batch loading function
async def load_agent_library(agent_name: str, pdf_directory: str):
    """Load all PDFs in a directory for a specific agent"""
    if not os.path.exists(pdf_directory):
        logger.error(f"Directory not found: {pdf_directory}")
        return
    
    loader = PDFKnowledgeLoader()
    pdf_files = list(Path(pdf_directory).glob("*.pdf"))
    
    successful_loads = 0
    for pdf_file in pdf_files:
        success = await loader.load_pdf_for_agent(
            agent_name=agent_name,
            pdf_path=str(pdf_file),
            category="library_document",
            source_description=pdf_file.stem
        )
        if success:
            successful_loads += 1
    
    logger.info(f"Loaded {successful_loads}/{len(pdf_files)} PDFs for {agent_name}")
    return successful_loads 