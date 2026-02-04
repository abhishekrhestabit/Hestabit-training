const productService = require('../services/product.service');
const AppError = require('../utils/AppError');

// Wrap async functions to catch errors automatically (no try-catch clutter)
const catchAsync = (fn) => {
  return (req, res, next) => {
    fn(req, res, next).catch(next);
  };
};

exports.getAllProducts = catchAsync(async (req, res, next) => {
  const products = await productService.findAllProducts(req.query);

  res.status(200).json({
    success: true,
    count: products.length,
    data: products,
  });
});


exports.getProduct = catchAsync(async (req, res, next) => {
  const product = await productService.findProductById(req.params.id);

  if (!product) {
    return next(new AppError('No product found with that ID', 404));
  }

  res.status(200).json({
    success: true,
    data: product,
  });
});


exports.createProduct = async (productData) => {
  const product = await Product.create(productData);
  
  // Add background job for email notification
  await emailQueue.add('product-created', {
    type: 'product-created',
    data: {
      productName: product.name,
      productPrice: product.price,
      productId: product._id,
      createdBy: product.createdBy,
    },
  });
  
  return product;
};

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