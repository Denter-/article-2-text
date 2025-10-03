package repository

import (
	"context"
	"fmt"

	"github.com/Denter-/article-extraction/api/internal/models"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

type JobRepository struct {
	db *pgxpool.Pool
}

func NewJobRepository(db *pgxpool.Pool) *JobRepository {
	return &JobRepository{db: db}
}

func (r *JobRepository) Create(ctx context.Context, job *models.Job) error {
	query := `
		INSERT INTO jobs (user_id, url, domain, status, credits_used)
		VALUES ($1, $2, $3, $4, $5)
		RETURNING id, queued_at, created_at, updated_at
	`
	return r.db.QueryRow(
		ctx, query,
		job.UserID, job.URL, job.Domain, job.Status, job.CreditsUsed,
	).Scan(&job.ID, &job.QueuedAt, &job.CreatedAt, &job.UpdatedAt)
}

func (r *JobRepository) GetByID(ctx context.Context, id uuid.UUID) (*models.Job, error) {
	job := &models.Job{}
	query := `
		SELECT id, user_id, url, domain, status, worker_type,
		       progress_percent, progress_message, result_path, markdown_content,
		       title, author, published_at, word_count, image_count,
		       error_message, retry_count, queued_at, started_at, completed_at,
		       credits_used, created_at, updated_at
		FROM jobs
		WHERE id = $1
	`
	err := r.db.QueryRow(ctx, query, id).Scan(
		&job.ID, &job.UserID, &job.URL, &job.Domain, &job.Status, &job.WorkerType,
		&job.ProgressPercent, &job.ProgressMessage, &job.ResultPath, &job.MarkdownContent,
		&job.Title, &job.Author, &job.PublishedAt, &job.WordCount, &job.ImageCount,
		&job.ErrorMessage, &job.RetryCount, &job.QueuedAt, &job.StartedAt, &job.CompletedAt,
		&job.CreditsUsed, &job.CreatedAt, &job.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("job not found: %w", err)
	}
	return job, nil
}

func (r *JobRepository) GetByUserID(ctx context.Context, userID uuid.UUID, limit int) ([]*models.Job, error) {
	query := `
		SELECT id, user_id, url, domain, status, worker_type,
		       progress_percent, progress_message, result_path,
		       title, author, published_at, word_count, image_count,
		       error_message, queued_at, started_at, completed_at,
		       credits_used, created_at, updated_at
		FROM jobs
		WHERE user_id = $1
		ORDER BY created_at DESC
		LIMIT $2
	`
	rows, err := r.db.Query(ctx, query, userID, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	jobs := make([]*models.Job, 0)
	for rows.Next() {
		job := &models.Job{}
		err := rows.Scan(
			&job.ID, &job.UserID, &job.URL, &job.Domain, &job.Status, &job.WorkerType,
			&job.ProgressPercent, &job.ProgressMessage, &job.ResultPath,
			&job.Title, &job.Author, &job.PublishedAt, &job.WordCount, &job.ImageCount,
			&job.ErrorMessage, &job.QueuedAt, &job.StartedAt, &job.CompletedAt,
			&job.CreditsUsed, &job.CreatedAt, &job.UpdatedAt,
		)
		if err != nil {
			return nil, err
		}
		jobs = append(jobs, job)
	}
	return jobs, nil
}

func (r *JobRepository) UpdateStatus(ctx context.Context, id uuid.UUID, status models.JobStatus, message *string) error {
	query := `
		UPDATE jobs
		SET status = $1, progress_message = $2, updated_at = CURRENT_TIMESTAMP
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

func (r *JobRepository) Complete(ctx context.Context, job *models.Job) error {
	query := `
		UPDATE jobs
		SET status = $1, progress_percent = 100,
		    result_path = $2, markdown_content = $3,
		    title = $4, author = $5, word_count = $6, image_count = $7,
		    completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
		WHERE id = $8
	`
	_, err := r.db.Exec(
		ctx, query,
		models.StatusCompleted, job.ResultPath, job.MarkdownContent,
		job.Title, job.Author, job.WordCount, job.ImageCount, job.ID,
	)
	return err
}

func (r *JobRepository) Fail(ctx context.Context, id uuid.UUID, errorMsg string) error {
	query := `
		UPDATE jobs
		SET status = $1, error_message = $2, completed_at = CURRENT_TIMESTAMP,
		    updated_at = CURRENT_TIMESTAMP
		WHERE id = $3
	`
	_, err := r.db.Exec(ctx, query, models.StatusFailed, errorMsg, id)
	return err
}


