"""
Perplexity API Research Integration for Aristotle
Provides real-time research and fact-checking capabilities
"""

import os
import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class ResearchResult:
    """Represents a research result from Perplexity"""
    query: str
    answer: str
    sources: List[str]
    citations: List[Dict[str, str]]
    timestamp: datetime
    confidence: str

class PerplexityResearcher:
    """Perplexity API integration for real-time research"""
    
    def __init__(self):
        # Force reload .env file to ensure we get the latest keys
        from dotenv import load_dotenv
        load_dotenv(override=True)  # Override any existing env vars
        
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.base_url = "https://api.perplexity.ai/chat/completions"
        self.model = "sonar"  # Current Perplexity model for real-time research
        
        if not self.api_key or self.api_key.startswith("your-"):
            logger.warning("PERPLEXITY_API_KEY not found or using placeholder. Research features will be disabled.")
        else:
            logger.info(f"✅ Perplexity API key loaded: {self.api_key[:10]}...")
    
    async def research_claim(self, claim: str, context: str = "") -> Optional[ResearchResult]:
        """Research a specific claim or statement"""
        if not self.api_key:
            logger.warning("Perplexity API key not available")
            return None
            
        research_prompt = f"""
        As Aristotle, the philosopher of logic and empirical observation, research this claim:
        
        CLAIM: {claim}
        CONTEXT: {context}
        
        Please:
        1. Verify the factual accuracy of this claim
        2. Provide current evidence and data
        3. Identify any logical fallacies or weak reasoning
        4. Cite specific, credible sources
        5. Give a clear assessment of the claim's validity
        
        Be systematic and evidence-based in your analysis.
        """
        
        return await self._make_research_request(research_prompt, f"fact-check: {claim}")
    
    async def research_topic(self, topic: str, focus: str = "current evidence") -> Optional[ResearchResult]:
        """Research a general topic for background information"""
        if not self.api_key:
            return None
            
        research_prompt = f"""
        As Aristotle, research this topic with focus on {focus}:
        
        TOPIC: {topic}
        
        Please provide:
        1. Current scientific consensus or expert opinion
        2. Recent studies or authoritative sources
        3. Key facts and statistics
        4. Different perspectives if they exist
        5. Methodologically sound evidence
        
        Focus on empirical evidence and logical analysis.
        """
        
        return await self._make_research_request(research_prompt, f"topic research: {topic}")
    
    async def verify_statistics(self, statistic: str, context: str = "") -> Optional[ResearchResult]:
        """Verify specific statistics or data points"""
        if not self.api_key:
            return None
            
        research_prompt = f"""
        As Aristotle, verify this statistic or data point:
        
        STATISTIC: {statistic}
        CONTEXT: {context}
        
        Please:
        1. Find the original source of this statistic
        2. Verify its accuracy and recency
        3. Check the methodology used to derive it
        4. Identify any limitations or caveats
        5. Provide more recent data if available
        
        Be rigorous in evaluating the quality of data sources.
        """
        
        return await self._make_research_request(research_prompt, f"stat verification: {statistic}")
    
    async def logical_analysis(self, argument: str) -> Optional[ResearchResult]:
        """Analyze the logical structure of an argument"""
        if not self.api_key:
            return None
            
        research_prompt = f"""
        As Aristotle, analyze the logical structure of this argument:
        
        ARGUMENT: {argument}
        
        Please:
        1. Identify the premises and conclusion
        2. Check for logical validity
        3. Identify any logical fallacies
        4. Assess the strength of evidence
        5. Find counter-evidence if it exists
        6. Provide a systematic logical evaluation
        
        Use formal logic principles and empirical verification.
        """
        
        return await self._make_research_request(research_prompt, f"logical analysis: {argument[:50]}...")
    
    async def _make_research_request(self, prompt: str, query: str) -> Optional[ResearchResult]:
        """Make a request to Perplexity API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are Aristotle, the ancient Greek philosopher known for systematic thinking, empirical observation, and logical analysis. Provide thorough, evidence-based research with proper citations."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.1  # Low temperature for factual accuracy
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_research_response(data, query)
                    else:
                        logger.error(f"Perplexity API error: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Research request failed: {e}")
            return None
    
    def _parse_research_response(self, response_data: Dict, query: str) -> ResearchResult:
        """Parse Perplexity API response into ResearchResult"""
        try:
            content = response_data["choices"][0]["message"]["content"]
            
            # Extract citations if available - Perplexity returns direct URLs
            citations = []
            sources = []
            
            if "citations" in response_data:
                # Perplexity citations are direct URLs, not objects
                sources = response_data["citations"]
                citations = [{"url": url, "title": "", "source": url} for url in sources]
            
            return ResearchResult(
                query=query,
                answer=content,
                sources=sources,
                citations=citations,
                timestamp=datetime.now(),
                confidence="high"  # Perplexity provides real-time sourced data
            )
            
        except Exception as e:
            logger.error(f"Failed to parse research response: {e}")
            return ResearchResult(
                query=query,
                answer="Research failed",
                sources=[],
                citations=[],
                timestamp=datetime.now(),
                confidence="none"
            )

class AristotleResearchAgent:
    """Enhanced Aristotle with Perplexity research capabilities"""
    
    def __init__(self):
        self.researcher = PerplexityResearcher()
        self.research_cache: Dict[str, ResearchResult] = {}
        self.max_cache_size = 100
        
    async def analyze_with_research(self, statement: str, context: str = "") -> Dict[str, Any]:
        """Analyze a statement using both knowledge base and real-time research"""
        
        # Check cache first
        cache_key = f"{statement[:50]}..."
        if cache_key in self.research_cache:
            cached_result = self.research_cache[cache_key]
            # Use cached result if less than 1 hour old
            if (datetime.now() - cached_result.timestamp).seconds < 3600:
                return self._format_analysis_result(cached_result, "cached")
        
        # Determine research type based on statement content
        if any(keyword in statement.lower() for keyword in ["study shows", "research indicates", "statistics", "data", "%", "according to"]):
            research_result = await self.researcher.research_claim(statement, context)
        elif any(keyword in statement.lower() for keyword in ["because", "therefore", "proves", "leads to", "causes"]):
            research_result = await self.researcher.logical_analysis(statement)
        else:
            # Extract key topic for general research
            topic = self._extract_main_topic(statement)
            research_result = await self.researcher.research_topic(topic, "current evidence")
        
        if research_result:
            # Cache the result
            self.research_cache[cache_key] = research_result
            
            # Limit cache size
            if len(self.research_cache) > self.max_cache_size:
                oldest_key = min(self.research_cache.keys(), key=lambda k: self.research_cache[k].timestamp)
                del self.research_cache[oldest_key]
            
            return self._format_analysis_result(research_result, "live")
        
        return {"status": "no_research", "analysis": "Research unavailable"}
    
    def _extract_main_topic(self, statement: str) -> str:
        """Extract the main topic from a statement for research"""
        # Simple keyword extraction (could be enhanced with NLP)
        words = statement.split()
        # Remove common words and focus on content words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should"}
        content_words = [word.strip(".,!?") for word in words if word.lower() not in stop_words and len(word) > 3]
        
        # Return first few content words as topic
        return " ".join(content_words[:3])
    
    def _format_analysis_result(self, result: ResearchResult, source_type: str) -> Dict[str, Any]:
        """Format research result for agent consumption"""
        return {
            "status": "success",
            "source_type": source_type,
            "analysis": result.answer,
            "sources": result.sources,
            "citations": result.citations,
            "confidence": result.confidence,
            "timestamp": result.timestamp.isoformat(),
            "query": result.query
        }

# Global instance for Aristotle
aristotle_researcher = AristotleResearchAgent()

async def get_aristotle_research(statement: str, context: str = "") -> Dict[str, Any]:
    """Main function to get research-enhanced analysis from Aristotle"""
    return await aristotle_researcher.analyze_with_research(statement, context)

async def research_with_perplexity(query: str, research_type: str = "general") -> Optional[Dict[str, Any]]:
    """Research a query using Perplexity API - direct interface function"""
    if not aristotle_researcher.researcher.api_key:
        return {"error": "Perplexity API key not available", "answer": "Research unavailable"}
    
    try:
        if research_type == "fact-check":
            result = await aristotle_researcher.researcher.research_claim(query)
        elif research_type == "statistics":
            result = await aristotle_researcher.researcher.verify_statistics(query)
        elif research_type == "logic":
            result = await aristotle_researcher.researcher.logical_analysis(query)
        else:
            result = await aristotle_researcher.researcher.research_topic(query)
        
        if result:
            return {
                "answer": result.answer,
                "sources": result.sources,
                "citations": result.citations,
                "confidence": result.confidence,
                "timestamp": result.timestamp.isoformat()
            }
        else:
            return {"error": "Research failed", "answer": "No results available"}
            
    except Exception as e:
        return {"error": f"Research error: {str(e)}", "answer": "Research unavailable"} 