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

	// Queue names
	QueueGoWorker     = "go-worker"     // For sites with existing configs
	QueuePythonWorker = "python-worker" // For sites needing AI learning
)

type QueueService struct {
	client *asynq.Client
}

func NewQueueService(redisAddr string) *QueueService {
	client := asynq.NewClient(asynq.RedisClientOpt{Addr: redisAddr})
	return &QueueService{client: client}
}

func (s *QueueService) EnqueueJob(ctx context.Context, job *models.Job) error {
	// Default to go-worker queue for backward compatibility
	return s.EnqueueJobToQueue(ctx, job, QueueGoWorker)
}

func (s *QueueService) EnqueueJobToQueue(ctx context.Context, job *models.Job, queueName string) error {
	payload, err := json.Marshal(job)
	if err != nil {
		return fmt.Errorf("failed to marshal job: %w", err)
	}

	task := asynq.NewTask(TypeExtractionJob, payload)

	// Enqueue to specific queue with options
	_, err = s.client.EnqueueContext(ctx, task, asynq.Queue(queueName))
	if err != nil {
		return fmt.Errorf("failed to enqueue task to queue %s: %w", queueName, err)
	}

	return nil
}

func (s *QueueService) Close() error {
	return s.client.Close()
}
