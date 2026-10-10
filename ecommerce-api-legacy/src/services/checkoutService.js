const { AppError, NotFoundError } = require('../errors');
const { PAYMENT_STATUS } = require('../models/paymentModel');

function createCheckoutService({
    db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway, passwordHasher,
}) {
    return Object.freeze({
        async checkout({ name, email, password, courseId, cardNumber }) {
            const course = await courseModel.findActiveById(courseId);
            if (!course) throw new NotFoundError('Curso não encontrado');

            const status = paymentGateway.charge({ cardNumber, amount: course.price });
            if (status === PAYMENT_STATUS.DENIED) throw new AppError('Pagamento recusado', 400);

            return db.transaction(async () => {
                const existing = await userModel.findByEmail(email);
                const userId = existing ? existing.id : await userModel.create({
                    name,
                    email,
                    passwordHash: passwordHasher.hashPassword(password || passwordHasher.generateRandomPassword()),
                });
                const enrollmentId = await enrollmentModel.create(userId, course.id);
                await paymentModel.create(enrollmentId, course.price, status);
                await auditLogModel.log(`Checkout curso ${course.id} por ${userId}`);
                return { enrollmentId };
            });
        },
    });
}

module.exports = { createCheckoutService };
