package repository

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

type JobStatus string

const (
	StatusQueued                 JobStatus = "queued"
	StatusProcessing             JobStatus = "processing"
	StatusLearning               JobStatus = "learning"
	StatusExtracting             JobStatus = "extracting"
	StatusGeneratingDescriptions JobStatus = "generating_descriptions"
	StatusCompleted              JobStatus = "completed"
	StatusFailed                 JobStatus = "failed"
)

type Job struct {
	ID              uuid.UUID
	UserID          uuid.UUID
	URL             string
	Domain          string
	Status          JobStatus
	ProgressPercent int
	ProgressMessage *string
	ResultPath      *string
	Title           *string
	Author          *string
	WordCount       *int
	ImageCount      *int
	MarkdownContent *string
	CreditsUsed     int
}

type JobRepository struct {
	db *pgxpool.Pool
}

func NewJobRepository(db *pgxpool.Pool) *JobRepository {
	return &JobRepository{db: db}
}

func (r *JobRepository) UpdateStatus(ctx context.Context, id uuid.UUID, status JobStatus, message string) error {
	query := `
		UPDATE jobs
		SET status = $1, progress_message = $2, 
		    started_at = COALESCE(started_at, CURRENT_TIMESTAMP),
		    updated_at = CURRENT_TIMESTAMP
		WHERE id = $3
	`
	_, err := r.db.Exec(ctx, query, status, message, id)
	return err
}

func (r *JobRepository) UpdateProgress(ctx context.Context, id uuid.UUID, percent int, message string) error {
	query := `
		UPDATE jobs
		SET progress_percent = $1, progress_message = $2, updated_at = CURRENT_TIMESTAMP
		WHERE id = $3
	`
	_, err := r.db.Exec(ctx, query, percent, message, id)
	return err
}

func (r *JobRepository) Complete(ctx context.Context, job *Job) error {
	query := `
		UPDATE jobs
		SET status = $1, progress_percent = 100,
		    result_path = $2, title = $3, author = $4,
		    word_count = $5, image_count = $6, markdown_content = $7,
		    completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
		WHERE id = $8
	`
	_, err := r.db.Exec(
		ctx, query,
		StatusCompleted, job.ResultPath, job.Title, job.Author,
		job.WordCount, job.ImageCount, job.MarkdownContent, job.ID,
	)
	return err
}

func (r *JobRepository) Fail(ctx context.Context, id uuid.UUID, errorMsg string) error {
	query := `
		UPDATE jobs
		SET status = $1, error_message = $2, 
		    completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
		WHERE id = $3
	`
	_, err := r.db.Exec(ctx, query, StatusFailed, errorMsg, id)
	return err
}

func (r *JobRepository) GetByID(ctx context.Context, id uuid.UUID) (*Job, error) {
	job := &Job{}
	query := `
		SELECT id, user_id, url, domain, status, progress_percent, 
		       progress_message, result_path, title, author, word_count, image_count, credits_used
		FROM jobs
		WHERE id = $1
	`
	err := r.db.QueryRow(ctx, query, id).Scan(
		&job.ID, &job.UserID, &job.URL, &job.Domain, &job.Status,
		&job.ProgressPercent, &job.ProgressMessage, &job.ResultPath,
		&job.Title, &job.Author, &job.WordCount, &job.ImageCount, &job.CreditsUsed,
	)
	if err != nil {
		return nil, fmt.Errorf("job not found: %w", err)
	}
	return job, nil
}

type SiteConfig struct {
	Domain          string
	ConfigYAML      string
	RequiresBrowser bool
}

type ConfigRepository struct {
	db *pgxpool.Pool
}

func NewConfigRepository(db *pgxpool.Pool) *ConfigRepository {
	return &ConfigRepository{db: db}
}

func (r *ConfigRepository) GetByDomain(ctx context.Context, domain string) (*SiteConfig, error) {
	config := &SiteConfig{}
	query := `
		SELECT domain, config_yaml, requires_browser
		FROM site_configs
		WHERE domain = $1
	`
	err := r.db.QueryRow(ctx, query, domain).Scan(
		&config.Domain, &config.ConfigYAML, &config.RequiresBrowser,
	)
	if err != nil {
		return nil, fmt.Errorf("config not found: %w", err)
	}
	return config, nil
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

// Database connection helper
func NewPostgresPool(connString string) (*pgxpool.Pool, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pool, err := pgxpool.New(ctx, connString)
	if err != nil {
		return nil, fmt.Errorf("unable to create connection pool: %w", err)
	}

	if err := pool.Ping(ctx); err != nil {
		return nil, fmt.Errorf("unable to ping database: %w", err)
	}

	return pool, nil
}


