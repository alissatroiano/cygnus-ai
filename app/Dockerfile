# Stage 1: Build React App
FROM node:18-alpine as build

WORKDIR /app

COPY package*.json ./
RUN npm install

ARG VITE_BACKEND_URL
ARG REACT_APP_GEMINI_API_KEY

ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
ENV REACT_APP_GEMINI_API_KEY=$REACT_APP_GEMINI_API_KEY

COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:stable-alpine

COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
