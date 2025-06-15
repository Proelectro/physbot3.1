# Use official Python slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (optional: ffmpeg, etc.)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your source code
COPY . .

# Set environment variable for Google credentials (mounted via Secret Manager)
ENV GOOGLE_APPLICATION_CREDENTIALS="/creds.json"

# Run the bot
CMD ["python", "physbot.py"]
