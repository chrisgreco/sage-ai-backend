# LiveKit Debate Moderator Agent

This project implements a LiveKit agent that serves as a debate moderator. The agent joins a LiveKit room, listens to the participants, and helps moderate the debate by asking clarifying questions, enforcing debate rules, monitoring emotional tone, providing summaries, and requesting sources for factual claims.

## Requirements

- Python 3.8+
- OpenAI API key
- LiveKit API key and secret

## Installation

1. Clone the repository
2. Install the dependencies:

```bash
pip install livekit-agents livekit-plugins-openai livekit-plugins-silero python-dotenv pyjwt requests
```

## Configuration

The application can be configured using command line arguments or environment variables:

- `--livekit-url`: LiveKit server URL (default: `wss://sage-2kpu4z1y.livekit.cloud`)
- `--livekit-api-key`: LiveKit API key
- `--livekit-api-secret`: LiveKit API secret
- `--openai-api-key`: OpenAI API key
- `--debate-topic`: Debate topic (default: "The impact of artificial intelligence on society")
- `--room-name`: Room name to join (for test client, default: "test-debate-room")
- `--identity`: User identity (for test client, default: "test-user")

## Usage

### Running the Agent

To run the agent:

```bash
python run.py agent --openai-api-key your_openai_api_key
```

### Running the Test Client

To run the test client that creates a room and waits for the agent to connect:

```bash
python run.py client
```

### Running Both

To run both the agent and test client:

```bash
python run.py both --openai-api-key your_openai_api_key
```

## Project Structure

- `run_agent.py`: The main agent implementation
- `test_agent.py`: A test client to create a room and test the agent
- `run.py`: A helper script to run the agent, test client, or both

## How It Works

1. The agent registers with the LiveKit server
2. When a job is received, the agent connects to the specified room
3. The agent listens to the participants and processes their speech
4. The agent responds with AI-generated speech when appropriate
5. The agent provides moderation, summaries, and guidance during the debate

## Agent Capabilities

The SAGE debate moderator can:

- Ask clarifying questions when participants make assumptions
- Enforce debate rules (no interruptions, personal attacks, etc.)
- Monitor emotional tone and diffuse conflicts
- Provide summaries and transitions during natural pauses
- Request sources for factual claims

## Customization

You can customize the debate topic using the `--debate-topic` argument:

```bash
python run.py agent --openai-api-key your_openai_api_key --debate-topic "Climate change solutions"
```

## Troubleshooting

- If you encounter authentication issues, make sure your LiveKit API key and secret are correct
- If the agent doesn't connect, check the logs for errors
- If you see errors related to OpenAI, make sure your OpenAI API key is valid

## License

This project is licensed under the MIT License - see the LICENSE file for details.
