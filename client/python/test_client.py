import asyncio
import json
import websockets
import numpy as np
import sounddevice as sd
import argparse
import contextlib

async def audio_stream(uri: str):
    """Connect to WebSocket server and stream audio with back-pressure handling."""
    queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=100)  # larger buffer

    async with websockets.connect(uri, ping_interval=10, ping_timeout=20) as websocket:
        print(f"Connected to {uri}")

        # --- task that pulls from the queue and sends over WS ---
        async def sender():
            while True:
                data = await queue.get()
                try:
                    await websocket.send(data)
                finally:
                    queue.task_done()

        sender_task = asyncio.create_task(sender())

        # --- set up microphone & speaker ---
        loop = asyncio.get_running_loop()
        def mic_callback(indata, frames, time, status):
            if status.input_overflow:
                print("Audio buffer overflow!")
            # copy bytes so we can return immediately
            pcm_bytes = bytes(indata)
            def safe_put(item: bytes):
                if not queue.full():
                    queue.put_nowait(item)
            loop.call_soon_threadsafe(safe_put, pcm_bytes)

        with sd.InputStream(samplerate=16000, channels=1, dtype='int16', callback=mic_callback), \
             sd.OutputStream(samplerate=24000, channels=1, dtype='int16') as speaker:
            print("Streaming microphone… Press Ctrl-C to stop.")
            try:
                while True:
                    try:
                        response_data = await websocket.recv()
                        if isinstance(response_data, (bytes, bytearray)) and len(response_data):
                            speaker.write(np.frombuffer(response_data, dtype=np.int16))
                    except websockets.exceptions.ConnectionClosedOK:
                        print("Server closed connection cleanly.")
                        break
            except asyncio.CancelledError:
                pass
            except KeyboardInterrupt:
                print("\nExiting…")

        sender_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sender_task

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test WebSocket audio streaming")
    parser.add_argument('--uri', default='ws://localhost:8765/ws', help='WebSocket server URI')
    args = parser.parse_args()
    
    try:
        asyncio.run(audio_stream(args.uri))
    except KeyboardInterrupt:
        print("\nExiting…")
