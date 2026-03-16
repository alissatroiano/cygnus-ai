from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import json
import asyncio
import base64

from google import genai
from google.genai import types
from playwright.async_api import async_playwright

# Load environment variables from .env file
load_dotenv()

app = FastAPI(title="Cygnus API")

# Configure CORS so the React app can communicate with the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Playwright state for the tool execution engine
playwright_instance = None
browser_instance = None
current_page = None

async def get_browser_page():
    global playwright_instance, browser_instance, current_page
    if not playwright_instance:
        playwright_instance = await async_playwright().start()
        browser_instance = await playwright_instance.chromium.launch(headless=False)
        current_page = await browser_instance.new_page()
    return current_page

@app.post("/execute-tool")
async def execute_tool(tool: dict):
    name = tool.get("name")
    args = tool.get("args", {})
    page = await get_browser_page()
    
    print(f"Backend executing tool: {name} with {args}")
    
    try:
        if name == "navigate_to_url":
            await page.goto(args.get("url"))
        elif name == "select_country_requirements":
            country = args.get("country_name") or args.get("country")
            if country:
                # Scroll down to reveal the "Learn about your destination" box
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1) # Allow scroll to settle
                
                search_selector = "input#TSGcomboBox"
                go_button = "button[aria-label='Open selected page']"
                
                try:
                    await page.wait_for_selector(search_selector, timeout=5000)
                    await page.click(search_selector)
                    # Clear existing text if any
                    await page.evaluate(f"document.querySelector('{search_selector}').value = ''")
                    # Type with delay to trigger dynamic dropdown
                    await page.type(search_selector, country, delay=100)
                    await asyncio.sleep(1.5) # Wait for suggestions
                    
                    # Select the first suggestion (usually highlighted)
                    await page.press(search_selector, "Enter")
                    await asyncio.sleep(1)
                    
                    # Trigger navigation
                    await page.click(go_button)
                    print(f"Successfully selected {country} and clicked Go.")
                except Exception as e:
                    print(f"Selector-based selection failed: {e}")
                    # Desperate fallback: try typing and pressing Enter twice
                    await page.keyboard.type(country)
                    await asyncio.sleep(0.5)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(0.5)
                    await page.keyboard.press("Enter")
        elif name == "click_element":
            await page.click(args.get("selector"))
        elif name == "type_text":
            await page.fill(args.get("selector"), args.get("text"))
        elif name == "scroll_window":
            direction = args.get("direction", "down")
            if direction == "down":
                await page.evaluate("window.scrollBy(0, 500)")
            else:
                await page.evaluate("window.scrollBy(0, -500)")
        return {"status": "success"}
    except Exception as e:
        print(f"Tool execution error: {e}")
        return {"status": "error", "message": str(e)}

client = genai.Client(
    http_options={"api_version": "v1beta"},
    api_key=os.environ.get("GEMINI_API_KEY"),
)
MODEL = "gemini-2.0-flash-exp"

SYSTEM_PROMPT = """
You are Cygnus, a real-time UI Navigator and International Travel Advisor. 

CORE MISSION:
You observe the user's screen capture to provide proactive, hands-free assistance.

CRITICAL BEHAVIOR:
1. VISUAL MONITORING: Constantly analyze the video stream for international travel patterns (flight searches, airport codes, passports).
2. AUTONOMOUS ALERT: If you see an international destination, call 'trigger_flight_alert' IMMEDIATELY.
3. VISUAL NAVIGATION: You can interact with the UI by "pointing" and clicking. Use 'click_at_location' with normalized coordinates [0-100] based on where you see elements in the video.
4. SEARCH: When a destination is detected, use your Google Search tool to find 2026 entry requirements (passport validity, visas) for that specific country and tell the user.

Style: Proactive, safety-oriented, and high-tech.
"""

TOOLS = [
    {
        "function_declarations": [
            {
                "name": "click_at_location",
                "description": "Simulates a click at specific normalized coordinates (0-100) on the user's screen as seen in the video stream.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "x": { "type": "NUMBER", "description": "Horizontal coordinate from 0 to 100" },
                        "y": { "type": "NUMBER", "description": "Vertical coordinate from 0 to 100" }
                    },
                    "required": ["x", "y"]
                }
            },
            {
                "name": "trigger_flight_alert",
                "description": "Action: Trigger a critical UI alert popover for the user when an international flight destination is visually detected on screen.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "destination": { "type": "STRING", "description": "The destination country or city detected in the video." }
                    },
                    "required": ["destination"]
                }
            }
        ]
    }
]

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
    system_instruction=types.Content(
        parts=[types.Part(text=SYSTEM_PROMPT)]
    ),
    tools=[types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())] + TOOLS,
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
    
    async with async_playwright() as p:
        # Cloud Run needs headless=True
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
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
                            
                            # Handle tool responses from frontend
                            if "toolResponse" in msg:
                                await session.send(input=types.LiveClientToolResponse(
                                    function_responses=[
                                        types.LiveClientFunctionResponse(
                                            name=resp["name"],
                                            id=resp["id"],
                                            response=resp["response"]
                                        ) for resp in msg["toolResponse"]["functionResponses"]
                                    ]
                                ))

                    except WebSocketDisconnect:
                        print("Client disconnected")
                    except Exception as e:
                        print(f"Error receiving from client: {e}")

                async def receive_from_gemini():
                    """Receive audio and text from Gemini and send to the React client."""
                    try:
                        async for response in session.receive():
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
                                
                                if response.tool_call:
                                    print(f"Tool call received: {response.tool_call}")
                                    
                                    for fc in response.tool_call.function_calls:
                                        tool_name = fc.name
                                        args = fc.args
                                        
                                        print(f"Executing tool {tool_name} with args {args}")
                                        
                                        try:
                                            if tool_name == "click_at_location":
                                                # The frontend handles the visual cursor, the backend just confirms
                                                print(f"Visual Click triggered at: {args.get('x')}, {args.get('y')}")
                                            elif tool_name == "trigger_flight_alert":
                                                # Primarily a frontend UI trigger
                                                print(f"Triggering flight alert for {args.get('destination')}")
                                            
                                            # Send response back to Gemini to complete the turn
                                            await session.send(
                                                input=types.LiveClientToolResponse(
                                                    function_responses=[
                                                        types.LiveClientFunctionResponse(
                                                            name=tool_name,
                                                            id=fc.id,
                                                            response={"status": "success"}
                                                        )
                                                    ]
                                                )
                                            )
                                        except Exception as tool_err:
                                            print(f"Tool execution error: {tool_err}")
                                            await session.send(
                                                input=types.LiveClientToolResponse(
                                                    function_responses=[
                                                        types.LiveClientFunctionResponse(
                                                            name=tool_name,
                                                            id=fc.id,
                                                            response={"status": "error", "message": str(tool_err)}
                                                        )
                                                    ]
                                                )
                                            )

                                    # Also notify frontend of tool activity
                                    await websocket.send_json({
                                        "toolCall": {
                                            "functionCalls": [
                                                {
                                                    "name": fc.name,
                                                    "args": fc.args,
                                                    "id": fc.id
                                                } for fc in response.tool_call.function_calls
                                            ]
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
        finally:
            await browser.close()
            await websocket.close()

