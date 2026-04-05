const express = require('express');
const os = require('os'); // Import OS module to get hostname
const app = express();
const PORT = 3000;

app.get('/api', (req, res) => {
    // os.hostname() in Docker returns the Container ID
    const containerID = os.hostname();
    
    console.log(`Request served by container: ${containerID}`);
    
    res.json({ 
        message: 'Hello from Scaled Backend!',
        server_id: containerID 
    });
});

app.listen(PORT, () => {
    console.log(`Backend Server running on port ${PORT} | ID: ${os.hostname()}`);
});