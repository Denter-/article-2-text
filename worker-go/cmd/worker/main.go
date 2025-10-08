package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/hibiken/asynq"
	"github.com/rs/zerolog"
	zlog "github.com/rs/zerolog/log"

	"github.com/Denter-/article-extraction/worker/internal/config"
	"github.com/Denter-/article-extraction/worker/internal/extractor"
	"github.com/Denter-/article-extraction/worker/internal/gemini"
	"github.com/Denter-/article-extraction/worker/internal/repository"
	"github.com/Denter-/article-extraction/worker/internal/worker"
)

func main() {
	// Setup logging
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	zlog.Logger = zlog.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	zlog.Info().Msg("🚀 Starting Article Extraction Worker (Go Fast Path)...")

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}
	zlog.Info().Msg("✅ Configuration loaded")

	// Connect to PostgreSQL
	db, err := repository.NewPostgresPool(cfg.Database.URL)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()
	zlog.Info().Msg("✅ Connected to PostgreSQL")

	// Initialize repositories
	jobRepo := repository.NewJobRepository(db)
	configRepo := repository.NewConfigRepository(db)

	// Initialize Gemini client
	geminiClient, err := gemini.NewClient(cfg.Gemini.APIKey)
	if err != nil {
		log.Fatalf("Failed to create Gemini client: %v", err)
	}
	zlog.Info().Msg("✅ Gemini client initialized")

	// Initialize extractor
	configDir := "config/sites" // Same directory structure as Python implementation
	extractorInstance := extractor.New(geminiClient, cfg.Storage.Path, configDir)

	// Create worker handler
	handler := worker.NewHandler(jobRepo, configRepo, extractorInstance)

	// Create asynq server
	redisAddr := fmt.Sprintf("%s:%s", cfg.Redis.Host, cfg.Redis.Port)
	srv := asynq.NewServer(
		asynq.RedisClientOpt{Addr: redisAddr},
		asynq.Config{
			Concurrency: cfg.Queue.Concurrency,
			Queues: map[string]int{
				"go-worker": 10,     // High priority for Go worker
				"python-worker": 5,  // AI learning queue
				"default":   3,      // Fallback for backward compatibility
			},
		},
	)

	// Register handler
	mux := asynq.NewServeMux()
	mux.HandleFunc(worker.TypeExtractionJob, handler.HandleExtractionJob)

	// Handle shutdown gracefully
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		<-sigChan
		zlog.Info().Msg("🛑 Shutting down worker...")
		srv.Shutdown()
	}()

	// Start worker
	zlog.Info().
		Int("concurrency", cfg.Queue.Concurrency).
		Str("redis", redisAddr).
		Msg("👷 Worker started, listening for jobs...")
	zlog.Info().Msg("")
	zlog.Info().Msg("Worker ready to process:")
	zlog.Info().Msg("  - Article extraction")
	zlog.Info().Msg("  - Image description generation")
	zlog.Info().Msg("  - Markdown conversion")
	zlog.Info().Msg("")

	if err := srv.Run(mux); err != nil {
		log.Fatalf("Could not start worker: %v", err)
	}
}
