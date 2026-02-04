const { Queue } = require('bullmq');
const IORedis = require('ioredis');

// Redis connection (use local Redis or fallback to in-memory)
const connection = new IORedis({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  maxRetriesPerRequest: null,
});

// Create email queue
const emailQueue = new Queue('email-notifications', {
  connection,
  defaultJobOptions: {
    attempts: 3, // Retry 3 times
    backoff: {
      type: 'exponential',
      delay: 1000, // Start with 1 second
    },
    removeOnComplete: 100, // Keep last 100 completed jobs
    removeOnFail: 50, // Keep last 50 failed jobs
  },
});

// Queue event listeners
emailQueue.on('error', (error) => {
  console.error('Queue error:', error);
});

module.exports = emailQueue;