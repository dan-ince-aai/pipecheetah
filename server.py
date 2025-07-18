#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import uvicorn
from bot import run_bot
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connection for audio streaming."""
    await websocket.accept()
    print("WebSocket connection accepted")
    
    # Initialize the bot with the WebSocket connection
    await run_bot(websocket, app.state.testing)


if __name__ == "__main__":
    app.state.testing = False  # No testing mode for now
    uvicorn.run(app, host="0.0.0.0", port=8765)
