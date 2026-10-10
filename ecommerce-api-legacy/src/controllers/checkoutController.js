const { ValidationError, NotFoundError } = require('../errors');

const isOptionalString = (value) => value === undefined || value === null || typeof value === 'string';

function parseCheckoutInput(body) {
    const { usr, eml, pwd, c_id: courseId, card } = body || {};

    if (!usr || !eml || !courseId || !card) throw new ValidationError('Bad Request');
    if (typeof usr !== 'string' || typeof eml !== 'string' || typeof card !== 'string' || !isOptionalString(pwd)) {
        throw new ValidationError('Bad Request');
    }
    if (typeof courseId !== 'number' && typeof courseId !== 'string') throw new NotFoundError('Curso não encontrado');

    return { name: usr, email: eml, password: pwd, courseId, cardNumber: card };
}

function createCheckoutController({ checkoutService }) {
    return Object.freeze({
        async checkout(body) {
            const { enrollmentId } = await checkoutService.checkout(parseCheckoutInput(body));
            return { msg: 'Sucesso', enrollment_id: enrollmentId };
        },
    });
}

module.exports = { createCheckoutController };
