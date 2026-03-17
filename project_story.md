Inspiration
The idea for Cygnus came from something that happened to my little sister a few years ago. She and her friends had been planning a two-week trip to Italy, Greece, and Spain for months — flights, hotels, the Amalfi Coast, Barcelona, everything. The night before the flight, while checking in on the airline's app, her passport wouldn't scan. She called the airline and learned something none of us had ever heard of: many countries enforce a "three or six-month rule," requiring your passport to be valid several months beyond your travel dates. Because her passport fell inside that window, the airline told her entry could depend on the customs officer when she arrived. She decided not to risk it. Her friends left without her. She lost a year of excitement and a lot of money.

That moment stayed with me. When this hackathon came up, it popped back into my head — and I realized that with the power of Gemini, I could finally build something that would have helped her. The UI Navigator category felt like a perfect fit: it's genuinely hard to find the State Department's official international travel guidelines, and an AI agent that can show you exactly where to look could save a lot of people from the same situation.

What it does
Cygnus is a real-time AI travel companion that monitors your browser via screen sharing and detects when you're searching for or booking international flights. The moment it identifies a destination — from a country name, airport code, or booking site like Google Flights, Kayak, or Expedia — it speaks to you directly, alerts you to the entry requirements for that country (passport validity, blank pages, visa status), and offers to open the official U.S. Department of State page for your destination.

If you're booking a domestic flight, Cygnus stays quiet. It only steps in when it matters.

How I Built It
Cygnus is built with React, TypeScript, and Vite, powered by the Google GenAI SDK (@google/genai). It uses Gemini 2.5 Flash via the Gemini Live API to process a real-time screen capture (1fps) and microphone audio simultaneously — giving it both visual and conversational awareness.

The backend is a FastAPI server deployed to Google Cloud Run, connected via WebSocket. It uses Playwright for browser automation when Cygnus needs to open URLs or navigate on the user's behalf. The API key is stored and retrieved securely using Google Secret Manager, and the entire deployment pipeline is automated with Google Cloud Build (

cloudbuild.yaml
).

Challenges I ran into
The biggest technical challenge was the Gemini Live API connection — getting bidirectional audio and screen streaming to work reliably in the browser required careful handling of PCM audio encoding/decoding, frame rate tuning, and WebSocket lifecycle management. I also had to debug a deployment issue where environment variables weren't being correctly injected into the Vite build at Cloud Build time (the wrong build arg names were being passed), which caused the deployed app to fail silently. Working with a GCP business account added some IAM and permissions complexity to the Cloud Build and Secret Manager setup.

Accomplishments that I'm proud of
The core Cygnus experience works end-to-end: it watches your screen, recognizes an international flight, and speaks to you — all in real time. I'm especially proud of the fact that I had this idea just last week and shipped a working, deployed MVP in time for the deadline. Getting the Gemini Live multimodal pipeline (vision + voice, simultaneously) working in a browser without any transcription lag was the hardest part, and it works.

What I learned
I learned a tremendous amount about the Gemini Live API — specifically how to stream PCM audio at 16kHz in, receive 24kHz audio out, and schedule audio chunks without gaps or overlaps using the WebAudio API. I also deepened my understanding of building secure, automated GCP deployments using Cloud Build, Cloud Run, and Secret Manager together.

🚀 What's next for Cygnus
Cross-App Workflows: Moving beyond the browser to navigate desktop applications.
Automated Document Scanning: Checking a user's physical passport via webcam and comparing it against destination requirements.
Mobile Navigator: Bringing Cygnus to mobile devices for on-the-go travel assistance.