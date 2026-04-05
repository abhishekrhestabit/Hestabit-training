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
  app.get('/', (_, res) => res.send('OK'));

  app.get('/health', (_, res) => res.send('Health OK'));
  routeCount++;

  logger.info(`Routes mounted: ${routeCount} endpoints`);

  // NOTE: Don't add 404 or error handlers here
  // They will be added in index.js AFTER all routes are mounted

  return app;
};
                           