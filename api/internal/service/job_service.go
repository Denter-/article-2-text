package service

import (
	"context"
	"fmt"
	"net/url"
	"strings"

	"github.com/Denter-/article-extraction/api/internal/models"
	"github.com/Denter-/article-extraction/api/internal/repository"
	"github.com/google/uuid"
)

type JobService struct {
	jobRepo    *repository.JobRepository
	configRepo *repository.ConfigRepository
	userRepo   *repository.UserRepository
	queueSvc   *QueueService
}

func NewJobService(
	jobRepo *repository.JobRepository,
	configRepo *repository.ConfigRepository,
	userRepo *repository.UserRepository,
	queueSvc *QueueService,
) *JobService {
	return &JobService{
		jobRepo:    jobRepo,
		configRepo: configRepo,
		userRepo:   userRepo,
		queueSvc:   queueSvc,
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

	// Queue job for processing
	if err := s.queueSvc.EnqueueJob(ctx, job); err != nil {
		return nil, fmt.Errorf("failed to queue job: %w", err)
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

	// Queue all jobs
	for _, job := range jobs {
		s.queueSvc.EnqueueJob(ctx, job)
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


