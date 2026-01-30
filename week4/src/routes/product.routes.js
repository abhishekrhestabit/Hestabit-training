const express = require('express');
const productController = require('../controllers/product.controller');

const router = express.Router();

// Define routes for /api/v1/products

router
  .route('/')
  .get(productController.getAllProducts); // Maps GET / to getAllProducts

router
  .route('/:id')
  .delete(productController.deleteProduct) // Maps DELETE /:id to deleteProduct
  .patch(productController.restoreProduct); // Maps PATCH /:id to restoreProduct (if you added restore logic)

module.exports = router;