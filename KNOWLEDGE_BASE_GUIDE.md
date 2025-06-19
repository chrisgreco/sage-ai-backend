# 🧠 AI Agent Knowledge Base System

## Overview

This system allows you to train each of the 5 philosophical AI debate agents with specialized knowledge from PDFs, documents, and custom content. Each agent maintains their own vector database collection for intelligent retrieval during debates.

## 🎯 What This Enables

### **Real-Time Knowledge Integration**
- Agents search their knowledge bases during conversations
- Relevant information is retrieved based on conversation context
- Each agent draws from their specialized domain expertise

### **PDF Training Capabilities**
- Upload PDFs to train specific agents
- Automatic text extraction and chunking
- Semantic search for relevant content retrieval

### **Agent Specialization**
Each agent has their own knowledge domain:

| Agent | Role | Best Knowledge Sources |
|-------|------|----------------------|
| **Solon** | Rule Enforcer | Parliamentary procedures, conflict resolution guides, moderation best practices |
| **Aristotle** | Fact-Checker | Scientific papers, logic textbooks, research methodologies, fact-checking standards |
| **Socrates** | Clarifier | Philosophical dialogues, questioning techniques, critical thinking frameworks |
| **Hermes** | Synthesizer | Systems thinking literature, communication theory, synthesis methodologies |
| **Buddha** | Peacekeeper | Mindfulness texts, compassionate communication, conflict de-escalation guides |

## 🚀 How to Use

### **1. Basic Setup**

Install required dependencies:
```bash
pip install chromadb PyPDF2 PyMuPDF
```

### **2. Loading PDFs for Specific Agents**

```python
from pdf_knowledge_loader import (
    load_moderation_guide,
    load_logic_textbook,
    load_socratic_dialogue,
    load_synthesis_guide,
    load_mindfulness_text
)

# Load a debate moderation guide for Solon
await load_moderation_guide(
    pdf_path="./documents/parliamentary_procedure.pdf",
    description="Parliamentary Procedure Manual"
)

# Load a logic textbook for Aristotle
await load_logic_textbook(
    pdf_path="./documents/formal_logic.pdf", 
    description="Formal Logic and Reasoning"
)

# Load Socratic dialogue examples for Socrates
await load_socratic_dialogue(
    pdf_path="./documents/platonic_dialogues.pdf",
    description="Plato's Dialogues Collection"
)
```

### **3. Batch Loading from Directories**

```python
from pdf_knowledge_loader import load_agent_library

# Load all PDFs in a directory for a specific agent
await load_agent_library("aristotle", "./aristotle_library/")
await load_agent_library("solon", "./moderation_guides/")
await load_agent_library("socrates", "./philosophy_texts/")
```

### **4. Adding Custom Knowledge Directly**

```python
from knowledge_base_manager import knowledge_manager

# Add custom knowledge to an agent
await knowledge_manager.add_knowledge_to_agent(
    agent_name="buddha",
    content="The Four Noble Truths: Life contains suffering, suffering has a cause, suffering can end, there is a path to end suffering.",
    metadata={
        "source": "Buddhist Fundamentals",
        "type": "principle",
        "category": "core_teaching"
    }
)
```

## 📁 Recommended Directory Structure

```
sage-ai-backend/
├── knowledge_documents/
│   ├── solon/
│   │   ├── parliamentary_procedure.pdf
│   │   ├── conflict_resolution_guide.pdf
│   │   └── debate_moderation_best_practices.pdf
│   ├── aristotle/
│   │   ├── formal_logic_textbook.pdf
│   │   ├── scientific_method_guide.pdf
│   │   └── fact_checking_standards.pdf
│   ├── socrates/
│   │   ├── platonic_dialogues.pdf
│   │   ├── socratic_method_guide.pdf
│   │   └── critical_thinking_handbook.pdf
│   ├── hermes/
│   │   ├── systems_thinking.pdf
│   │   ├── communication_theory.pdf
│   │   └── synthesis_methodologies.pdf
│   └── buddha/
│       ├── mindfulness_meditation.pdf
│       ├── compassionate_communication.pdf
│       └── conflict_deescalation.pdf
```

## 🔍 How Agents Use Knowledge During Debates

### **Automatic Knowledge Retrieval**
1. **Context Analysis**: Agent analyzes current conversation
2. **Knowledge Search**: Searches their specialized knowledge base
3. **Relevant Retrieval**: Finds 3 most relevant pieces of information
4. **Integration**: Incorporates knowledge into their response
5. **Sourced Response**: Provides informed, evidence-based input

### **Example Knowledge Integration**

**User**: "I think we should just ignore climate change data."

**Aristotle's Process**:
1. Detects claim about ignoring scientific data
2. Searches knowledge base for "scientific evidence" and "data evaluation"
3. Retrieves relevant methodology principles
4. Responds: "Let us examine the evidence systematically. According to established research methodology, we must evaluate the quality of data sources, peer review process, and reproducibility of findings before dismissing scientific consensus..."

## 🎯 Best Practices

### **1. Quality Over Quantity**
- Focus on high-quality, authoritative sources
- Ensure content aligns with agent's role
- Avoid contradictory information

### **2. Organized Knowledge**
- Use clear, descriptive metadata
- Categorize content appropriately
- Maintain source attribution

### **3. Regular Updates**
- Add new knowledge as needed
- Update outdated information
- Monitor agent performance

### **4. Testing Knowledge Integration**
- Test agents with specific questions
- Verify they're using appropriate knowledge
- Adjust knowledge base as needed

## 🔧 Technical Implementation

The system uses **ChromaDB** for vector storage with **OpenAI embeddings** for semantic search. Each agent maintains a separate collection:

- `solon_moderation_kb`
- `aristotle_logic_kb` 
- `socrates_inquiry_kb`
- `hermes_synthesis_kb`
- `buddha_compassion_kb`

Knowledge is automatically chunked (1000 characters with 200 character overlap) for optimal retrieval and embedded using `text-embedding-3-small` for efficient semantic search.

## 🎉 Result

Your AI debate agents become **specialized experts** that can draw from real knowledge sources during conversations, making debates more informed, nuanced, and valuable for participants!
" 
