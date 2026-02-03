const express = require('express');
const config = require('./config');
const logger = require('./utils/logger');
const connectDB = require('./loaders/db'); // Keeping your existing DB loader

// --- DAY 3 IMPORTS ---
const productRouter = require('./routes/product.routes');
const globalErrorHandler = require('./middlewares/error.middleware');
const AppError = require('./utils/AppError');

(async () => {
  try {
    // 1. Establish Database Connection (Using your loader)
    await connectDB();
    logger.info('Database loaded successfully');

    // 2. Initialize Express App directly here (Instead of loadApp)
    const app = express();

    // --- MIDDLEWARE ---
    app.use(express.json());

    // --- ROUTES (DAY 3 LOGIC) ---
    app.use('/api/v1/products', productRouter);

    // --- 404 HANDLER ---
    // FIX: Use regex /(.*)/ instead of '*' to avoid "Missing parameter name" error
    app.all(/(.*)/, (req, res, next) => {
      next(new AppError(`Can't find ${req.originalUrl} on this server!`, 404));
    });

    // --- GLOBAL ERROR HANDLER ---
    app.use(globalErrorHandler);

    // 3. Start Server
    app.listen(config.port, () => {
      logger.info(`Server started on port ${config.port}`);
      logger.info(`Test Query: http://localhost:${config.port}/api/v1/products?price[gte]=100&sort=-price`);
    });

  } catch (err) {
    logger.error(`Startup failed: ${err.message}`);
    process.exit(1);
  }
})();