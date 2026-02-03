const Joi = require('joi');

/**
 * DAY 4 - User Validation Schemas
 * Robust validation for all User-related requests
 */

// MongoDB ObjectId pattern
const objectIdPattern = /^[0-9a-fA-F]{24}$/;

// Password pattern: min 8 chars, at least 1 letter and 1 number
const passwordPattern = /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d@$!%*#?&]{8,}$/;

// ═══════════════════════════════════════════════════════════════
// CREATE USER (REGISTER) - POST /api/v1/users
// ═══════════════════════════════════════════════════════════════
const createUser = {
  body: Joi.object().keys({
    firstName: Joi.string()
      .required()
      .trim()
      .min(2)
      .max(50)
      .messages({
        'string.empty': 'First name is required',
        'string.min': 'First name must be at least 2 characters',
        'string.max': 'First name cannot exceed 50 characters',
        'any.required': 'First name is required',
      }),
    
    lastName: Joi.string()
      .required()
      .trim()
      .min(2)
      .max(50)
      .messages({
        'string.empty': 'Last name is required',
        'string.min': 'Last name must be at least 2 characters',
        'string.max': 'Last name cannot exceed 50 characters',
        'any.required': 'Last name is required',
      }),
    
    email: Joi.string()
      .required()
      .trim()
      .lowercase()
      .email()
      .messages({
        'string.empty': 'Email is required',
        'string.email': 'Please provide a valid email address',
        'any.required': 'Email is required',
      }),
    
    password: Joi.string()
      .required()
      .min(8)
      .max(128)
      .pattern(passwordPattern)
      .messages({
        'string.empty': 'Password is required',
        'string.min': 'Password must be at least 8 characters',
        'string.max': 'Password cannot exceed 128 characters',
        'string.pattern.base': 'Password must contain at least one letter and one number',
        'any.required': 'Password is required',
      }),
    
    role: Joi.string()
      .valid('user', 'admin')
      .default('user')
      .optional()
      .messages({
        'any.only': 'Role must be either user or admin',
      }),
    
    status: Joi.string()
      .valid('active', 'inactive', 'suspended')
      .default('active')
      .optional()
      .messages({
        'any.only': 'Status must be active, inactive, or suspended',
      }),
  }),
};

// ═══════════════════════════════════════════════════════════════
// UPDATE USER - PATCH /api/v1/users/:id
// ═══════════════════════════════════════════════════════════════
const updateUser = {
  params: Joi.object().keys({
    id: Joi.string()
      .pattern(objectIdPattern)
      .required()
      .messages({
        'string.pattern.base': 'Invalid user ID format',
        'any.required': 'User ID is required',
      }),
  }),
  body: Joi.object().keys({
    firstName: Joi.string().trim().min(2).max(50).optional(),
    lastName: Joi.string().trim().min(2).max(50).optional(),
    email: Joi.string().trim().lowercase().email().optional(),
    status: Joi.string().valid('active', 'inactive', 'suspended').optional(),
    role: Joi.string().valid('user', 'admin').optional(),
  }).min(1).messages({
    'object.min': 'At least one field must be provided for update',
  }),
};

// ═══════════════════════════════════════════════════════════════
// GET USERS - GET /api/v1/users
// ═══════════════════════════════════════════════════════════════
const getUsers = {
  query: Joi.object().keys({
    // Search
    search: Joi.string().trim().max(100).optional(),
    email: Joi.string().trim().email().optional(),
    
    // Filtering
    status: Joi.string().valid('active', 'inactive', 'suspended').optional(),
    role: Joi.string().valid('user', 'admin').optional(),
    
    // Sorting
    sort: Joi.string().trim().max(100).optional(),
    
    // Pagination
    page: Joi.number().integer().min(1).default(1).optional(),
    limit: Joi.number().integer().min(1).max(100).default(10).optional(),
  }),
};

// ═══════════════════════════════════════════════════════════════
// GET SINGLE USER - GET /api/v1/users/:id
// ═══════════════════════════════════════════════════════════════
const getUser = {
  params: Joi.object().keys({
    id: Joi.string()
      .pattern(objectIdPattern)
      .required()
      .messages({
        'string.pattern.base': 'Invalid user ID format',
        'any.required': 'User ID is required',
      }),
  }),
};

// ═══════════════════════════════════════════════════════════════
// DELETE USER - DELETE /api/v1/users/:id
// ═══════════════════════════════════════════════════════════════
const deleteUser = {
  params: Joi.object().keys({
    id: Joi.string()
      .pattern(objectIdPattern)
      .required()
      .messages({
        'string.pattern.base': 'Invalid user ID format',
        'any.required': 'User ID is required',
      }),
  }),
};

// ═══════════════════════════════════════════════════════════════
// LOGIN - POST /api/v1/auth/login
// ═══════════════════════════════════════════════════════════════
const loginUser = {
  body: Joi.object().keys({
    email: Joi.string()
      .required()
      .trim()
      .lowercase()
      .email()
      .messages({
        'string.empty': 'Email is required',
        'string.email': 'Please provide a valid email address',
        'any.required': 'Email is required',
      }),
    
    password: Joi.string()
      .required()
      .messages({
        'string.empty': 'Password is required',
        'any.required': 'Password is required',
      }),
  }),
};

module.exports = {
  createUser,
  updateUser,
  getUsers,
  getUser,
  deleteUser,
  loginUser,
};
