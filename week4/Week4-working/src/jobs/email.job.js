const logger = require('../utils/logger');

/**
 * DAY 5 - Email Job Processor
 * Handles background email notifications
 */
class EmailJob {
  /**
   * Process email job
   * @param {Object} job - BullMQ job object
   */
  static async process(job) {
    const { type, data } = job.data;
    
    logger.info({
      message: `Processing email job: ${type}`,
      jobId: job.id,
      attempt: job.attemptsMade,
      data,
    });

    try {
      switch (type) {
        case 'product-created':
          await this.sendProductCreatedEmail(data);
          break;
        case 'product-deleted':
          await this.sendProductDeletedEmail(data);
          break;
        case 'weekly-report':
          await this.sendWeeklyReport(data);
          break;
        default:
          throw new Error(`Unknown email type: ${type}`);
      }

      logger.info({
        message: `Email job completed: ${type}`,
        jobId: job.id,
      });

      return { success: true, type };
    } catch (error) {
      logger.error({
        message: `Email job failed: ${type}`,
        jobId: job.id,
        error: error.message,
        stack: error.stack,
      });
      throw error; // Will trigger retry
    }
  }

  /**
   * Send product created notification
   */
  static async sendProductCreatedEmail(data) {
    const { productName, productPrice, createdBy } = data;
    
    // Simulate email sending (replace with real email service)
    await this.simulateEmailSend();
    
    logger.info({
      message: 'Product created email sent',
      product: productName,
      price: productPrice,
      recipient: createdBy,
    });
  }

  /**
   * Send product deleted notification
   */
  static async sendProductDeletedEmail(data) {
    const { productName, deletedBy } = data;
    
    await this.simulateEmailSend();
    
    logger.info({
      message: 'Product deleted email sent',
      product: productName,
      recipient: deletedBy,
    });
  }

  /**
   * Send weekly report
   */
  static async sendWeeklyReport(data) {
    const { recipient, totalProducts, totalRevenue } = data;
    
    await this.simulateEmailSend();
    
    logger.info({
      message: 'Weekly report email sent',
      recipient,
      stats: { totalProducts, totalRevenue },
    });
  }

  /**
   * Simulate email sending (2 second delay)
   * Replace with real email service: SendGrid, AWS SES, Nodemailer, etc.
   */
  static async simulateEmailSend() {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve();
      }, 2000); // 2 second delay
    });
  }
}

module.exports = EmailJob;