"""
Automated Knowledge Base Loader
Downloads and processes curated PDFs for each philosophical agent
"""

import os
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from pdf_knowledge_loader import (
    load_moderation_guide,
    load_socratic_dialogue, 
    load_synthesis_guide,
    load_mindfulness_text
)

logger = logging.getLogger(__name__)

# Curated knowledge sources for each agent
KNOWLEDGE_SOURCES = {
    "solon": [
        {
            "url": "https://www.nyc.gov/assets/manhattancb3/downloads/resources/cec/guide_parliamentary_procedure.pdf",
            "filename": "nyc_parliamentary_procedure.pdf",
            "description": "NYC Guide to Parliamentary Procedure"
        },
        {
            "url": "https://www.circlek.org/wp-content/uploads/sites/9/2021/08/PARLIAMENTARY-PROCEDURE-101.pdf",
            "filename": "parliamentary_procedure_101.pdf", 
            "description": "Parliamentary Procedure 101 Guide"
        },
        {
            "url": "https://animationguild.org/wp-content/uploads/2022/10/Parliamentary-Procedure-Cheat-Sheet.pdf",
            "filename": "parliamentary_cheat_sheet.pdf",
            "description": "Parliamentary Procedure Quick Reference"
        }
    ],
    
    "socrates": [
        {
            "url": "http://www.criticalthinking.org/TGS_files/SocraticQuestioning2006.pdf",
            "filename": "socratic_questioning_guide.pdf",
            "description": "The Art of Socratic Questioning - Foundation for Critical Thinking"
        }
    ],
    
    "hermes": [
        {
            "url": "https://thesystemsthinker.com/wp-content/uploads/2016/03/Systems-Thinking-Tools-TRST01E.pdf",
            "filename": "systems_thinking_tools.pdf",
            "description": "Systems Thinking Tools: A User's Guide"
        },
        {
            "url": "https://people.sabanciuniv.edu/atilgan/CEM-Spring17/Books/6.Anderson-Johnson_SystemsThinkingBasics.pdf",
            "filename": "systems_thinking_basics.pdf",
            "description": "Systems Thinking Basics: From Concepts to Causal Loops"
        }
    ],
    
    "buddha": [
        {
            "url": "https://www.upaya.org/uploads/pdfs/KramaraeMediationResources.pdf",
            "filename": "buddhist_mediation_resources.pdf",
            "description": "Transform Conflict: Mediation Resources for Buddhist Chaplains"
        },
        {
            "url": "https://konfliktloesning.dk/wp-content/uploads/2017/04/Bog_Meeting_Conflicts_Mindfully_2001.pdf",
            "filename": "meeting_conflicts_mindfully.pdf",
            "description": "Meeting Conflicts Mindfully"
        }
    ]
}

class AutoKnowledgeLoader:
    """Automatically downloads and loads knowledge sources for agents"""
    
    def __init__(self, download_dir: str = "./knowledge_documents"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Create agent subdirectories
        for agent in KNOWLEDGE_SOURCES.keys():
            (self.download_dir / agent).mkdir(exist_ok=True)
    
    async def download_pdf(self, url: str, filepath: Path) -> bool:
        """Download a PDF from URL to filepath"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        filepath.write_bytes(content)
                        logger.info(f"Downloaded: {filepath.name}")
                        return True
                    else:
                        logger.error(f"Failed to download {url}: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return False
    
    async def load_agent_knowledge(self, agent_name: str) -> int:
        """Download and load knowledge for a specific agent"""
        if agent_name not in KNOWLEDGE_SOURCES:
            logger.error(f"No knowledge sources defined for agent: {agent_name}")
            return 0
        
        agent_dir = self.download_dir / agent_name
        sources = KNOWLEDGE_SOURCES[agent_name]
        loaded_count = 0
        
        logger.info(f"Loading knowledge for {agent_name}...")
        
        for source in sources:
            filepath = agent_dir / source["filename"]
            
            # Download if not already exists
            if not filepath.exists():
                success = await self.download_pdf(source["url"], filepath)
                if not success:
                    continue
            
            # Load into agent's knowledge base
            try:
                if agent_name == "solon":
                    success = await load_moderation_guide(str(filepath), source["description"])
                elif agent_name == "socrates":
                    success = await load_socratic_dialogue(str(filepath), source["description"])
                elif agent_name == "hermes":
                    success = await load_synthesis_guide(str(filepath), source["description"])
                elif agent_name == "buddha":
                    success = await load_mindfulness_text(str(filepath), source["description"])
                
                if success:
                    loaded_count += 1
                    logger.info(f"Loaded: {source['description']}")
                
            except Exception as e:
                logger.error(f"Failed to load {source['filename']}: {e}")
        
        logger.info(f"Loaded {loaded_count}/{len(sources)} knowledge sources for {agent_name}")
        return loaded_count
    
    async def load_all_knowledge(self) -> Dict[str, int]:
        """Load knowledge for all agents"""
        results = {}
        
        for agent_name in KNOWLEDGE_SOURCES.keys():
            results[agent_name] = await self.load_agent_knowledge(agent_name)
        
        total_loaded = sum(results.values())
        total_sources = sum(len(sources) for sources in KNOWLEDGE_SOURCES.values())
        
        logger.info(f"Knowledge loading complete: {total_loaded}/{total_sources} total sources loaded")
        
        return results

# Main execution functions
async def setup_all_knowledge():
    """Main function to set up all agent knowledge bases"""
    loader = AutoKnowledgeLoader()
    
    print("🧠 Setting up AI Agent Knowledge Bases...")
    print("=" * 50)
    
    # Load automatically downloadable sources
    results = await loader.load_all_knowledge()
    
    # Print results
    for agent, count in results.items():
        print(f"✅ {agent.title()}: {count} sources loaded")
    
    print("\n🎉 Knowledge base setup complete!")
    return results

async def setup_single_agent(agent_name: str):
    """Set up knowledge base for a single agent"""
    loader = AutoKnowledgeLoader()
    count = await loader.load_agent_knowledge(agent_name)
    print(f"✅ {agent_name.title()}: {count} knowledge sources loaded")
    return count

if __name__ == "__main__":
    # Example usage
    asyncio.run(setup_all_knowledge()) 