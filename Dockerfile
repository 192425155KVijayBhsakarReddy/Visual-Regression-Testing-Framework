FROM python:3.11-slim

# Install system dependencies, Chromium and drivers for headless browser testing
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    libgl1-mesa-glx \
    libglib2.0-0 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Environment variables for headless Chromium execution
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    SELENIUM_HEADLESS=true \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install Python dependencies
COPY visual_regression/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy source repository
COPY . /app

EXPOSE 5000 5001

CMD ["python", "visual_regression/app.py"]

