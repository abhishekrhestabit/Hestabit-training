# Deployment Notes - Day 5

## Prerequisites

- Node.js v18+
- MongoDB (running)
- Redis v6+
- PM2 (optional, for production)

## Environment Setup

Update `.env.dev`:

NODE_ENV=local
PORT=3000
DB_URI=mongodb://localhost:27017/week4
LOG_LEVEL=debug
REDIS_HOST=localhost
REDIS_PORT=6379



# Start Redis
redis-server

# Start application (worker runs in same process)
npm start
# or with auto-reload
npm run dev
# we do
NODE_ENV=dev node src/index.js

## Endpoints

Base URL: `http://localhost:3000`

### Products API

- **GET** `/api/v1/products` - List products (with pagination)
- **GET** `/api/v1/products/:id` - Get single product (populates user)
- **POST** `/api/v1/products` - Create product (triggers background email job)
- **DELETE** `/api/v1/products/:id` - Soft delete product
- **PATCH** `/api/v1/products/:id` - Restore the product

### Request Headers

All responses include `X-Request-ID` for distributed tracing.


curl -v http://localhost:3000/api/v1/products


## Redis Configuration

### Background Job Queue

Redis powers the BullMQ job queue for background tasks.

**Queue:** email-notifications  
**Jobs:** product-created, product-deleted, weekly-report

**Features:**
- Retry: 3 attempts with exponential backoff
- Concurrency: 5 jobs at once
- Retention: Last 100 completed, 50 failed

### Testing Background Jobs

# 1. Create a product (triggers email job)
curl -X POST http://localhost:3000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "price": 99, "category": "Tech", "createdBy": "USER_ID"}'

# 2. Watch worker logs
tail -f logs/combined.log | grep "email job"

# 3. Check Redis queue
redis-cli
> LLEN bull:email-notifications:wait
> LLEN bull:email-notifications:completed

### Troubleshooting Redis

# Check Redis is running
redis-cli ping
Should return: PONG

# View all queue keys
redis-cli KEYS "bull:*"

# Clear failed jobs (if needed)
redis-cli DEL bull:email-notifications:failed

