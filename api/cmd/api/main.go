package main

import (
	"fmt"
	"log"
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"github.com/rs/zerolog"
	zlog "github.com/rs/zerolog/log"

	"github.com/Denter-/article-extraction/api/internal/config"
	"github.com/Denter-/article-extraction/api/internal/database"
	"github.com/Denter-/article-extraction/api/internal/handlers"
	"github.com/Denter-/article-extraction/api/internal/middleware"
	"github.com/Denter-/article-extraction/api/internal/repository"
	"github.com/Denter-/article-extraction/api/internal/service"
	ws "github.com/Denter-/article-extraction/api/internal/websocket"
)

func main() {
	// Setup logging
	zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
	zlog.Logger = zlog.Output(zerolog.ConsoleWriter{Out: os.Stderr})

	zlog.Info().Msg("🚀 Starting Article Extraction API...")

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}
	zlog.Info().Msg("✅ Configuration loaded")

	// Connect to PostgreSQL
	db, err := database.NewPostgresPool(&cfg.Database)
	if err != nil {
		log.Fatalf("Failed to connect to database: %v", err)
	}
	defer db.Close()
	zlog.Info().Msg("✅ Connected to PostgreSQL")

	// Connect to Redis
	rdb, err := database.NewRedisClient(&cfg.Redis)
	if err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	defer rdb.Close()
	zlog.Info().Msg("✅ Connected to Redis")

	// Initialize repositories
	userRepo := repository.NewUserRepository(db)
	jobRepo := repository.NewJobRepository(db)
	configRepo := repository.NewConfigRepository(db)

	// Initialize WebSocket hub
	hub := ws.NewHub()
	go hub.Run()
	zlog.Info().Msg("✅ WebSocket hub started")

	// Initialize services
	queueSvc := service.NewQueueService(fmt.Sprintf("%s:%s", cfg.Redis.Host, cfg.Redis.Port))
	defer queueSvc.Close()

	authSvc := service.NewAuthService(userRepo, &cfg.Auth)
	jobSvc := service.NewJobService(jobRepo, configRepo, userRepo, queueSvc)

	// Initialize handlers
	authHandler := handlers.NewAuthHandler(authSvc)
	extractHandler := handlers.NewExtractHandler(jobSvc)
	jobHandler := handlers.NewJobHandler(jobSvc)
	wsHandler := handlers.NewWebSocketHandler(hub, authSvc)

	// Create Fiber app
	app := fiber.New(fiber.Config{
		ErrorHandler: customErrorHandler,
		AppName:      "Article Extraction API",
	})

	// Global middleware
	app.Use(recover.New())
	app.Use(cors.New())
	app.Use(middleware.Logger())

	// Public routes
	app.Get("/health", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{
			"status":  "healthy",
			"service": "article-extraction-api",
			"version": "1.0.0",
		})
	})

	// Auth routes
	auth := app.Group("/api/v1/auth")
	auth.Post("/register", authHandler.Register)
	auth.Post("/login", authHandler.Login)
	auth.Get("/me", middleware.AuthRequired(authSvc), authHandler.Me)

	// WebSocket route (handles auth internally)
	app.Get("/api/v1/ws", wsHandler.HandleConnection)

	// Protected routes
	api := app.Group("/api/v1")
	api.Use(middleware.AuthRequired(authSvc))
	api.Use(middleware.RateLimit(rdb, &cfg.RateLimit))

	// Extract routes
	api.Post("/extract/single", extractHandler.ExtractSingle)
	api.Post("/extract/batch", extractHandler.ExtractBatch)

	// Job routes
	api.Get("/jobs/:id", jobHandler.GetJob)
	api.Get("/jobs", jobHandler.ListJobs)

	// Start server
	addr := fmt.Sprintf("%s:%s", cfg.Server.Host, cfg.Server.Port)
	zlog.Info().Msgf("🌐 Server starting on %s", addr)
	zlog.Info().Msg("")
	zlog.Info().Msg("Available endpoints:")
	zlog.Info().Msg("  GET  /health")
	zlog.Info().Msg("  POST /api/v1/auth/register")
	zlog.Info().Msg("  POST /api/v1/auth/login")
	zlog.Info().Msg("  GET  /api/v1/auth/me")
	zlog.Info().Msg("  POST /api/v1/extract/single")
	zlog.Info().Msg("  POST /api/v1/extract/batch")
	zlog.Info().Msg("  GET  /api/v1/jobs/:id")
	zlog.Info().Msg("  GET  /api/v1/jobs")
	zlog.Info().Msg("")

	if err := app.Listen(addr); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}

func customErrorHandler(c *fiber.Ctx, err error) error {
	code := fiber.StatusInternalServerError
	if e, ok := err.(*fiber.Error); ok {
		code = e.Code
	}

	zlog.Error().
		Err(err).
		Int("status", code).
		Str("path", c.Path()).
		Msg("Request error")

	return c.Status(code).JSON(fiber.Map{
		"error": err.Error(),
	})
}


