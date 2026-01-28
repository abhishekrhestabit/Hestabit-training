const path = require('path');
const dotenv = require('dotenv');

const env = process.env.NODE_ENV || 'local';

const envFileMap = {
  local: '.env.local',
  dev: '.env.dev',
  prod: '.env.prod',
};

const envFile = envFileMap[env];

if (!envFile) {
  throw new Error(`Invalid NODE_ENV: ${env}`);
}

dotenv.config({
  path: path.resolve(process.cwd(), envFile),
});

module.exports = {
  env,
  port: process.env.PORT || 3000,
  dbUri: process.env.DB_URI,
  logLevel: process.env.LOG_LEVEL || 'info',
};
