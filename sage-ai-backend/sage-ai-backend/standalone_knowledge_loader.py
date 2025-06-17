"""
Standalone Knowledge Base Loader
Downloads curated PDFs for each philosophical agent without dependencies
"""

import os
import asyncio
import aiohttp
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Curated knowledge sources for each agent based on research
KNOWLEDGE_SOURCES = {
    "solon": [
        {
            "url": "https://www.nyc.gov/assets/manhattancb3/downloads/resources/cec/guide_parliamentary_procedure.pdf",
            "filename": "nyc_parliamentary_procedure.pdf",
            "description": "NYC Guide to Parliamentary Procedure - Comprehensive moderation guide"
        },
        {
            "url": "https://www.circlek.org/wp-content/uploads/sites/9/2021/08/PARLIAMENTARY-PROCEDURE-101.pdf",
            "filename": "parliamentary_procedure_101.pdf", 
            "description": "Parliamentary Procedure 101 - Practical meeting facilitation"
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
            "description": "Systems Thinking Tools: A User's Guide - 87 pages of frameworks"
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
            "description": "Meeting Conflicts Mindfully - Tibetan Centre for Conflict Resolution"
        }
    ]
}

# Additional high-value sources that may require manual download
ADDITIONAL_SOURCES = {
    "socrates": [
        {
            "title": "The Socratic Temperament",
            "url": "http://www.socraticmethod.net/essays/ST_pdf_versions.html",
            "instructions": "Visit website and download PDF version"
        }
    ],
    "buddha": [
        {
            "title": "Buddhist Path to Transforming Conflict",
            "url": "https://www.mangrovec.com/files/the-buddhist-path-to-transforming-conflict.pdf",
            "instructions": "Direct PDF download"
        }
    ]
}

class StandaloneKnowledgeLoader:
    """Downloads and organizes knowledge sources for agents"""
    
    def __init__(self, download_dir: str = "./knowledge_documents"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Create agent subdirectories
        for agent in KNOWLEDGE_SOURCES.keys():
            (self.download_dir / agent).mkdir(exist_ok=True)
    
    async def download_pdf(self, url: str, filepath: Path) -> bool:
        """Download a PDF from URL to filepath"""
        try:
            # Add headers to mimic browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.read()
                        filepath.write_bytes(content)
                        file_size = len(content) / 1024 / 1024  # MB
                        logger.info(f"✅ Downloaded: {filepath.name} ({file_size:.1f} MB)")
                        return True
                    else:
                        logger.error(f"❌ Failed to download {url}: HTTP {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Error downloading {url}: {e}")
            return False
    
    async def download_agent_knowledge(self, agent_name: str) -> int:
        """Download knowledge for a specific agent"""
        if agent_name not in KNOWLEDGE_SOURCES:
            logger.error(f"No knowledge sources defined for agent: {agent_name}")
            return 0
        
        agent_dir = self.download_dir / agent_name
        sources = KNOWLEDGE_SOURCES[agent_name]
        downloaded_count = 0
        
        print(f"\n🎭 {agent_name.upper()}: Downloading knowledge sources...")
        
        for source in sources:
            filepath = agent_dir / source["filename"]
            
            # Skip if already exists
            if filepath.exists():
                file_size = filepath.stat().st_size / 1024 / 1024  # MB
                print(f"   📁 Already exists: {source['filename']} ({file_size:.1f} MB)")
                downloaded_count += 1
                continue
            
            print(f"   📥 Downloading: {source['description']}")
            success = await self.download_pdf(source["url"], filepath)
            
            if success:
                downloaded_count += 1
            else:
                print(f"   ⚠️  Skipped: {source['filename']}")
        
        print(f"   ✅ {agent_name.title()}: {downloaded_count}/{len(sources)} sources ready")
        return downloaded_count
    
    async def download_all_knowledge(self) -> dict:
        """Download knowledge for all agents"""
        results = {}
        
        print("🧠 DOWNLOADING AI AGENT KNOWLEDGE BASES")
        print("=" * 50)
        
        for agent_name in KNOWLEDGE_SOURCES.keys():
            results[agent_name] = await self.download_agent_knowledge(agent_name)
        
        total_downloaded = sum(results.values())
        total_sources = sum(len(sources) for sources in KNOWLEDGE_SOURCES.values())
        
        print(f"\n🎉 DOWNLOAD COMPLETE: {total_downloaded}/{total_sources} sources ready")
        
        return results
    
    def print_file_summary(self):
        """Print summary of downloaded files"""
        print("\n📚 KNOWLEDGE BASE SUMMARY")
        print("=" * 50)
        
        total_size = 0
        total_files = 0
        
        for agent_name in KNOWLEDGE_SOURCES.keys():
            agent_dir = self.download_dir / agent_name
            if not agent_dir.exists():
                continue
                
            agent_files = list(agent_dir.glob("*.pdf"))
            agent_size = sum(f.stat().st_size for f in agent_files) / 1024 / 1024  # MB
            
            print(f"\n🎭 {agent_name.upper()}:")
            for pdf_file in agent_files:
                file_size = pdf_file.stat().st_size / 1024 / 1024  # MB
                print(f"   📄 {pdf_file.name} ({file_size:.1f} MB)")
            
            print(f"   📊 Subtotal: {len(agent_files)} files, {agent_size:.1f} MB")
            total_files += len(agent_files)
            total_size += agent_size
        
        print(f"\n🎯 TOTAL: {total_files} PDF files, {total_size:.1f} MB")
    
    def print_next_steps(self):
        """Print instructions for next steps"""
        print("\n🚀 NEXT STEPS")
        print("=" * 30)
        print("1. 📋 Review downloaded PDFs in ./knowledge_documents/")
        print("2. 🔧 Run the knowledge_base_manager.py to process PDFs into vector database")
        print("3. 🧪 Test agents with knowledge-based questions")
        print("4. 🎭 Start debates - agents now have specialized expertise!")
        
        # Print additional manual sources
        if ADDITIONAL_SOURCES:
            print("\n📖 OPTIONAL MANUAL ADDITIONS:")
            for agent, sources in ADDITIONAL_SOURCES.items():
                print(f"\n🎭 {agent.upper()}:")
                for source in sources:
                    print(f"   📚 {source['title']}")
                    print(f"   🔗 {source['url']}")
                    print(f"   💾 {source['instructions']}")

# Main execution functions
async def setup_all_knowledge():
    """Main function to download all knowledge sources"""
    loader = StandaloneKnowledgeLoader()
    
    # Download all PDFs
    results = await loader.download_all_knowledge()
    
    # Print summary
    loader.print_file_summary()
    loader.print_next_steps()
    
    return results

async def setup_single_agent(agent_name: str):
    """Download knowledge for a single agent"""
    loader = StandaloneKnowledgeLoader()
    count = await loader.download_agent_knowledge(agent_name)
    loader.print_file_summary()
    return count

if __name__ == "__main__":
    # Run the automatic setup
    asyncio.run(setup_all_knowledge()) 