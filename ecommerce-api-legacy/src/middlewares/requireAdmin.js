const crypto = require('crypto');
const { ForbiddenError, UnauthorizedError } = require('../errors');

const digest = (value) => crypto.createHash('sha256').update(String(value)).digest();

function createRequireAdmin(adminToken) {
    const expected = adminToken ? digest(adminToken) : null;

    return function requireAdmin(req, res, next) {
        if (!expected) return next(new ForbiddenError('Endpoint administrativo desabilitado'));
        const provided = req.get('X-Admin-Token');
        if (!provided || !crypto.timingSafeEqual(digest(provided), expected)) return next(new UnauthorizedError());
        return next();
    };
}

module.exports = { createRequireAdmin };
