class AppError extends Error {
    constructor(message, status = 400) {
        super(message);
        this.name = this.constructor.name;
        this.status = status;
    }
}

class ValidationError extends AppError {
    constructor(message = 'Bad Request') { super(message, 400); }
}

class NotFoundError extends AppError {
    constructor(message) { super(message, 404); }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Não autorizado') { super(message, 401); }
}

class ForbiddenError extends AppError {
    constructor(message) { super(message, 403); }
}

module.exports = { AppError, ValidationError, NotFoundError, UnauthorizedError, ForbiddenError };
