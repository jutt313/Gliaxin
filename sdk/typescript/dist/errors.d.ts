export declare class GliaxinError extends Error {
    readonly statusCode?: number | undefined;
    constructor(message: string, statusCode?: number | undefined);
}
export declare class AuthError extends GliaxinError {
    constructor(message: string);
}
export declare class NotFoundError extends GliaxinError {
    constructor(message: string);
}
export declare class ValidationError extends GliaxinError {
    constructor(message: string);
}
export declare class RateLimitError extends GliaxinError {
    constructor(message: string);
}
export declare class ServerError extends GliaxinError {
    constructor(message: string, statusCode: number);
}
//# sourceMappingURL=errors.d.ts.map