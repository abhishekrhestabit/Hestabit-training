const mongoose = require('mongoose');
const UserRepository = require('./repositories/user.repository');
const ProductRepository = require('./repositories/product.repository');

// Connection String
const MONGO_URI = 'mongodb+srv://abhishekrhestabit_db_user:guddi%40975@cluster0.rl4k2qm.mongodb.net/week4mongo'; 

const seedDatabase = async () => {
    try {
        // 1. Connect
        await mongoose.connect(MONGO_URI);
        console.log('Connected to MongoDB');

        // 2. Clear existing data
        await mongoose.connection.collection('users').deleteMany({});
        await mongoose.connection.collection('products').deleteMany({});
        console.log('Cleared existing data');

        // 3. Create 2 Users Manually
        console.log('... Creating Users');

        const user1 = await UserRepository.create({
            firstName: 'Abhishek',
            lastName: 'Rai',
            email: 'abhishek@example.com',
            password: 'password123',
            status: 'active',
            role: 'admin'
        });

        const user2 = await UserRepository.create({
            firstName: 'Pranshu',
            lastName: 'Kothari',
            email: 'pranshu@example.com',
            password: 'password123',
            status: 'inactive',
            role: 'user'
        });

        console.log(`Created 2 users: ${user1.email}, ${user2.email}`);

        // 4. Create 3 Products Manually (Linked to users)
        console.log('... Creating Products');

        // Product 1: Created by Alice
        await ProductRepository.create({
            name: 'Gaming Laptop',
            price: 1200,
            category: 'Electronics',
            createdBy: user1._id, 
            isFlashSale: true, 
            expireAt: new Date(Date.now() + 1000 * 60 * 60) // Expires in 1 hour
        });

        // Product 2: Created by Bob
        await ProductRepository.create({
            name: 'Wireless Mouse',
            price: 25,
            category: 'Electronics',
            createdBy: user2._id, 
            isFlashSale: false,
            expireAt: null
        });

        // Product 3: Created by Alice
        await ProductRepository.create({
            name: 'HD Monitor',
            price: 300,
            category: 'Electronics',
            createdBy: user1._id, 
            isFlashSale: false,
            expireAt: null
        });

        console.log('Created 3 products');

        console.log('Seeding complete.');
        process.exit(0);

    } catch (error) {
        console.error('Seeding failed:', error);
        process.exit(1);
    }
};

seedDatabase();