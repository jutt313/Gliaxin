package gliaxin

import "fmt"

// GliaxinError is the base error type for all Gliaxin SDK errors.
type GliaxinError struct {
	Message    string
	StatusCode int
}

func (e *GliaxinError) Error() string {
	return fmt.Sprintf("gliaxin: %s (status %d)", e.Message, e.StatusCode)
}

// AuthError is returned when the API key is missing or invalid (401).
type AuthError struct{ GliaxinError }

// NotFoundError is returned when the requested resource does not exist (404).
type NotFoundError struct{ GliaxinError }

// ValidationError is returned when a required field is missing or invalid (400).
type ValidationError struct{ GliaxinError }

// RateLimitError is returned when burst or monthly limits are exceeded (429).
type RateLimitError struct{ GliaxinError }

// ServerError is returned on unexpected server errors (5xx).
type ServerError struct{ GliaxinError }

func newAPIError(status int, message string) error {
	base := GliaxinError{Message: message, StatusCode: status}
	switch status {
	case 400:
		return &ValidationError{base}
	case 401:
		return &AuthError{base}
	case 404:
		return &NotFoundError{base}
	case 429:
		return &RateLimitError{base}
	}
	if status >= 500 {
		return &ServerError{base}
	}
	return &base
}
