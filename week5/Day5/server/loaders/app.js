const express = require('express');
const cors = require('cors');

const setupApp = () => {
  const app = express();

  // Middleware
  app.use(cors()); 
  app.use(express.json()); 

  return app;
};

module.exports = setupApp;