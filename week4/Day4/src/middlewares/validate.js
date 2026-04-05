const Joi = require('joi');
const AppError = require('../utils/AppError');

/**
 * DAY 4 - Validation Middleware
 * Validates request body, query, and params against Joi schemas
 */
const validate = (schema) => {
  return (req, res, next) => {
    // Determine which parts of the request to validate
    const toValidate = {};
    
    if (schema.body && req.body) {
      toValidate.body = req.body;
    }
    if (schema.query && req.query) {
      toValidate.query = req.query;
    }
    if (schema.params && req.params) {
      toValidate.params = req.params;
    }

    // Build the validation schema
    const validationSchema = Joi.object({
      body: schema.body || Joi.any(),
      query: schema.query || Joi.any(),
      params: schema.params || Joi.any(),
    });

    // Validate
    const { error, value } = validationSchema.validate(toValidate, {
      abortEarly: false, // Return all errors, not just the first
      stripUnknown: true, // Remove unknown keys
      errors: { label: 'key' },
    });

    if (error) {
      const errorMessage = error.details
        .map((detail) => detail.message)
        .join(', ');
      return next(new AppError(errorMessage, 400));
    }

    // Replace request data with validated data
    if (value.body) req.body = value.body;
    if (value.query) req.query = value.query;
    if (value.params) req.params = value.params;

    next();
  };
};

module.exports = validate;
