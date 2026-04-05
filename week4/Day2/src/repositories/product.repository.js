const Product = require('../models/Products');

class ProductRepository {
    
    async create(productData) {
        const product = new Product(productData);
        return await product.save();
    }

    async findById(id) {
        // Populate: Automatically replaces the 'createdBy' ID with the actual User document
        return await Product.findById(id).populate('createdBy', 'firstName lastName email');
    }

    async findPaginated(page = 1, limit = 10) {
        const skip = (page - 1) * limit;
        return await Product.find()
            .skip(skip)
            .limit(limit)
            .populate('createdBy', 'firstName');
    }

    // Example of using a cursor-based approach (often faster for infinite scroll)
    async findByCursor(cursorId, limit = 10) {
        let query = {};
        if (cursorId) {
            // Fetch records with ID greater than cursor
            query = { _id: { $gt: cursorId } };
        }
        return await Product.find(query).limit(limit).sort({ _id: 1 });
    }
}

module.exports = new ProductRepository();