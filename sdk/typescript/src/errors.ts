export class GliaxinError extends Error {
  constructor(
    message: string,
    public readonly statusCode?: number,
  ) {
    super(message)
    this.name = 'GliaxinError'
  }
}

export class AuthError extends GliaxinError {
  constructor(message: string) {
    super(message, 401)
    this.name = 'AuthError'
  }
}

export class NotFoundError extends GliaxinError {
  constructor(message: string) {
    super(message, 404)
    this.name = 'NotFoundError'
  }
}

export class ValidationError extends GliaxinError {
  constructor(message: string) {
    super(message, 400)
    this.name = 'ValidationError'
  }
}

export class RateLimitError extends GliaxinError {
  constructor(message: string) {
    super(message, 429)
    this.name = 'RateLimitError'
  }
}

export class ServerError extends GliaxinError {
  constructor(message: string, statusCode: number) {
    super(message, statusCode)
    this.name = 'ServerError'
  }
}
