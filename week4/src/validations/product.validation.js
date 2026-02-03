const Joi = require('joi');

/**
 * DAY 4 - Product Validation Schemas
 * Robust validation for all Product-related requests
 */

// MongoDB ObjectId pattern
const objectIdPattern = /^[0-9a-fA-F]{24}$/;

const createProduct = {
  body: Joi.object().keys({
    name: Joi.string()
      .required()
      .trim()
      .min(3)
      .max(100)
      .messages({
        'string.empty': 'Product name is required',
        'string.min': 'Product name must be at least 3 characters',
        'string.max': 'Product name cannot exceed 100 characters',
        'any.required': 'Product name is required',
      }),
  
    price: Joi.number()
      .required()
      .min(0)
      .max(1000000)
      .messages({
        'number.base': 'Price must be a valid number',
        'number.min': 'Price cannot be negative',
        'number.max': 'Price cannot exceed 1,000,000',
        'any.required': 'Price is required',
      }),
    
    category: Joi.string()
      .required()
      .trim()
      .min(2)
      .max(50)
      .messages({
        'string.empty': 'Category is required',
        'any.required': 'Category is required',
      }),
    
    tags: Joi.array()
      .items(Joi.string().trim().max(30))
      .max(10)
      .optional()
      .messages({
        'array.max': 'Cannot have more than 10 tags',
      }),
    
    isFlashSale: Joi.boolean()
      .optional()
      .default(false),
    
    createdBy: Joi.string()
      .pattern(objectIdPattern)
      .optional()
      .messages({
        'string.pattern.base': 'Invalid user ID format',
      }),
  }),
};


const updateProduct = {
  params: Joi.object().keys({
    id: Joi.string()
      .pattern(objectIdPattern)
      .required()
      .messages({
        'string.pattern.base': 'Invalid product ID format',
        'any.required': 'Product ID is required',
      }),
  }),
  body: Joi.object().keys({
    name: Joi.string().trim().min(3).max(100).optional(),
    price: Joi.number().min(0).max(1000000).optional(),
    category: Joi.string().trim().min(2).max(50).optional(),
    tags: Joi.array().items(Joi.string().trim().max(30)).max(10).optional(),
    isFlashSale: Joi.boolean().optional(),
  }).min(1).messages({
    'object.min': 'At least one field must be provided for update',
  }),
};


const getProducts = {
  query: Joi.object().keys({
    // Search
    search: Joi.string().trim().max(100).optional(),
    name: Joi.string().trim().max(100).optional(),
    
    // Filtering
    category: Joi.string().trim().max(50).optional(),
    minPrice: Joi.number().min(0).optional(),
    maxPrice: Joi.number().min(0).optional(),
    tags: Joi.string().trim().optional(), // comma-separated
    
    // Soft delete filter
    includeDeleted: Joi.string().valid('true', 'false').optional(),
    
    // Sorting
    sort: Joi.string().trim().max(100).optional(),
    
    // Field limiting
    fields: Joi.string().trim().max(200).optional(),
    
    // Pagination
    page: Joi.number().integer().min(1).default(1).optional(),
    limit: Joi.number().integer().min(1).max(100).default(10).optional(),
  }),
};


const getProduct = {
  params: Joi.object().keys({
    id: Joi.string()
      .pattern(objectIdPattern)
      .required()
      .messages({
        'string.pattern.base': 'Invalid product ID format',
        'any.required': 'Product ID is required',
      }),
  }),
};


const deleteProduct = {
  params: Joi.object().keys({
    id: Joi.string()
      .pattern(objectIdPattern)
      .required()
      .messages({
        'string.pattern.base': 'Invalid product ID format',
        'any.required': 'Product ID is required',
      }),
  }),
};

module.exports = {
  createProduct,
  updateProduct,
  getProducts,
  getProduct,
  deleteProduct,
};
