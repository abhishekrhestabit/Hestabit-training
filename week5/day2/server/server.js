const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');

const app = express();
const PORT = 5000;

// Enable CORS so React can visit us
app.use(cors());

// Connection URL
// "mongo" is the service name we will define in docker-compose.yml
const MONGO_URI = 'mongodb://mongo:27017/testdb';

// Connect to MongoDB
mongoose.connect(MONGO_URI)
    .then(() => console.log('Connected to MongoDB via Docker Networking!'))
    .catch(err => console.error('MongoDB Connection Error:', err));

// Simple API Endpoint
app.get('/api', (req, res) => {
    res.json({ message: 'Hello from Node.js Server connected to MongoDB!' });
});

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});