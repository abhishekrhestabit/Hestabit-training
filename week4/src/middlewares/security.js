const helmet = require('helmet');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const hpp = require('hpp');

/**
 * DAY 4 - Security Middleware Setup
 * Configures all security-related middleware for the Express app
 */
const setupSecurity = (app) => {
  
  
  // Helmet helps secure Express apps by setting various HTTP headers.
  // It prevents common attacks like clickjacking, XSS, etc.
  app.use(helmet());
  

  // Controls which domains can access your API
  const corsOptions = {
    origin: process.env.CORS_ORIGIN || '*', // In production, set specific domains
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization'],
    credentials: true,
    maxAge: 86400, // 24 hours
  };
  app.use(cors(corsOptions));

  
  // Limits requests from the same IP address
  const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // Limit each IP to 100 requests per windowMs
    message: {
      success: false,
      message: 'Too many requests from this IP, please try again after 15 minutes',
      code: 429,
    },
    standardHeaders: true, // Return rate limit info in headers
    legacyHeaders: false,
  });
  app.use('/api', limiter);

  
  // Prevents parameter pollution attacks like ?sort=price&sort=name
  app.use(hpp({
    whitelist: ['price', 'category', 'rating', 'tags'],
  }));

  
  // Manual sanitization middleware (Express 5 compatible)
  app.use((req, res, next) => {
    // Sanitize req.body
    if (req.body) {
      req.body = sanitizeObject(req.body);
    }
    // Sanitize req.params
    if (req.params) {
      req.params = sanitizeObject(req.params);
    }
    next();
  });

  
  // Manual XSS sanitization (Express 5 compatible)
  app.use((req, res, next) => {
    if (req.body) {
      req.body = sanitizeXSS(req.body);
    }
    next();
  });
};

/**
 * Sanitize object to prevent NoSQL injection
 * Removes dangerous MongoDB operators like $gt, $lt, $ne, etc.
 */
function sanitizeObject(obj) {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeObject(item));
  }

  const sanitized = {};
  for (const key of Object.keys(obj)) {
    // Remove keys starting with $ (MongoDB operators)
    if (key.startsWith('$')) {
      continue;
    }
    // Recursively sanitize nested objects
    sanitized[key] = sanitizeObject(obj[key]);
  }
  return sanitized;
}

/**
 * Sanitize strings to prevent XSS attacks
 * Escapes HTML special characters
 */
function sanitizeXSS(obj) {
  if (typeof obj === 'string') {
    return obj
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;')
      .replace(/\//g, '&#x2F;');
  }

  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeXSS(item));
  }

  const sanitized = {};
  for (const key of Object.keys(obj)) {
    sanitized[key] = sanitizeXSS(obj[key]);
  }
  return sanitized;
}

module.exports = setupSecurity;
