const express = require('express');

const { openDatabase } = require('./database/connection');
const { initSchema } = require('./database/schema');
const passwordHasher = require('./utils/passwordHasher');

const { createUserModel } = require('./models/userModel');
const { createCourseModel } = require('./models/courseModel');
const { createEnrollmentModel } = require('./models/enrollmentModel');
const { createPaymentModel } = require('./models/paymentModel');
const { createAuditLogModel } = require('./models/auditLogModel');

const { createPaymentGateway } = require('./services/paymentGateway');
const { createCheckoutService } = require('./services/checkoutService');
const { createReportService } = require('./services/reportService');

const { createCheckoutController } = require('./controllers/checkoutController');
const { createReportController } = require('./controllers/reportController');
const { createUserController } = require('./controllers/userController');

const { createCheckoutRoutes } = require('./routes/checkoutRoutes');
const { createAdminRoutes } = require('./routes/adminRoutes');
const { createUserRoutes } = require('./routes/userRoutes');

const { createRequireAdmin } = require('./middlewares/requireAdmin');
const { createErrorHandler } = require('./middlewares/errorHandler');

// Composition root: cria a infraestrutura e injeta as dependências camada por camada.
async function createApp(config, logger) {
    const db = await openDatabase(config.databasePath);
    await initSchema(db, passwordHasher);

    const userModel = createUserModel(db);
    const courseModel = createCourseModel(db);
    const enrollmentModel = createEnrollmentModel(db);
    const paymentModel = createPaymentModel(db);
    const auditLogModel = createAuditLogModel(db);

    const paymentGateway = createPaymentGateway({ apiKey: config.paymentGatewayKey, logger });
    const checkoutService = createCheckoutService({
        db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel, paymentGateway, passwordHasher,
    });
    const reportService = createReportService({ courseModel });

    if (!config.adminToken) logger.warn('ADMIN_TOKEN não definido; endpoints administrativos desabilitados (403)');
    const requireAdmin = createRequireAdmin(config.adminToken);

    const app = express();
    app.disable('x-powered-by');
    app.use(express.json());

    app.use(createCheckoutRoutes({ checkoutController: createCheckoutController({ checkoutService }) }));
    app.use(createAdminRoutes({ reportController: createReportController({ reportService }), requireAdmin }));
    app.use(createUserRoutes({ userController: createUserController({ userModel }), requireAdmin }));

    app.use(createErrorHandler(logger));

    return { app, db };
}

module.exports = { createApp };
