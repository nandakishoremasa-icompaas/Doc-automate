# Use the official Microsoft Playwright image as the base
# This image contains all necessary Linux dependencies for browsers
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set the working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# The base image uses Chromium by default, but your script specifically targets google-chrome.
# We will install the official Google Chrome Stable directly into the container.
RUN apt-get update && apt-get install -y wget gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire project into the container
COPY . .

# Expose the Flask web port
EXPOSE 5000

# Run the Flask application
CMD ["python", "app.py"]
