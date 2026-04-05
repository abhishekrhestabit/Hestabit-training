FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
# --host needed for Vite to expose network
CMD ["npm", "run", "dev"]