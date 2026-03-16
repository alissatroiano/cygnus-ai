# Stage 1: Build the Vite/React frontend
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

# Accept API key and backend URL as build args so Vite can bake them in
ARG GEMINI_API_KEY
ARG VITE_BACKEND_URL

ENV GEMINI_API_KEY=$GEMINI_API_KEY
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

COPY . .
RUN npm run build

# Stage 2: Run the Express server to serve the built app
FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --omit=dev

# Copy the built frontend
COPY --from=build /app/dist ./dist

# Copy the server entry point
COPY server.ts ./
COPY tsconfig.json ./

# Runtime env vars — injected by Cloud Run, NOT baked into the image
ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

# Run the express server using tsx
CMD ["npx", "tsx", "server.ts"]
