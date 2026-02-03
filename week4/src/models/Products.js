const mongoose = require('mongoose');

const productSchema = new mongoose.Schema({
    name: {
        type: String,
        required: true
    },
    price: {
        type: Number,
        required: true,
        min: 0
    },
    category: {
        type: String,
        index: true // Simple single field index
    },
    // Referenced Schema: Points to the User collection
    createdBy: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true
    },
    isFlashSale: {
        type: Boolean,
        default: false
    },
    expireAt: {
        type: Date,
        default: null
    },
    // Day 3: Soft Delete Fields
    isDeleted: {
        type: Boolean,
        default: false
    },
    deletedAt: {
        type: Date,
        default: null
    },
    // Day 3: Tags for filtering
    tags: {
        type: [String],
        default: []
    }
}, { timestamps: true });

// TTL Index: Documents expire after the time specified in 'expireAt' field
// expireAfterSeconds: 0 means it expires exactly at the time in the field
productSchema.index({ expireAt: 1 }, { expireAfterSeconds: 0 });

// Day 3: Compound Index for performance (status-like field + timestamp)
productSchema.index({ isDeleted: 1, createdAt: -1 });

// Day 3: Query Middleware - Automatically exclude soft-deleted products
productSchema.pre(/^find/, function() {
  // Only apply filter if includeDeleted option is not set
  if (!this.getOptions().includeDeleted) {
    this.where({ isDeleted: { $ne: true } });
  }
});

module.exports = mongoose.model('Product', productSchema);