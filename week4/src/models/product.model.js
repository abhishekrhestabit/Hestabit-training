const mongoose = require('mongoose');

const productSchema = new mongoose.Schema(
  {
    name: {
      type: String,
      required: [true, 'A product must have a name'],
      trim: true,
    },
    price: {
      type: Number,
      required: [true, 'A product must have a price'],
    },
    category: {
      type: String,
      required: [true, 'A product must have a category'],
    },
    tags: [String],
    rating: {
      type: Number,
      default: 4.5,
    },
    // Soft Delete Fields
    isDeleted: {
      type: Boolean,
      default: false,
      select: false, // Hide this field by default in queries
    },
    deletedAt: {
      type: Date,
      default: null,
    },
  },
  {
    timestamps: true, // Adds createdAt and updatedAt
    toJSON: { virtuals: true },
    toObject: { virtuals: true },
  }
);

// FIX: Switched to 'async function' and removed 'next'.
// Mongoose will simply await this function.
productSchema.pre(/^find/, async function () {
  // 'this' refers to the current query
  
  // Check if 'includeDeleted' was manually set on the query options
  if (this.getOptions().includeDeleted !== true) {
    // If not asking for deleted items, filter them out
    this.find({ isDeleted: { $ne: true } });
  }
});

const Product = mongoose.model('Product', productSchema);

module.exports = Product;