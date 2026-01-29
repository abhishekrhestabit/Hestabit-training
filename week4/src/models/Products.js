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
    }
}, { timestamps: true });

// TTL Index: Documents expire after the time specified in 'expireAt' field
// expireAfterSeconds: 0 means it expires exactly at the time in the field
productSchema.index({ expireAt: 1 }, { expireAfterSeconds: 0 });

module.exports = mongoose.model('Product', productSchema);