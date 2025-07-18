# Pipecheetah AI Audio Streaming Server

Pipecheetah is a FastAPI-based WebSocket server that provides real-time AI-powered audio streaming with speech-to-text, language model processing, and text-to-speech capabilities. Built with Pipecat AI framework, it creates an intelligent audio pipeline for interactive voice applications.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Client Integration](#client-integration)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Real-time Audio Processing**: WebSocket-based audio streaming with low latency
- **Multi-Service AI Pipeline**: Integrates AssemblyAI (STT), Cerebras (LLM), and Cartesia (TTS)
- **Voice Activity Detection**: Silero VAD for intelligent audio processing
- **FastAPI Framework**: Modern, high-performance web framework
- **CORS Support**: Cross-origin requests enabled for web clients
- **Audio Recording**: Automatic saving of audio sessions
- **Elementary Teacher Bot**: Pre-configured as an educational assistant

## Requirements

- Python 3.12+
- API Keys for:
  - AssemblyAI (Speech-to-Text)
  - Cerebras (Language Model)
  - Cartesia (Text-to-Speech)
  - OpenAI (Context management)
  - Daily (Optional)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd pipecheetah
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Create environment file**:
   Create a `.env` file in the project root with your API keys:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   DAILY_API_KEY=your_daily_api_key
   ASSEMBLYAI_API_KEY=your_assemblyai_api_key
   CEREBRAS_API_KEY=your_cerebras_api_key
   CARTESIA_API_KEY=your_cartesia_api_key
   ```

2. **Voice Configuration**:
   The server uses Cartesia voice ID `5c9e800f-2a92-4720-969b-99c4ab8fbc87` by default. You can modify this in `bot.py`.

## Running the Server

1. **Start the server**:
   ```bash
   python server.py
   ```

2. **Server will be available at**:
   - HTTP: `http://0.0.0.0:8765`
   - WebSocket: `ws://0.0.0.0:8765/ws`

## Usage

### WebSocket Connection

Connect to the WebSocket endpoint to start audio streaming:

```javascript
const ws = new WebSocket('ws://localhost:8765/ws');

ws.onopen = function(event) {
    console.log('Connected to Pipecheetah server');
};

ws.onmessage = function(event) {
    // Handle audio data or text responses
    console.log('Received:', event.data);
};
```

### Python Client

Use the provided Python client for testing:

```bash
python client/python/test_client.py
```

## API Endpoints

- **WebSocket**: `/ws` - Main audio streaming endpoint
- **Health Check**: Server runs on port 8765 with CORS enabled

## Client Integration

The server expects audio data in PCM format and returns:
- Processed audio responses
- Text transcriptions
- AI-generated speech

Audio sessions are automatically saved as WAV files with timestamps.

## Architecture

### AI Pipeline Components

1. **Audio Input**: WebSocket receives PCM audio data
2. **VAD**: Silero Voice Activity Detection
3. **STT**: AssemblyAI Speech-to-Text (sandbox endpoint)
4. **LLM**: Cerebras Llama-4-Scout model for response generation
5. **TTS**: Cartesia Text-to-Speech
6. **Audio Output**: Processed audio returned via WebSocket

### System Prompt

Configured as an elementary teacher:
- Responds in short, simple sentences
- Audio-optimized responses (no special characters)
- Educational and supportive tone

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the BSD 2-Clause License.

Copyright (c) 2025, Daily