# ClawChat Backend

A Python WebSocket server for real-time chat applications.

## Features

- **WebSocket Support**: Real-time bidirectional communication
- **Connection Management**: Handle multiple concurrent connections
- **Ping/Pong Keepalive**: Automatic connection health monitoring
- **Configurable**: YAML-based configuration
- **Structured Logging**: Comprehensive logging with rotation
- **Error Handling**: Robust error recovery and graceful degradation

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python server.py
```

## Configuration

Edit `config.yaml` to customize:
- Host and port
- Maximum connections
- Logging levels
- Ping interval and timeout

## Project Structure

```
backend/
├── server.py           # Main WebSocket server
├── config.yaml         # Server configuration
├── requirements.txt    # Python dependencies
└── logging_config.py   # Logging configuration
```
