# Cygnus Agent Implementation Plan

This plan details the steps to implement the Cygnus proactive International Travel Advisor on top of the Google Multimodal Live API Web Console. We will replace the default [Altair](file:///c:/Users/Cecca/Desktop/Alissa/web%20dev/HACKATHONS/cygnus-ai/frontend/src/components/altair/Altair.tsx#42-112) graphing component with a dedicated `CygnusAgent` component that configures the Gemini API according to the requirements and handles the custom tool executions.

## Proposed Changes

### `frontend/src/components/cygnus-agent` (New Component)
- Create a new directory and component `CygnusAgent.tsx`.
- Establish the `systemInstruction` using the provided user prompt (Cygnus, International Travel Advisor).
- Define the two required tools: `navigate_to_url` and `select_country_requirements`.
- Setup a `useEffect` to register these with `setConfig` via [useLiveAPIContext](file:///c:/Users/Cecca/Desktop/Alissa/web%20dev/HACKATHONS/cygnus-ai/frontend/src/contexts/LiveAPIContext.tsx#41-48).
- Setup a `useEffect` to handle the `toolcall` event emitted by the Gemini Live API. When `navigate_to_url` or `select_country_requirements` is called, it will execute the dummy action (like logging or a small UI pop-up indicating the action to the user) and send the tool response back to the API.

### [frontend/src/App.tsx](file:///c:/Users/Cecca/Desktop/Alissa/web%20dev/HACKATHONS/cygnus-ai/frontend/src/App.tsx)
#### [MODIFY] [App.tsx](file:///c:/Users/Cecca/Desktop/Alissa/web%20dev/HACKATHONS/cygnus-ai/frontend/src/App.tsx)(file:///c:/Users/Cecca/Desktop/Alissa/web%20dev/HACKATHONS/cygnus-ai/frontend/src/App.tsx)
- Remove the `<Altair />` component.
- Import and insert the `<CygnusAgent />` component instead.

## Verification Plan

### Manual Verification
1. Start the React frontend application using `npm start`.
2. Allow microphone and screen recording permissions in the browser.
3. Share a screen containing a mock flight booking page (e.g. Expedia, Google Flights) targeting an international destination.
4. Verify that Cygnus detects the screen and verbally interrupts with the required prompt: "I noticed you're looking at international flights...".
5. Verbally agree to Cygnus's offer to check the destination.
6. Verify in the frontend console / UI that the `navigate_to_url` tool is called by Cygnus.
7. Verify that the `select_country_requirements` tool is called with the correct country name based on the visual context of the flight.
