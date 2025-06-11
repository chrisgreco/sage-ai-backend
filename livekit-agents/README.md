
# SAGE LiveKit Agents

This is the LiveKit Agents service for SAGE's multi-agent debate moderation system.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your actual keys
```

3. Run the agent:
```bash
python main.py dev
```

## Agent Architecture

The service implements a multi-agent moderation system with the following AI personas:

- **Socrates**: Asks clarifying questions when assumptions are made
- **Solon**: Enforces debate rules and ensures fair turn-taking  
- **Buddha**: Monitors tone and diffuses conflict
- **Hermes**: Provides summaries and logical transitions
- **Aristotle**: Fact-checks claims and requests sources

## Deployment

For production deployment, use:
```bash
python main.py start
```
