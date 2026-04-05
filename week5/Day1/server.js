// server.js
const express = require('express');
const app = express();
const PORT = 3000;

app.get('/', (req, res) => {
    res.send('Hello! I am running inside a Docker Container!');
});

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});