# Use official Node.js image
FROM node:20-slim

# Set work directory
WORKDIR /app

# Install dependencies first for better caching
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Expose Vite development port (aligned with package.json)
EXPOSE 3003

# Run Vite in development mode with --host flag
# This allows the container's port to be accessed by the host machine
CMD ["npm", "run", "dev", "--", "--host"]
