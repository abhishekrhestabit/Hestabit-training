const { createLogger, format, transports } = require('winston');
const config = require('../config');

const logger = createLogger({
  level: config.logLevel,
  format: format.combine(
    format.timestamp(),
    format.printf(
      ({ timestamp, level, message }) =>
        `[${timestamp}] ${level.toUpperCase()}: ${message}`
    )
  ),
  transports: [
    new transports.Console(),
    new transports.File({ filename: 'src/logs/app.log' }),
  ],
});

module.exports = logger;
