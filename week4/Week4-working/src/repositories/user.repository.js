const User = require('../models/Users');

class UserRepository {
    
    // Create a new user
    async create(userData) {
        try {
            const user = new User(userData);
            return await user.save();
        } catch (error) {
            throw error;
        }
    }

    // Find by ID
    async findById(id) {
        return await User.findById(id);
    }

    // Pagination: Cursor vs Offset
    // Here we use Offset (Skip/Limit) for simplicity
    async findPaginated(page = 1, limit = 10) {
        const skip = (page - 1) * limit;
        
        const users = await User.find()
            .sort({ createdAt: -1 }) // Sort by newest first
            .skip(skip)
            .limit(limit);
            
        const total = await User.countDocuments();
        
        return {
            data: users,
            meta: {
                total,
                page,
                pages: Math.ceil(total / limit)
            }
        };
    }

    // Update user
    async update(id, updateData) {
        return await User.findByIdAndUpdate(
            id, 
            updateData, 
            { new: true, runValidators: true } // Return updated doc & run validation
        );
    }

    // Delete user
    async delete(id) {
        return await User.findByIdAndDelete(id);
    }
}

module.exports = new UserRepository();