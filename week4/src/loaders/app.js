const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const logger = require('../utils/logger');

module.exports = async function loadApp() {
  const app = express();

  // Middlewares
  app.use(express.json());
  app.use(cors());
  app.use(helmet());

  logger.info('Middlewares loaded');

  // Routes
  let routeCount = 0;

  app.get('/health', (_, res) => res.send('OK'));
  routeCount++;

  logger.info(`Routes mounted: ${routeCount} endpoints`);

  // 404 handler
  app.use((req, res) => {
    res.status(404).json({ message: 'Route not found' });
  });

  // Error handler
  app.use((err, req, res, next) => {
    logger.error(err.message);
    res.status(500).json({ message: 'Internal server error' });
  });

  return app;
};
