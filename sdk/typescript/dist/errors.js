export class GliaxinError extends Error {
    statusCode;
    constructor(message, statusCode) {
        super(message);
        this.statusCode = statusCode;
        this.name = 'GliaxinError';
    }
}
export class AuthError extends GliaxinError {
    constructor(message) {
        super(message, 401);
        this.name = 'AuthError';
    }
}
export class NotFoundError extends GliaxinError {
    constructor(message) {
        super(message, 404);
        this.name = 'NotFoundError';
    }
}
export class ValidationError extends GliaxinError {
    constructor(message) {
        super(message, 400);
        this.name = 'ValidationError';
    }
}
export class RateLimitError extends GliaxinError {
    constructor(message) {
        super(message, 429);
        this.name = 'RateLimitError';
    }
}
export class ServerError extends GliaxinError {
    constructor(message, statusCode) {
        super(message, statusCode);
        this.name = 'ServerError';
    }
}
//# sourceMappingURL=errors.js.map