package service

import (
	"context"
	"fmt"
	"net/url"
	"strings"

	"github.com/Denter-/article-extraction/api/internal/models"
	"github.com/Denter-/article-extraction/api/internal/repository"
	ws "github.com/Denter-/article-extraction/api/internal/websocket"
	"github.com/google/uuid"
)

type JobService struct {
	jobRepo    *repository.JobRepository
	configRepo *repository.ConfigRepository
	userRepo   *repository.UserRepository
	queueSvc   *QueueService
	hub        *ws.Hub
}

func NewJobService(
	jobRepo *repository.JobRepository,
	configRepo *repository.ConfigRepository,
	userRepo *repository.UserRepository,
	queueSvc *QueueService,
	hub *ws.Hub,
) *JobService {
	return &JobService{
		jobRepo:    jobRepo,
		configRepo: configRepo,
		userRepo:   userRepo,
		queueSvc:   queueSvc,
		hub:        hub,
	}
}

func (s *JobService) CreateJob(ctx context.Context, userID uuid.UUID, req *models.CreateJobRequest) (*models.Job, error) {
	// Check user credits
	user, err := s.userRepo.GetByID(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("user not found: %w", err)
	}

	if user.Credits < 1 {
		return nil, fmt.Errorf("insufficient credits")
	}

	// Parse domain
	domain, err := extractDomain(req.URL)
	if err != nil {
		return nil, fmt.Errorf("invalid URL: %w", err)
	}

	// Create job
	job := &models.Job{
		UserID:      userID,
		URL:         req.URL,
		Domain:      domain,
		Status:      models.StatusQueued,
		CreditsUsed: 1,
	}

	if err := s.jobRepo.Create(ctx, job); err != nil {
		return nil, fmt.Errorf("failed to create job: %w", err)
	}

	// Deduct credits
	newCredits := user.Credits - 1
	if err := s.userRepo.UpdateCredits(ctx, userID, newCredits); err != nil {
		return nil, fmt.Errorf("failed to update credits: %w", err)
	}

	// Check if site configuration exists to determine which worker to use
	_, err = s.configRepo.GetByDomain(ctx, job.Domain)
	if err != nil {
		// No config found, send to Python worker for AI learning
		if err := s.queueSvc.EnqueueJobToQueue(ctx, job, "python-worker"); err != nil {
			return nil, fmt.Errorf("failed to queue job for AI learning: %w", err)
		}
	} else {
		// Config exists, send to Go worker for fast extraction
		if err := s.queueSvc.EnqueueJobToQueue(ctx, job, "go-worker"); err != nil {
			return nil, fmt.Errorf("failed to queue job for extraction: %w", err)
		}
	}

	// Broadcast job creation via WebSocket
	if s.hub != nil {
		s.hub.BroadcastToUser(userID.String(), "job_status", map[string]interface{}{
			"job_id":   job.ID.String(),
			"status":   job.Status,
			"url":      job.URL,
			"domain":   job.Domain,
		})
	}

	return job, nil
}

func (s *JobService) CreateBatchJobs(ctx context.Context, userID uuid.UUID, req *models.CreateBatchJobRequest) ([]*models.Job, error) {
	// Check user credits
	user, err := s.userRepo.GetByID(ctx, userID)
	if err != nil {
		return nil, fmt.Errorf("user not found: %w", err)
	}

	requiredCredits := len(req.URLs)
	if user.Credits < requiredCredits {
		return nil, fmt.Errorf("insufficient credits: need %d, have %d", requiredCredits, user.Credits)
	}

	// Create all jobs
	jobs := make([]*models.Job, 0, len(req.URLs))
	for _, urlStr := range req.URLs {
		domain, err := extractDomain(urlStr)
		if err != nil {
			continue // Skip invalid URLs
		}

		job := &models.Job{
			UserID:      userID,
			URL:         urlStr,
			Domain:      domain,
			Status:      models.StatusQueued,
			CreditsUsed: 1,
		}

		if err := s.jobRepo.Create(ctx, job); err != nil {
			continue // Skip failed creations
		}

		jobs = append(jobs, job)
	}

	// Deduct credits
	newCredits := user.Credits - len(jobs)
	if err := s.userRepo.UpdateCredits(ctx, userID, newCredits); err != nil {
		return nil, fmt.Errorf("failed to update credits: %w", err)
	}

	// Queue all jobs with appropriate routing
	for _, job := range jobs {
		_, err := s.configRepo.GetByDomain(ctx, job.Domain)
		if err != nil {
			// No config found, send to Python worker for AI learning
			s.queueSvc.EnqueueJobToQueue(ctx, job, "python-worker")
		} else {
			// Config exists, send to Go worker for fast extraction
			s.queueSvc.EnqueueJobToQueue(ctx, job, "go-worker")
		}
	}

	return jobs, nil
}

func (s *JobService) GetJob(ctx context.Context, jobID uuid.UUID, userID uuid.UUID) (*models.Job, error) {
	job, err := s.jobRepo.GetByID(ctx, jobID)
	if err != nil {
		return nil, fmt.Errorf("job not found: %w", err)
	}

	// Verify ownership
	if job.UserID != userID {
		return nil, fmt.Errorf("unauthorized")
	}

	return job, nil
}

func (s *JobService) ListUserJobs(ctx context.Context, userID uuid.UUID, limit int) ([]*models.Job, error) {
	if limit <= 0 || limit > 100 {
		limit = 20
	}
	return s.jobRepo.GetByUserID(ctx, userID, limit)
}

func extractDomain(urlStr string) (string, error) {
	parsedURL, err := url.Parse(urlStr)
	if err != nil {
		return "", err
	}

	host := parsedURL.Hostname()
	// Remove www. prefix
	host = strings.TrimPrefix(host, "www.")

	return host, nil
}
