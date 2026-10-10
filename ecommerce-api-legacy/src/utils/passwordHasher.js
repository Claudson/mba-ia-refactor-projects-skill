const crypto = require('crypto');

const SALT_BYTES = 16;
const KEY_LENGTH = 64;

function hashPassword(password) {
    const salt = crypto.randomBytes(SALT_BYTES).toString('hex');
    const hash = crypto.scryptSync(password, salt, KEY_LENGTH).toString('hex');
    return `${salt}:${hash}`;
}

function verifyPassword(password, stored) {
    const [salt, hash] = String(stored).split(':');
    if (!salt || !hash) return false;
    const expected = Buffer.from(hash, 'hex');
    const actual = crypto.scryptSync(password, salt, KEY_LENGTH);
    return expected.length === actual.length && crypto.timingSafeEqual(expected, actual);
}

function generateRandomPassword() {
    return crypto.randomBytes(24).toString('base64url');
}

module.exports = { hashPassword, verifyPassword, generateRandomPassword };
