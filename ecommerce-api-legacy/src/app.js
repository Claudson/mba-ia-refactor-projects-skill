const config = require('./config');
const { createLogger } = require('./utils/logger');
const { createApp } = require('./createApp');

const logger = createLogger(config.logLevel);

createApp(config, logger)
    .then(({ app }) => {
        app.listen(config.port, () => logger.info(`LMS API rodando na porta ${config.port}`));
    })
    .catch((err) => {
        logger.error('Falha ao iniciar a aplicação:', err);
        process.exit(1);
    });
