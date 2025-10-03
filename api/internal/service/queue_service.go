package service

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/Denter-/article-extraction/api/internal/models"
	"github.com/hibiken/asynq"
)

const (
	TypeExtractionJob = "extraction:job"
)

type QueueService struct {
	client *asynq.Client
}

func NewQueueService(redisAddr string) *QueueService {
	client := asynq.NewClient(asynq.RedisClientOpt{Addr: redisAddr})
	return &QueueService{client: client}
}

func (s *QueueService) EnqueueJob(ctx context.Context, job *models.Job) error {
	payload, err := json.Marshal(job)
	if err != nil {
		return fmt.Errorf("failed to marshal job: %w", err)
	}

	task := asynq.NewTask(TypeExtractionJob, payload)

	// Enqueue with options
	_, err = s.client.EnqueueContext(ctx, task)
	if err != nil {
		return fmt.Errorf("failed to enqueue task: %w", err)
	}

	return nil
}

func (s *QueueService) Close() error {
	return s.client.Close()
}


