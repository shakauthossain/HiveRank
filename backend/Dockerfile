# Use the official Playwright Python image which includes system-level browser dependencies
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

# Set work directory
WORKDIR /app

# Install system dependencies (libpq-dev for Postgres, gcc for building, Node for pptxgenjs)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt watchfiles

# Ensure only Chromium is installed to save bandwidth and image size
RUN playwright install chromium

# Copy the rest of the application
COPY . .

# Deck builder (pptxgenjs) — Node 20 installed above
RUN cd /app/deck-builder && npm install --omit=dev

# Create reports directory if it doesn't exist
RUN mkdir -p reports

# Expose backend port
EXPOSE 8003

# Production default — do NOT use --reload (spawns a child process that crashes
# under many hosts and is unsafe in prod). Local compose overrides with --reload.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
