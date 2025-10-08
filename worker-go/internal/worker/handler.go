package worker

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/hibiken/asynq"
	"github.com/rs/zerolog/log"

	"github.com/Denter-/article-extraction/worker/internal/extractor"
	"github.com/Denter-/article-extraction/worker/internal/repository"
)

const (
	TypeExtractionJob = "extraction:job"
)

type Handler struct {
	jobRepo    *repository.JobRepository
	configRepo *repository.ConfigRepository
	extractor  *extractor.Extractor
}

func NewHandler(
	jobRepo *repository.JobRepository,
	configRepo *repository.ConfigRepository,
	extractor *extractor.Extractor,
) *Handler {
	return &Handler{
		jobRepo:    jobRepo,
		configRepo: configRepo,
		extractor:  extractor,
	}
}

func (h *Handler) HandleExtractionJob(ctx context.Context, t *asynq.Task) error {
	// Parse job from payload
	var job repository.Job
	if err := json.Unmarshal(t.Payload(), &job); err != nil {
		return fmt.Errorf("failed to unmarshal job: %w", err)
	}

	log.Info().
		Str("job_id", job.ID.String()).
		Str("url", job.URL).
		Str("domain", job.Domain).
		Msg("🔄 Processing extraction job")

	// Update job status to processing
	if err := h.jobRepo.UpdateStatus(ctx, job.ID, repository.StatusProcessing, "Starting extraction..."); err != nil {
		log.Error().Err(err).Msg("Failed to update job status")
	}

	startTime := time.Now()

	// Check if site config exists
	config, err := h.configRepo.GetByDomain(ctx, job.Domain)
	if err != nil {
		// No config found - forward to Python AI worker for learning
		log.Warn().
			Str("domain", job.Domain).
			Msg("No site config found - forwarding to Python AI worker for learning")

		// Forward to Python AI worker - it will handle everything including completion
		_, err := h.extractor.ForwardToPythonAIWorker(ctx, &job)
		if err != nil {
			log.Error().Err(err).Msg("Failed to forward to Python AI worker")
			h.jobRepo.Fail(ctx, job.ID, fmt.Sprintf("Failed to forward to Python AI worker: %v", err))
			return err
		}

		// Python AI worker has already completed the job and updated the database
		// No need to do anything else - the job is done
		log.Info().
			Str("job_id", job.ID.String()).
			Msg("✅ Job completed by Python AI worker")
		return nil
	}

	log.Info().
		Str("domain", job.Domain).
		Bool("requires_browser", config.RequiresBrowser).
		Msg("Found site config")

	// Debug logging to check the actual value
	log.Info().
		Str("domain", job.Domain).
		Bool("requires_browser", config.RequiresBrowser).
		Msg("DEBUG: Checking requires_browser value")

	// Explicit check for debugging
	if config.RequiresBrowser == true {
		log.Info().
			Str("domain", job.Domain).
			Msg("DEBUG: config.RequiresBrowser is TRUE - should forward to Python")
	} else {
		log.Info().
			Str("domain", job.Domain).
			Bool("requires_browser", config.RequiresBrowser).
			Msg("DEBUG: config.RequiresBrowser is FALSE - will use Go worker")
	}

	// If site requires browser, forward to Python AI worker
	if config.RequiresBrowser {
		log.Info().
			Str("domain", job.Domain).
			Msg("Site requires browser - forwarding to Python AI worker")

		h.jobRepo.UpdateProgress(ctx, job.ID, 10, "Forwarding to Python AI worker for browser-based extraction...")

		// Forward to Python AI worker - it will handle everything including completion
		_, err := h.extractor.ForwardToPythonAIWorker(ctx, &job)
		if err != nil {
			log.Error().Err(err).Msg("Failed to forward to Python AI worker")
			h.jobRepo.Fail(ctx, job.ID, fmt.Sprintf("Failed to forward to Python AI worker: %v", err))
			return err
		}

		// Python AI worker has already completed the job and updated the database
		log.Info().
			Str("job_id", job.ID.String()).
			Msg("✅ Job completed by Python AI worker (browser-based extraction)")
		return nil
	} else {
		// Debug logging for when config.RequiresBrowser is false
		log.Info().
			Str("domain", job.Domain).
			Bool("requires_browser", config.RequiresBrowser).
			Msg("DEBUG: requires_browser is FALSE, proceeding with Go worker extraction")
	}

	// Update progress
	h.jobRepo.UpdateProgress(ctx, job.ID, 20, "Fetching and parsing HTML...")

	// Extract article - pass the config from database
	result, err := h.extractor.Extract(ctx, &job, config)
	if err != nil {
		errMsg := fmt.Sprintf("Extraction failed: %v", err)
		log.Error().
			Err(err).
			Str("job_id", job.ID.String()).
			Msg("Extraction failed")

		h.jobRepo.Fail(ctx, job.ID, errMsg)
		h.configRepo.UpdateUsageStats(ctx, job.Domain, false, 0)
		return fmt.Errorf("%s", errMsg)
	}

	// Update job with results
	job.ResultPath = &result.Path
	job.Title = &result.Title
	job.Author = &result.Author
	job.WordCount = &result.WordCount
	job.ImageCount = &result.ImageCount
	job.MarkdownContent = &result.Markdown

	if err := h.jobRepo.Complete(ctx, &job); err != nil {
		log.Error().Err(err).Msg("Failed to complete job")
		return err
	}

	// Update config stats
	extractionTime := int(time.Since(startTime).Milliseconds())
	h.configRepo.UpdateUsageStats(ctx, job.Domain, true, extractionTime)

	log.Info().
		Str("job_id", job.ID.String()).
		Dur("duration", time.Since(startTime)).
		Int("word_count", result.WordCount).
		Int("image_count", result.ImageCount).
		Str("result_path", result.Path).
		Msg("✅ Job completed successfully")

	return nil
}
