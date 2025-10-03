package models

import (
	"time"

	"github.com/google/uuid"
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
	ID              uuid.UUID  `json:"id" db:"id"`
	UserID          uuid.UUID  `json:"user_id" db:"user_id"`
	URL             string     `json:"url" db:"url"`
	Domain          string     `json:"domain" db:"domain"`
	Status          JobStatus  `json:"status" db:"status"`
	WorkerType      *string    `json:"worker_type,omitempty" db:"worker_type"`
	ProgressPercent int        `json:"progress_percent" db:"progress_percent"`
	ProgressMessage *string    `json:"progress_message,omitempty" db:"progress_message"`
	ResultPath      *string    `json:"result_path,omitempty" db:"result_path"`
	MarkdownContent *string    `json:"markdown_content,omitempty" db:"markdown_content"`
	Title           *string    `json:"title,omitempty" db:"title"`
	Author          *string    `json:"author,omitempty" db:"author"`
	PublishedAt     *time.Time `json:"published_at,omitempty" db:"published_at"`
	WordCount       *int       `json:"word_count,omitempty" db:"word_count"`
	ImageCount      *int       `json:"image_count,omitempty" db:"image_count"`
	ErrorMessage    *string    `json:"error_message,omitempty" db:"error_message"`
	RetryCount      int        `json:"retry_count" db:"retry_count"`
	QueuedAt        time.Time  `json:"queued_at" db:"queued_at"`
	StartedAt       *time.Time `json:"started_at,omitempty" db:"started_at"`
	CompletedAt     *time.Time `json:"completed_at,omitempty" db:"completed_at"`
	CreditsUsed     int        `json:"credits_used" db:"credits_used"`
	CreatedAt       time.Time  `json:"created_at" db:"created_at"`
	UpdatedAt       time.Time  `json:"updated_at" db:"updated_at"`
}

type CreateJobRequest struct {
	URL string `json:"url" validate:"required,url"`
}

type CreateBatchJobRequest struct {
	URLs []string `json:"urls" validate:"required,min=1,max=100,dive,url"`
}


