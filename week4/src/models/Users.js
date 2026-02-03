const mongoose = require('mongoose');
const crypto = require('crypto'); // Built-in node module for hashing

const userSchema = new mongoose.Schema({
    firstName: {
        type: String,
        required: true,
        trim: true
    },
    lastName: {
        type: String,
        required: true,
        trim: true
    },
    email: {
        type: String,
        required: true,
        unique: true,
        lowercase: true,
        // sparse index: only index documents that have this field
        sparse: true 
    },
    password: {
        type: String,
        required: true,
        minlength: 8
    },
    status: {
        type: String,
        enum: ['active', 'inactive', 'suspended'],
        default: 'active'
    },
    role: {
        type: String,
        enum: ['user', 'admin'],
        default: 'user'
    }
}, {
    timestamps: true, // Automatically manages createdAt and updatedAt
    toJSON: { virtuals: true }, // Ensure virtuals show up in JSON output
    toObject: { virtuals: true }
});

// 1. Compound Index: Optimizes queries filtering by status AND sorting by date
// Note: 1 means ascending, -1 means descending
userSchema.index({ status: 1, createdAt: -1 });

// 2. Virtual Field: fullName
// A property that is not stored in MongoDB but computed when retrieved
userSchema.virtual('fullName').get(function() {
    return `${this.firstName} ${this.lastName}`;
});

// 3. Pre-save Hook: Hash password
// Note: 'next' is a function that tells Mongoose to proceed to the actual save
userSchema.pre('save', async function(next) {
    // Only hash if password was modified (prevents rehashing on updates)
    if (!this.isModified('password')) return next();

    // Simple hashing simulation (In production, use bcrypt)
    this.password = crypto.createHash('sha256').update(this.password).digest('hex');
    
    next();
});

module.exports = mongoose.model('Users', userSchema);