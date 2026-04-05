const express = require('express');
const os = require('os');
const app = express();

app.get('/', (req, res) => {
    res.json({ 
        message: 'You have reached the SECURE fortress!',
        server: os.hostname(),
        protocol: req.protocol // Will likely show 'http' because NGINX decrypts it first
    });
});

app.listen(3000, () => console.log('Backend running on 3000'));