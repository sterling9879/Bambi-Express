# Frontend Dockerfile - Simplified
FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
