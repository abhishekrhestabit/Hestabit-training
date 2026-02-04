const Product = require('../models/Products');
const AppError = require('../utils/AppError');
const emailQueue = require('../queues/email.queue');
/**
 * Advanced Query Engine Logic
 * Handles filtering, sorting, field limiting, pagination, and search.
 */
exports.findAllProducts = async (queryObj) => {
  try {
    // 1. FILTERING
    const queryCopy = { ...queryObj };
    const excludedFields = ['page', 'sort', 'limit', 'fields', 'search', 'includeDeleted'];
    excludedFields.forEach((el) => delete queryCopy[el]);

    // Advanced Filtering: minPrice/maxPrice -> $gte/$lte
    let queryStr = JSON.stringify(queryCopy);
    queryStr = queryStr.replace(/\b(gte|gt|lte|lt)\b/g, (match) => `$${match}`);
    let filter = JSON.parse(queryStr);

    // 2. SEARCH (Partial Text Match)
    if (queryObj.search) {
      filter.name = { $regex: queryObj.search, $options: 'i' };
    }

    // 3. TAGS FILTER
    if (queryObj.tags) {
      const tagsArray = queryObj.tags.split(',');
      filter.tags = { $in: tagsArray };
    }

    // Initialize Query
    // The model middleware automatically adds { isDeleted: false }
    let query = Product.find(filter);

    if (queryObj.includeDeleted === 'true') {
      query.setOptions({ includeDeleted: true });
    }

    // 4. SORTING
    if (queryObj.sort) {
      const sortBy = queryObj.sort.split(',').join(' ');
      query = query.sort(sortBy);
    } else {
      query = query.sort('-createdAt');
    }

    // 5. FIELD LIMITING
    if (queryObj.fields) {
      const fields = queryObj.fields.split(',').join(' ');
      query = query.select(fields);
    } else {
      query = query.select('-__v');
    }

    // 6. PAGINATION
    const page = queryObj.page * 1 || 1;
    const limit = queryObj.limit * 1 || 100;
    const skip = (page - 1) * limit;

    query = query.skip(skip).limit(limit);

    // EXECUTE QUERY
    const products = await query;
    return products;

  } catch (error) {
    // DEBUG: Log the actual error to the console
    console.error('❌ Service Layer Error:', error);
    
    // Throw the specific error message instead of a generic one
    throw new AppError(`Error Querying Products: ${error.message}`, 500);
  }
};

exports.deleteProduct = async (id) => {
  const product = await Product.findByIdAndUpdate(
    id,
    { isDeleted: true, deletedAt: Date.now() },
    { new: true, runValidators: true }
  );

  if (!product) {
    throw new AppError('No product found with that ID', 404);
  }

  return product;
};

exports.restoreProduct = async (id) => {
  const product = await Product.findByIdAndUpdate(
    id,
    { isDeleted: false, deletedAt: null },
    { new: true, runValidators: true }
  ).setOptions({ includeDeleted: true });

  if (!product) {
    throw new AppError('No product found to restore', 404);
  }
  return product;
};

// ═══════════════════════════════════════════════════════════════
// FIND PRODUCT BY ID
// ═══════════════════════════════════════════════════════════════
exports.findProductById = async (id) => {
  const product = await Product.findById(id).populate('createdBy', 'firstName lastName email');
  return product;
};

// ═══════════════════════════════════════════════════════════════
// CREATE PRODUCT
// ═══════════════════════════════════════════════════════════════
exports.createProduct = async (productData) => {
  const product = await Product.create(productData);
  return product;
};