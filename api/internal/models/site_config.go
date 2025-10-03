package models

import (
	"time"

	"github.com/google/uuid"
)

type SiteConfig struct {
	ID                  uuid.UUID  `json:"id" db:"id"`
	Domain              string     `json:"domain" db:"domain"`
	ConfigYAML          string     `json:"config_yaml" db:"config_yaml"`
	RequiresBrowser     bool       `json:"requires_browser" db:"requires_browser"`
	LearnedByUserID     *uuid.UUID `json:"learned_by_user_id,omitempty" db:"learned_by_user_id"`
	LearnedAt           time.Time  `json:"learned_at" db:"learned_at"`
	LearnIterations     int        `json:"learn_iterations" db:"learn_iterations"`
	SuccessCount        int        `json:"success_count" db:"success_count"`
	FailureCount        int        `json:"failure_count" db:"failure_count"`
	LastUsedAt          *time.Time `json:"last_used_at,omitempty" db:"last_used_at"`
	Version             int        `json:"version" db:"version"`
	Notes               *string    `json:"notes,omitempty" db:"notes"`
	CreatedAt           time.Time  `json:"created_at" db:"created_at"`
	UpdatedAt           time.Time  `json:"updated_at" db:"updated_at"`
	AvgExtractionTimeMs *int       `json:"avg_extraction_time_ms,omitempty" db:"avg_extraction_time_ms"`
}


