const fs = require('fs');
const path = require('path');

const ENV_FILE = path.resolve(__dirname, '..', '..', '.env');
if (typeof process.loadEnvFile === 'function' && fs.existsSync(ENV_FILE)) {
    process.loadEnvFile(ENV_FILE);
}

module.exports = Object.freeze({
    port: Number(process.env.PORT) || 3000,
    databasePath: process.env.DATABASE_PATH || ':memory:',
    // Vazio → gateway roda em modo simulado.
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    // Ausente → endpoints administrativos respondem 403.
    adminToken: process.env.ADMIN_TOKEN || '',
    logLevel: process.env.LOG_LEVEL || 'info',
});
