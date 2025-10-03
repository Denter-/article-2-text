package repository

import (
	"context"
	"fmt"

	"github.com/Denter-/article-extraction/api/internal/models"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

type UserRepository struct {
	db *pgxpool.Pool
}

func NewUserRepository(db *pgxpool.Pool) *UserRepository {
	return &UserRepository{db: db}
}

func (r *UserRepository) Create(ctx context.Context, user *models.User) error {
	query := `
		INSERT INTO users (email, password_hash, tier, credits, api_key)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id, created_at, updated_at
	`
	return r.db.QueryRow(
		ctx, query,
		user.Email, user.PasswordHash, user.Tier, user.Credits, user.APIKey,
	).Scan(&user.ID, &user.CreatedAt, &user.UpdatedAt)
}

func (r *UserRepository) GetByEmail(ctx context.Context, email string) (*models.User, error) {
	user := &models.User{}
	query := `
		SELECT id, email, password_hash, tier, credits, api_key,
		       created_at, updated_at, last_login_at, is_active
		FROM users
		WHERE email = $1 AND is_active = true
	`
	err := r.db.QueryRow(ctx, query, email).Scan(
		&user.ID, &user.Email, &user.PasswordHash, &user.Tier, &user.Credits,
		&user.APIKey, &user.CreatedAt, &user.UpdatedAt, &user.LastLoginAt, &user.IsActive,
	)
	if err != nil {
		return nil, fmt.Errorf("user not found: %w", err)
	}
	return user, nil
}

func (r *UserRepository) GetByID(ctx context.Context, id uuid.UUID) (*models.User, error) {
	user := &models.User{}
	query := `
		SELECT id, email, password_hash, tier, credits, api_key,
		       created_at, updated_at, last_login_at, is_active
		FROM users
		WHERE id = $1 AND is_active = true
	`
	err := r.db.QueryRow(ctx, query, id).Scan(
		&user.ID, &user.Email, &user.PasswordHash, &user.Tier, &user.Credits,
		&user.APIKey, &user.CreatedAt, &user.UpdatedAt, &user.LastLoginAt, &user.IsActive,
	)
	if err != nil {
		return nil, fmt.Errorf("user not found: %w", err)
	}
	return user, nil
}

func (r *UserRepository) GetByAPIKey(ctx context.Context, apiKey string) (*models.User, error) {
	user := &models.User{}
	query := `
		SELECT id, email, password_hash, tier, credits, api_key,
		       created_at, updated_at, last_login_at, is_active
		FROM users
		WHERE api_key = $1 AND is_active = true
	`
	err := r.db.QueryRow(ctx, query, apiKey).Scan(
		&user.ID, &user.Email, &user.PasswordHash, &user.Tier, &user.Credits,
		&user.APIKey, &user.CreatedAt, &user.UpdatedAt, &user.LastLoginAt, &user.IsActive,
	)
	if err != nil {
		return nil, fmt.Errorf("user not found: %w", err)
	}
	return user, nil
}

func (r *UserRepository) UpdateCredits(ctx context.Context, userID uuid.UUID, credits int) error {
	query := `UPDATE users SET credits = $1 WHERE id = $2`
	_, err := r.db.Exec(ctx, query, credits, userID)
	return err
}

func (r *UserRepository) UpdateLastLogin(ctx context.Context, userID uuid.UUID) error {
	query := `UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = $1`
	_, err := r.db.Exec(ctx, query, userID)
	return err
}


