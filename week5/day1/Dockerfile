# 1. FROM: Specifies the base image (OS + Node runtime)
# We are using a lightweight version of Node running on Alpine Linux
FROM node:18-alpine

# 2. WORKDIR: Sets the working directory inside the container
# All future commands will run from here. Like 'cd /app'
WORKDIR /app

# 3. COPY: Moves files from your computer (host) to the container
# Format: COPY <source_on_your_pc> <destination_in_container>
COPY package*.json ./

# 4. RUN: Executes commands inside the container during build
# Here we install the dependencies listed in package.json
RUN npm install

# Copy the rest of the app code
COPY . .

# 5. EXPOSE: Documents that the container listens on this port
EXPOSE 3000

# 6. CMD: The command to start the application when the container runs
CMD ["node", "server.js"]