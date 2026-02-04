const express = require('express'); // Needed for json limit config
const config = require('./config');
const logger = require('./utils/logger');
const connectDB = require('./loaders/db');
const loadApp = require('./loaders/app');
const requestTracing = require('./middlewares/tracing');
require('./models/Users');  // Register User model
require('./models/Products'); // Register Product model

if (process.env.NODE_ENV !== 'production') {
  require('./workers/email.worker');
  logger.info('Email worker started in development mode');
}

// --- DAY 3 & 4 IMPORTS ---
const setupSecurity = require('./middlewares/security');
const productRouter = require('./routes/product.routes');
const globalErrorHandler = require('./middlewares/error.middleware');
const AppError = require('./utils/AppError');

(async () => {
  try {
    // 1. Connect to Database
    await connectDB();

    // 2. Load the base Express App (from your loader)
    const app = await loadApp();

    app.use(requestTracing);
    // A. Apply Security Middleware (Day 4)
    // (Helmet, CORS, Rate Limit, Sanitization)
    setupSecurity(app);

    // B. Body Parser with Limit (Day 4)
    // We explicitly set this to protect against large payloads.
    // Note: If loadApp already does this, this line reinforces the limit.
    app.use(express.json({ limit: '10kb' }));

    // C. Mount Product Routes (Day 3)
    app.use('/api/v1/products', productRouter);

    // D. 404 Handler (Day 3)
    // Must be after routes
    app.all(/(.*)/, (req, res, next) => {
      next(new AppError(`Can't find ${req.originalUrl} on this server!`, 404));
    });

    // E. Global Error Handler (Day 3)
    app.use(globalErrorHandler);

    // 3. Start Server
    app.listen(config.port, () => {
      logger.info(`Server started on port ${config.port}`);
      logger.info(`👉 Test URL: http://localhost:${config.port}/api/v1/products`);
    });

  } catch (err) {
    logger.error(`Startup failed: ${err.message}`);
    process.exit(1);
  }
})();