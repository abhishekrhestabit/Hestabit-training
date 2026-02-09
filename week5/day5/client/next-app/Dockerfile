# Base image
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Install dependencies (Layer caching)
COPY package*.json ./
RUN npm install

# Copy source code
COPY . .

# Build the Next.js application
RUN npm run build

# Expose the listening port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]