const PAYMENT_STATUS = Object.freeze({ PAID: 'PAID', DENIED: 'DENIED' });

function createPaymentModel(db) {
    return Object.freeze({
        create: (enrollmentId, amount, status) => db.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [enrollmentId, amount, status]),
    });
}

module.exports = { createPaymentModel, PAYMENT_STATUS };
