const productService = require('../services/product.service');
const AppError = require('../utils/AppError');

// Wrap async functions to catch errors automatically (no try-catch clutter)
const catchAsync = (fn) => {
  return (req, res, next) => {
    fn(req, res, next).catch(next);
  };
};

exports.getAllProducts = catchAsync(async (req, res, next) => {
  // Delegate logic to Service
  const products = await productService.findAllProducts(req.query);

  res.status(200).json({
    success: true,
    count: products.length,
    data: products,
  });
});

exports.deleteProduct = catchAsync(async (req, res, next) => {
  await productService.deleteProduct(req.params.id);

  res.status(200).json({
    success: true,
    message: 'Product soft deleted successfully',
  });
});

exports.restoreProduct = catchAsync(async (req, res, next) => {
  const product = await productService.restoreProduct(req.params.id);

  res.status(200).json({
    success: true,
    message: 'Product restored successfully',
    data: product,
  });
});