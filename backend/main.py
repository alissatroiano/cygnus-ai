from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
import asyncio
import base64

from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Cygnus API")

# Configure CORS so the React app can communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)
MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

CONFIG = types.LiveConnectConfig(
    response_modalities=[
        "AUDIO",
    ],
    media_resolution="MEDIA_RESOLUTION_MEDIUM",
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Zephyr")
        )
    ),
    context_window_compression=types.ContextWindowCompressionConfig(
        trigger_tokens=104857,
        sliding_window=types.SlidingWindow(target_tokens=52428),
    ),
)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Cygnus API"}

@app.get("/api/health")
def health_check():
    api_key_configured = bool(os.getenv("GEMINI_API_KEY"))
    return {"status": "healthy", "gemini_api_key_configured": api_key_configured}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connection established")
    try:
        async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
            print("Connected to Gemini Live API")
            
            async def receive_from_client():
                """Receive audio/video data from the React client and send to Gemini."""
                try:
                    while True:
                        data = await websocket.receive_text()
                        msg = json.loads(data)
                        
                        # Handle string messages sent via text proxy
                        if "clientContent" in msg:
                            # Send client text content to Gemini
                            await session.send(input=msg["clientContent"])
                        
                        # Handle realtime media (audio/video base64 chunks)
                        if "realtimeInput" in msg:
                            mime_type = msg["realtimeInput"]["mimeType"]
                            b64_data = msg["realtimeInput"]["data"]
                            raw_data = base64.b64decode(b64_data)
                            await session.send(input={"data": raw_data, "mime_type": mime_type})

                except WebSocketDisconnect:
                    print("Client disconnected")
                except Exception as e:
                    print(f"Error receiving from client: {e}")

            async def receive_from_gemini():
                """Receive audio and text from Gemini and send to the React client."""
                try:
                    while True:
                        turn = session.receive()
                        async for response in turn:
                            if response.data:
                                # Send audio data as base64 to client
                                b64_audio = base64.b64encode(response.data).decode('utf-8')
                                await websocket.send_json({
                                    "serverContent": {
                                        "modelTurn": {
                                            "parts": [{"inlineData": {"data": b64_audio, "mimeType": "audio/pcm"}}]
                                        }
                                    }
                                })
                            
                            if response.text:
                                await websocket.send_json({
                                    "serverContent": {
                                        "modelTurn": {
                                            "parts": [{"text": response.text}]
                                        }
                                    }
                                })
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Error receiving from Gemini: {e}")

            # Run both tasks concurrently
            async with asyncio.TaskGroup() as tg:
                tg.create_task(receive_from_client())
                tg.create_task(receive_from_gemini())

    except Exception as e:
        print(f"Gemini connection error: {e}")
        await websocket.close()

