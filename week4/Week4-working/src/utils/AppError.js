// A custom Error class to handle operational errors (errors we can predict)
// "Operational errors" are things like "User not found" or "Invalid Input", 
// distinct from bugs like "undefined variable".

class AppError extends Error {
  constructor(message, statusCode) {
    super(message);
    this.statusCode = statusCode;
    // 4xx = Fail (Client error), 5xx = Error (Server error)
    this.status = `${statusCode}`.startsWith('4') ? 'fail' : 'error';
    this.isOperational = true; // Marks this as a trusted error we created

    Error.captureStackTrace(this, this.constructor);
  }
}

module.exports = AppError;