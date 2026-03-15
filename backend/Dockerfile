# Use the official Playwright Python image which includes all browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (already in the image, but ensuring the right ones are installed for the env)
RUN playwright install chromium

# Copy project files
COPY . .

# Expose default port
ENV PORT 8080
EXPOSE 8080

# Start server using shell form to allow variable expansion
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
