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
    allow_origins=["*"], # In production, replace with specific origins
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
                search_selector = "input[aria-label*='Search'], input[placeholder*='Learn about'], input#country-search"
                try:
                    await page.wait_for_selector(search_selector, timeout=5000)
                    await page.fill(search_selector, country)
                    await page.press(search_selector, "Enter")
                except:
                    await page.keyboard.type(country)
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
MODEL = "models/gemini-2.0-flash-exp"

SYSTEM_PROMPT = """
You are Cynus, a proactive International Travel Advisor. You monitor a live video stream of the user's browser and alert them to check passport validity rules & requirements for their destination country when they are booking international flights. 

CRITICAL TRIGGER:
As soon as you see a flight booking screen, airline logo (Delta, United, Emirates, etc.), or airport codes (JFK, LHR, CDG, etc.) for a country different from the user's origin, you MUST INTERRUPT.

OBJECTIVE:
1. Detect when the user is researching or booking international flights.
2. INTERRUPT IMMEDIATELY: Say: "Excuse me, I noticed you're looking at international flights to [Destination Name]. Did you know 40% of travel cancellations are caused by passport validity issues, like the 6-month rule?"
3. OFFER ACTION: "Would you like me to check the specific entry requirements for [Destination Name] right now?"
4. TAKE CONTROL: If they say yes or imply they want help, use `navigate_to_url` to go to https://travel.state.gov/en/international-travel.html. Then, use `select_country_requirements` with the destination name.

GUIDELINES:
- Be proactive. Don't wait for them to ask. You are an automated assistant.
- Use the destination name you see on screen.
- If you aren't sure of the country yet, ask: "I see you're booking a flight, where are you headed? I want to check your passport rules for you."
"""

TOOLS = [
    {
        "function_declarations": [
            {
                "name": "navigate_to_url",
                "description": "Navigate to a specific URL in the browser.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "url": {
                            "type": "STRING",
                            "description": "The URL to navigate to."
                        }
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "select_country_requirements",
                "description": "Searches for and selects a country on travel.state.gov to view its specific entry requirements.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "country": {
                            "type": "STRING",
                            "description": "The name of the country to search for (e.g., 'France', 'Japan')."
                        }
                    },
                    "required": ["country"]
                }
            },
            {
                "name": "click_element",
                "description": "Clicks on a specific element on the page using a selector.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "selector": { "type": "STRING", "description": "CSS selector" }
                    },
                    "required": ["selector"]
                }
            },
            {
                "name": "type_text",
                "description": "Types text into an input field.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "selector": { "type": "STRING", "description": "CSS selector" },
                        "text": { "type": "STRING", "description": "Text to type" }
                    },
                    "required": ["selector", "text"]
                }
            },
            {
                "name": "scroll_window",
                "description": "Scrolls the window.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "direction": { "type": "STRING", "enum": ["up", "down"] }
                    },
                    "required": ["direction"]
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
    tools=TOOLS,
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
        browser = await p.chromium.launch(headless=False) # Headed for demo visibility
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
                                
                                if response.tool_call:
                                    print(f"Tool call received: {response.tool_call}")
                                    
                                    for fc in response.tool_call.function_calls:
                                        tool_name = fc.name
                                        args = fc.args
                                        
                                        print(f"Executing tool {tool_name} with args {args}")
                                        
                                        try:
                                            if tool_name == "navigate_to_url":
                                                await page.goto(args["url"])
                                            elif tool_name == "select_country_requirements":
                                                country = args.get("country")
                                                if country:
                                                    # Try to find the search input on travel.state.gov
                                                    search_selector = "input[aria-label*='Search'], input[placeholder*='Learn about'], input#country-search"
                                                    try:
                                                        await page.wait_for_selector(search_selector, timeout=5000)
                                                        await page.fill(search_selector, country)
                                                        await page.press(search_selector, "Enter")
                                                    except:
                                                        # Fallback for dynamic sites
                                                        await page.keyboard.type(country)
                                                        await page.keyboard.press("Enter")
                                            elif tool_name == "click_element":
                                                # Using a generic selector approach or coordinates
                                                # For simplicity, we'll try to use the selector if provided
                                                selector = args.get("selector")
                                                if selector:
                                                    await page.click(selector)
                                            elif tool_name == "type_text":
                                                selector = args.get("selector")
                                                text = args.get("text")
                                                if selector and text:
                                                    await page.fill(selector, text)
                                            elif tool_name == "scroll_window":
                                                direction = args.get("direction", "down")
                                                if direction == "down":
                                                    await page.evaluate("window.scrollBy(0, 500)")
                                                else:
                                                    await page.evaluate("window.scrollBy(0, -500)")
                                            
                                            # Send response back to Gemini
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

