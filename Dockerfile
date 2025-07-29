FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl unzip gnupg2 wget \
    chromium chromium-driver \
    && apt-get clean

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy application code
COPY . /app
WORKDIR /app

# Expose port
EXPOSE 5000

# Start Flask app
CMD ["python", "app.py"]
