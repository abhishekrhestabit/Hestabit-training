const dotenv = require('dotenv');
const connectDB = require('./loaders/db');
const setupApp = require('./loaders/app');
const goalRoutes = require('./main/main');

// 1. Load Config
dotenv.config();

// 2. Connect to Database
connectDB();

// 3. Initialize Express App
const app = setupApp();

// Health checks
// Simple Health Check Endpoint
app.get('/health', (req, res) => {
  res.status(200).send('OK');
});
// 4. Mount the Logic (Routes)
// All routes in main.js will be prefixed with /api/goals
app.use('/api/goals', goalRoutes);

// 5. Start Server
const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
});