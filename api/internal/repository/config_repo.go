package repository

import (
	"context"
	"fmt"

	"github.com/Denter-/article-extraction/api/internal/models"
	"github.com/jackc/pgx/v5/pgxpool"
)

type ConfigRepository struct {
	db *pgxpool.Pool
}

func NewConfigRepository(db *pgxpool.Pool) *ConfigRepository {
	return &ConfigRepository{db: db}
}

func (r *ConfigRepository) GetByDomain(ctx context.Context, domain string) (*models.SiteConfig, error) {
	config := &models.SiteConfig{}
	query := `
		SELECT id, domain, config_yaml, requires_browser, learned_by_user_id,
		       learned_at, learn_iterations, success_count, failure_count,
		       last_used_at, version, notes, created_at, updated_at, avg_extraction_time_ms
		FROM site_configs
		WHERE domain = $1
	`
	err := r.db.QueryRow(ctx, query, domain).Scan(
		&config.ID, &config.Domain, &config.ConfigYAML, &config.RequiresBrowser,
		&config.LearnedByUserID, &config.LearnedAt, &config.LearnIterations,
		&config.SuccessCount, &config.FailureCount, &config.LastUsedAt,
		&config.Version, &config.Notes, &config.CreatedAt, &config.UpdatedAt,
		&config.AvgExtractionTimeMs,
	)
	if err != nil {
		return nil, fmt.Errorf("config not found: %w", err)
	}
	return config, nil
}

func (r *ConfigRepository) Create(ctx context.Context, config *models.SiteConfig) error {
	query := `
		INSERT INTO site_configs (domain, config_yaml, requires_browser, learned_by_user_id, learn_iterations)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id, learned_at, created_at, updated_at
	`
	return r.db.QueryRow(
		ctx, query,
		config.Domain, config.ConfigYAML, config.RequiresBrowser, config.LearnedByUserID, config.LearnIterations,
	).Scan(&config.ID, &config.LearnedAt, &config.CreatedAt, &config.UpdatedAt)
}

func (r *ConfigRepository) UpdateUsageStats(ctx context.Context, domain string, success bool, extractionTimeMs int) error {
	var query string
	if success {
		query = `
			UPDATE site_configs
			SET success_count = success_count + 1,
			    last_used_at = CURRENT_TIMESTAMP,
			    avg_extraction_time_ms = CASE
			        WHEN avg_extraction_time_ms IS NULL THEN $2
			        ELSE (avg_extraction_time_ms + $2) / 2
			    END
			WHERE domain = $1
		`
	} else {
		query = `
			UPDATE site_configs
			SET failure_count = failure_count + 1,
			    last_used_at = CURRENT_TIMESTAMP
			WHERE domain = $1
		`
	}
	_, err := r.db.Exec(ctx, query, domain, extractionTimeMs)
	return err
}


