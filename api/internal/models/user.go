package models

import (
	"time"

	"github.com/google/uuid"
)

type UserTier string

const (
	TierFree       UserTier = "free"
	TierPro        UserTier = "pro"
	TierEnterprise UserTier = "enterprise"
)

type User struct {
	ID           uuid.UUID  `json:"id" db:"id"`
	Email        string     `json:"email" db:"email" validate:"required,email"`
	PasswordHash string     `json:"-" db:"password_hash"`
	Tier         UserTier   `json:"tier" db:"tier"`
	Credits      int        `json:"credits" db:"credits"`
	APIKey       *string    `json:"api_key,omitempty" db:"api_key"`
	CreatedAt    time.Time  `json:"created_at" db:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at" db:"updated_at"`
	LastLoginAt  *time.Time `json:"last_login_at,omitempty" db:"last_login_at"`
	IsActive     bool       `json:"is_active" db:"is_active"`
}

type CreateUserRequest struct {
	Email    string `json:"email" validate:"required,email"`
	Password string `json:"password" validate:"required,min=8"`
}

type LoginRequest struct {
	Email    string `json:"email" validate:"required,email"`
	Password string `json:"password" validate:"required"`
}

type LoginResponse struct {
	Token string `json:"token"`
	User  User   `json:"user"`
}


