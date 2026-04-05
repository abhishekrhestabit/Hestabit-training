// Centralized Error Handling Middleware
// This catches any error thrown in the app, formats it, and sends a clean response.

const globalErrorHandler = (err, req, res, next) => {
  err.statusCode = err.statusCode || 500;
  err.status = err.status || 'error';

  // Development: Send full stack trace for debugging
  if (process.env.NODE_ENV === 'dev') {
    return res.status(err.statusCode).json({
      success: false,
      status: err.status,
      message: err.message,
      stack: err.stack,
      error: err,
    });
  }

  // Production: Send clean message, hide implementation details
  if (err.isOperational) {
    return res.status(err.statusCode).json({
      success: false,
      status: err.status,
      message: err.message,
    });
  }

  // Programming or other unknown error: Don't leak details to client
  console.error('ERROR 💥', err);
  return res.status(500).json({
    success: false,
    status: 'error',
    message: 'Something went very wrong!',
  });
};

module.exports = globalErrorHandler;