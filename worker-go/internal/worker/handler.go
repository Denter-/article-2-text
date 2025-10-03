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

		// Forward to Python AI worker
		result, err := h.extractor.ForwardToPythonAIWorker(ctx, &job)
		if err != nil {
			log.Error().Err(err).Msg("Failed to forward to Python AI worker")
			h.jobRepo.Fail(ctx, job.ID, fmt.Sprintf("Failed to forward to Python AI worker: %v", err))
			return err
		}

		// Update job with Python AI worker result
		job.ResultPath = &result.Path
		job.MarkdownContent = &result.Markdown
		job.Title = &result.Title
		job.Author = &result.Author
		job.WordCount = &result.WordCount
		job.ImageCount = &result.ImageCount
		job.Status = repository.StatusCompleted

		// Mark job as completed
		h.jobRepo.Complete(ctx, &job)
		return nil
	}

	log.Info().
		Str("domain", job.Domain).
		Bool("requires_browser", config.RequiresBrowser).
		Msg("Found site config")

	// For now, we'll proceed with simple extraction even if browser is required
	// Full browser support will be added in Python worker integration
	if config.RequiresBrowser {
		h.jobRepo.UpdateProgress(ctx, job.ID, 10, "Note: Site may require JavaScript (proceeding with static HTML)")
	}

	// Update progress
	h.jobRepo.UpdateProgress(ctx, job.ID, 20, "Fetching and parsing HTML...")

	// Extract article
	result, err := h.extractor.Extract(ctx, &job)
	if err != nil {
		errMsg := fmt.Sprintf("Extraction failed: %v", err)
		log.Error().
			Err(err).
			Str("job_id", job.ID.String()).
			Msg("Extraction failed")

		h.jobRepo.Fail(ctx, job.ID, errMsg)
		h.configRepo.UpdateUsageStats(ctx, job.Domain, false, 0)
		return fmt.Errorf(errMsg)
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


