const config = require('./config');
const logger = require('./utils/logger');
const connectDB = require('./loaders/db');
const loadApp = require('./loaders/app');

(async () => {
  try {
    await connectDB();

    const app = await loadApp();

    app.listen(config.port, () => {
      logger.info(`Server started on port ${config.port}`);
    });
  } catch (err) {
    logger.error(`Startup failed: ${err.message}`);
    process.exit(1);
  }
})();
