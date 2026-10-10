const { AppError } = require('../errors');

function createErrorHandler(logger) {
    // O Express identifica o middleware de erro pela aridade (4 parâmetros).
    // eslint-disable-next-line no-unused-vars
    return function errorHandler(err, req, res, next) {
        if (err instanceof AppError) return res.status(err.status).send(err.message);
        // Erros do express.json() (JSON malformado, payload grande) já trazem um status 4xx.
        if (err.status >= 400 && err.status < 500) return res.status(err.status).send('Bad Request');

        logger.error(`Erro não tratado em ${req.method} ${req.originalUrl}:`, err);
        return res.status(500).send('Erro DB');
    };
}

module.exports = { createErrorHandler };
