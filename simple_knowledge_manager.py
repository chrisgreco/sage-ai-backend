"""
Simple Knowledge Manager - File-based storage for agent knowledge documents
Replaces the complex Supabase + chunking + vector search architecture
"""
import os
import re
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class SimpleKnowledgeManager:
    """
    Simple file-based knowledge manager for AI agents.
    Loads documents from disk and provides keyword-based search.
    """
    
    def __init__(self, agent_type: str):
        """
        Initialize knowledge manager for a specific agent type.
        
        Args:
            agent_type: The agent type (e.g., 'aristotle', 'socrates')
        """
        self.agent_type = agent_type
        self.knowledge_dir = Path(f"knowledge_documents/{agent_type}")
        self.documents = {}
        self.loaded = False
        
        # Ensure knowledge directory exists
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        
    def load_documents(self) -> bool:
        """
        Load all text documents from the agent's knowledge directory.
        
        Returns:
            bool: True if documents were loaded successfully
        """
        try:
            self.documents = {}
            
            if not self.knowledge_dir.exists():
                logger.warning(f"Knowledge directory not found: {self.knowledge_dir}")
                return False
                
            # Load all .txt files in the knowledge directory
            txt_files = list(self.knowledge_dir.glob("*.txt"))
            
            if not txt_files:
                logger.warning(f"No .txt files found in {self.knowledge_dir}")
                return False
                
            for file_path in txt_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            # Use filename (without extension) as document name
                            doc_name = file_path.stem
                            self.documents[doc_name] = {
                                'content': content,
                                'path': str(file_path),
                                'title': self._extract_title(content)
                            }
                            logger.debug(f"Loaded document: {doc_name} ({len(content)} chars)")
                        else:
                            logger.warning(f"Empty document: {file_path}")
                            
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")
                    continue
                    
            self.loaded = len(self.documents) > 0
            
            if self.loaded:
                logger.info(f"Loaded {len(self.documents)} documents for {self.agent_type}")
            else:
                logger.warning(f"No documents loaded for {self.agent_type}")
                
            return self.loaded
            
        except Exception as e:
            logger.error(f"Error loading documents: {e}")
            return False
            
    def _extract_title(self, content: str) -> str:
        """
        Extract title from document content (first heading or filename).
        
        Args:
            content: Document content
            
        Returns:
            str: Document title
        """
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                return line[2:].strip()
        return "Untitled Document"
        
    def search_knowledge(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Search knowledge documents using simple keyword matching.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of relevant document sections with relevance scores
        """
        if not self.loaded:
            if not self.load_documents():
                return []
                
        if not query or not self.documents:
            return []
            
        try:
            # Normalize query for search
            query_words = self._extract_keywords(query.lower())
            
            if not query_words:
                return []
                
            results = []
            
            for doc_name, doc_data in self.documents.items():
                content = doc_data['content']
                title = doc_data['title']
                
                # Calculate relevance score
                score = self._calculate_relevance(content.lower(), query_words)
                
                if score > 0:
                    # Find best matching section
                    best_section = self._find_best_section(content, query_words)
                    
                    results.append({
                        'document': doc_name,
                        'title': title,
                        'content': best_section,
                        'relevance_score': score,
                        'path': doc_data['path']
                    })
                    
            # Sort by relevance score (highest first)
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            # Return top results
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Error searching knowledge: {e}")
            return []
            
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text.
        
        Args:
            text: Input text
            
        Returns:
            List of keywords
        """
        # Remove punctuation and split into words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
            'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
            'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 
            'did', 'man', 'men', 'say', 'she', 'too', 'use', 'way', 'why', 'with',
            'this', 'that', 'they', 'have', 'from', 'would', 'been', 'what', 'when',
            'where', 'will', 'more', 'some', 'time', 'very', 'into', 'just', 'know',
            'take', 'than', 'them', 'well', 'were'
        }
        
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        return keywords
        
    def _calculate_relevance(self, content: str, query_words: List[str]) -> float:
        """
        Calculate relevance score between content and query words.
        
        Args:
            content: Document content (lowercase)
            query_words: List of query keywords
            
        Returns:
            float: Relevance score (0.0 to 1.0)
        """
        if not query_words:
            return 0.0
            
        content_words = self._extract_keywords(content)
        content_word_count = len(content_words)
        
        if content_word_count == 0:
            return 0.0
            
        # Count matches
        matches = 0
        for query_word in query_words:
            # Exact matches
            exact_matches = content.count(query_word)
            matches += exact_matches
            
            # Partial matches (query word contained in content words)
            partial_matches = sum(1 for word in content_words if query_word in word)
            matches += partial_matches * 0.5
            
        # Calculate score as ratio of matches to query length, normalized by content length
        score = (matches / len(query_words)) * min(1.0, 100.0 / content_word_count)
        return min(score, 1.0)
        
    def _find_best_section(self, content: str, query_words: List[str], section_length: int = 800) -> str:
        """
        Find the most relevant section of the document.
        
        Args:
            content: Full document content
            query_words: List of query keywords
            section_length: Maximum length of returned section
            
        Returns:
            str: Most relevant section of the document
        """
        if len(content) <= section_length:
            return content
            
        # Split content into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if not paragraphs:
            return content[:section_length] + "..."
            
        # Score each paragraph
        paragraph_scores = []
        for i, paragraph in enumerate(paragraphs):
            score = self._calculate_relevance(paragraph.lower(), query_words)
            paragraph_scores.append((score, i, paragraph))
            
        # Sort by score
        paragraph_scores.sort(reverse=True)
        
        # Build best section starting with highest-scoring paragraph
        best_section = paragraph_scores[0][2]
        current_length = len(best_section)
        
        # Add adjacent paragraphs if they fit
        best_index = paragraph_scores[0][1]
        
        # Try to add following paragraphs
        for i in range(best_index + 1, len(paragraphs)):
            next_para = paragraphs[i]
            if current_length + len(next_para) + 2 <= section_length:
                best_section += "\n\n" + next_para
                current_length += len(next_para) + 2
            else:
                break
                
        # Try to add preceding paragraphs
        for i in range(best_index - 1, -1, -1):
            prev_para = paragraphs[i]
            if current_length + len(prev_para) + 2 <= section_length:
                best_section = prev_para + "\n\n" + best_section
                current_length += len(prev_para) + 2
            else:
                break
                
        # Truncate if still too long
        if len(best_section) > section_length:
            best_section = best_section[:section_length-3] + "..."
            
        return best_section
        
    def get_all_documents(self) -> List[Dict]:
        """
        Get information about all loaded documents.
        
        Returns:
            List of document information
        """
        if not self.loaded:
            self.load_documents()
            
        return [
            {
                'name': name,
                'title': data['title'],
                'path': data['path'],
                'length': len(data['content'])
            }
            for name, data in self.documents.items()
        ]
        
    def get_document_by_name(self, name: str) -> Optional[str]:
        """
        Get full content of a specific document by name.
        
        Args:
            name: Document name (filename without extension)
            
        Returns:
            Document content or None if not found
        """
        if not self.loaded:
            self.load_documents()
            
        return self.documents.get(name, {}).get('content')
        
    def is_ready(self) -> bool:
        """
        Check if the knowledge manager is ready to use.
        
        Returns:
            bool: True if documents are loaded and ready
        """
        return self.loaded and len(self.documents) > 0
        
    def get_status(self) -> Dict:
        """
        Get status information about the knowledge manager.
        
        Returns:
            Dict with status information
        """
        return {
            'agent_type': self.agent_type,
            'knowledge_dir': str(self.knowledge_dir),
            'loaded': self.loaded,
            'document_count': len(self.documents),
            'documents': list(self.documents.keys()) if self.loaded else []
        }

# Convenience function for easy usage
def create_knowledge_manager(agent_type: str) -> SimpleKnowledgeManager:
    """
    Create and initialize a knowledge manager for an agent.
    
    Args:
        agent_type: The agent type (e.g., 'aristotle', 'socrates')
        
    Returns:
        Initialized SimpleKnowledgeManager
    """
    manager = SimpleKnowledgeManager(agent_type)
    manager.load_documents()
    return manager

# Test function
def test_knowledge_manager():
    """Test function to verify the knowledge manager works correctly."""
    print("Testing Simple Knowledge Manager...")
    
    # Test Aristotle's knowledge
    aristotle_km = create_knowledge_manager('aristotle')
    print(f"Aristotle status: {aristotle_km.get_status()}")
    
    if aristotle_km.is_ready():
        results = aristotle_km.search_knowledge("conflict resolution moderation", max_results=2)
        print(f"Search results for 'conflict resolution moderation': {len(results)} found")
        for result in results:
            print(f"- {result['title']} (score: {result['relevance_score']:.2f})")
            print(f"  Preview: {result['content'][:200]}...")
    
    # Test Socrates' knowledge
    socrates_km = create_knowledge_manager('socrates')
    print(f"\nSocrates status: {socrates_km.get_status()}")
    
    if socrates_km.is_ready():
        results = socrates_km.search_knowledge("questioning assumptions", max_results=2)
        print(f"Search results for 'questioning assumptions': {len(results)} found")
        for result in results:
            print(f"- {result['title']} (score: {result['relevance_score']:.2f})")
            print(f"  Preview: {result['content'][:200]}...")

if __name__ == "__main__":
    test_knowledge_manager() 