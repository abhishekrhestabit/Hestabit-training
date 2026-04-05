const express = require('express');
const productController = require('../controllers/product.controller');

// --- DAY 4 IMPORTS ---
const validate = require('../middlewares/validate');
const { 
  createProduct, 
  getProducts, 
  getProduct, 
  deleteProduct 
} = require('../validations/product.validation');

const router = express.Router();


router
  .route('/')
  // GET /api/v1/products - Get all products with filters
  .get(validate(getProducts), productController.getAllProducts)
  // POST /api/v1/products - Create a new product
  .post(validate(createProduct), productController.createProduct);

router
  .route('/:id')
  // GET /api/v1/products/:id - Get single product
  .get(validate(getProduct), productController.getProduct)
  // DELETE /api/v1/products/:id - Soft delete product
  .delete(validate(deleteProduct), productController.deleteProduct)
  // PATCH /api/v1/products/:id - Restore deleted product
  .patch(validate(getProduct), productController.restoreProduct);

module.exports = router;