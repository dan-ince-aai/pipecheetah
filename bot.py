#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import datetime
import io
import os
import sys
import wave

import aiofiles
from dotenv import load_dotenv
import numpy as np
from fastapi import WebSocket
from loguru import logger
from pipecat.frames.frames import StartFrame

from pipecat.serializers.base_serializer import FrameSerializer
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.audio.audio_buffer_processor import AudioBufferProcessor
from pipecat.services.assemblyai.stt import AssemblyAISTTService
from pipecat.services.assemblyai.models import AssemblyAIConnectionParams
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.services.cerebras.llm import CerebrasLLMService
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


async def save_audio(server_name: str, audio: bytes, sample_rate: int, num_channels: int):
    if len(audio) > 0:
        filename = (
            f"{server_name}_recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
        )
        with io.BytesIO() as buffer:
            with wave.open(buffer, "wb") as wf:
                wf.setsampwidth(2)
                wf.setnchannels(num_channels)
                wf.setframerate(sample_rate)
                wf.writeframes(audio)
            async with aiofiles.open(filename, "wb") as file:
                await file.write(buffer.getvalue())
        logger.info(f"Merged audio saved to {filename}")
    else:
        logger.info("No audio data to save")


async def run_bot(websocket_client: WebSocket, testing: bool):
    # Create a custom serializer for raw PCM audio
    class RawPCMSerializer(FrameSerializer):
        """Serialize raw PCM audio frames over WebSocket.

        Incoming bytes from the client are wrapped in `InputAudioRawFrame` so the
        pipeline treats them like any other audio source. For outgoing audio, we
        simply forward the raw bytes contained in `AudioRawFrame` instances.
        """

        def __init__(self, sample_rate: int = 16000, channels: int = 1):
            self._sample_rate = sample_rate
            self._channels = channels

        # The serializer uses binary payloads
        @property
        def type(self):
            from pipecat.serializers.base_serializer import FrameSerializerType
            return FrameSerializerType.BINARY

        async def setup(self, frame: StartFrame):
            # Capture pipeline configuration so we can construct matching frames
            self._sample_rate = frame.audio_in_sample_rate or self._sample_rate

        async def serialize(self, frame):
            # Only handle raw audio frames destined for the client
            from pipecat.frames.frames import AudioRawFrame
            if isinstance(frame, AudioRawFrame):
                import logging
                logging.getLogger(__name__).debug(f"Serializing audio frame of {len(frame.audio)} bytes")
                return frame.audio
            return None

        async def deserialize(self, data):
            """Convert incoming WebSocket payloads into Pipecat frames."""
            from pipecat.frames.frames import InputAudioRawFrame, StartFrame
            # Binary payload -> raw audio frame
            if isinstance(data, (bytes, bytearray)):
                return InputAudioRawFrame(
                    audio=bytes(data),
                    sample_rate=self._sample_rate,
                    num_channels=self._channels,
                )
            # Text payload (JSON) -> StartFrame with audio params
            if isinstance(data, str):
                try:
                    import json
                    obj = json.loads(data)
                    if obj.get("type") == "start":
                        self._sample_rate = obj.get("audio_in_sample_rate", self._sample_rate)
                        self._channels = obj.get("audio_in_channels", self._channels)
                        return StartFrame(
                            audio_in_sample_rate=self._sample_rate,
                            audio_in_channels=self._channels,
                        )
                except json.JSONDecodeError:
                    pass
            return None

    # Initialize audio buffer processor
    audiobuffer = AudioBufferProcessor(
        sample_rate=16000,
        channels=1
    )

    transport = FastAPIWebsocketTransport(
        websocket=websocket_client,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=RawPCMSerializer(),
        ),
    )

    llm = CerebrasLLMService(
        api_key=os.getenv("CEREBRAS_API_KEY"),
        model="llama-4-scout-17b-16e-instruct"
    )

    stt = AssemblyAISTTService(
        api_key=os.getenv("ASSEMBLYAI_API_KEY"),
        vad_force_turn_endpoint=False,
        api_endpoint_base_url="wss://streaming.sandbox023.assemblyai-labs.com/v3/ws",
        connection_params=AssemblyAIConnectionParams(
            formatted_finals=False,
        )
    )

    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="5c9e800f-2a92-4720-969b-99c4ab8fbc87",
    )

    messages = [
        {
            "role": "system",
            "content": "You are an elementary teacher in an audio call. Your output will be converted to audio so don't include special characters in your answers. Respond to what the student said in a short short sentence.",
        },
    ]

    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    # NOTE: Watch out! This will save all the conversation in memory. You can
    # pass `buffer_size` to get periodic callbacks.
    audiobuffer = AudioBufferProcessor()

    pipeline = Pipeline([
        transport.input(),  # incoming audio frames
        audiobuffer,
        stt,
        context_aggregator.user(),  # User responses
        llm,
        tts,
        transport.output(),  # outgoing audio frames
        context_aggregator.assistant(),  # Assistant spoken responses
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Start recording.
        await audiobuffer.start_recording()
        # Kick off the conversation.
        messages.append({"role": "system", "content": "Please introduce yourself to the user."})
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        await task.cancel()

    @audiobuffer.event_handler("on_audio_data")
    async def on_audio_data(buffer, audio, sample_rate, num_channels):
        server_name = f"server_{websocket_client.client.port}"
        await save_audio(server_name, audio, sample_rate, num_channels)

    # We use `handle_sigint=False` because `uvicorn` is controlling keyboard
    # interruptions. We use `force_gc=True` to force garbage collection after
    # the runner finishes running a task which could be useful for long running
    # applications with multiple clients connecting.
    runner = PipelineRunner(handle_sigint=False, force_gc=True)

    await runner.run(task)
