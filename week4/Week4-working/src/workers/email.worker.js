const { Worker } = require('bullmq');
const IORedis = require('ioredis');
const EmailJob = require('../jobs/email.job');
const logger = require('../utils/logger');

// Redis connection
const connection = new IORedis({
  host: process.env.REDIS_HOST || 'localhost',
  port: process.env.REDIS_PORT || 6379,
  maxRetriesPerRequest: null,
});

// Create worker
const emailWorker = new Worker(
  'email-notifications',
  async (job) => {
    return await EmailJob.process(job);
  },
  {
    connection,
    concurrency: 5, // Process 5 jobs concurrently
  }
);

// Worker event listeners
emailWorker.on('completed', (job, result) => {
  logger.info({
    message: 'Job completed',
    jobId: job.id,
    result,
  });
});

emailWorker.on('failed', (job, error) => {
  logger.error({
    message: 'Job failed',
    jobId: job?.id,
    error: error.message,
    attempts: job?.attemptsMade,
  });
});

emailWorker.on('error', (error) => {
  logger.error({
    message: 'Worker error',
    error: error.message,
  });
});

logger.info('Email worker started and listening for jobs...');

module.exports = emailWorker;