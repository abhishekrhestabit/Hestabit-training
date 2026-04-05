FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
# Inline initialization to save time creating package.json manually
RUN npm init -y && npm install express
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]