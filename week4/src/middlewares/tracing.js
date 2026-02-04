const { v4: uuidv4 } = require('uuid');

/**
 * DAY 5 - Request Tracing Middleware
 * Generates unique request ID for tracking requests across the application
 */
const requestTracing = (req, res, next) => {
  // Generate unique request ID or use existing from header
  const requestId = req.headers['x-request-id'] || uuidv4();
  
  // Attach to request object
  req.id = requestId;
  
  // Add to response headers for client tracking
  res.setHeader('X-Request-ID', requestId);
  
  // Log request start
  const startTime = Date.now();
  
  // Log when response finishes
  res.on('finish', () => {
    const duration = Date.now() - startTime;
    const logger = require('../utils/logger');
    
    logger.info({
      requestId,
      method: req.method,
      url: req.originalUrl,
      statusCode: res.statusCode,
      duration: `${duration}ms`,
      ip: req.ip,
      userAgent: req.headers['user-agent'],
    });
  });
  
  next();
};

module.exports = requestTracing;