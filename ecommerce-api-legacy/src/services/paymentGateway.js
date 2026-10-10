const { PAYMENT_STATUS } = require('../models/paymentModel');

// Regra do gateway simulado: apenas cartões que começam com este prefixo são aprovados.
const APPROVED_CARD_PREFIX = '4';

const maskCard = (cardNumber) => `**** ${String(cardNumber).slice(-4)}`;

function createPaymentGateway({ apiKey, logger }) {
    if (!apiKey) logger.warn('PAYMENT_GATEWAY_KEY não definida; gateway de pagamento em modo simulado');

    return Object.freeze({
        charge({ cardNumber, amount }) {
            logger.info(`Processando pagamento de ${amount} no cartão ${maskCard(cardNumber)}`);
            return cardNumber.startsWith(APPROVED_CARD_PREFIX) ? PAYMENT_STATUS.PAID : PAYMENT_STATUS.DENIED;
        },
    });
}

module.exports = { createPaymentGateway };
