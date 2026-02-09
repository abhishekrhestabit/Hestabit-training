const express = require('express');
const cors = require('cors');

const setupApp = () => {
  const app = express();

  // Middleware
  app.use(cors()); // Allow Frontend to talk to Backend
  app.use(express.json()); // Parse incoming JSON bodies

  return app;
};

module.exports = setupApp;