package config

import (
	"fmt"
	"os"
	"time"

	"github.com/joho/godotenv"
)

type Config struct {
	Server    ServerConfig
	Database  DatabaseConfig
	Redis     RedisConfig
	Queue     QueueConfig
	Auth      AuthConfig
	Gemini    GeminiConfig
	Storage   StorageConfig
	RateLimit RateLimitConfig
	Logging   LoggingConfig
}

type ServerConfig struct {
	Port        string
	Host        string
	Environment string
}

type DatabaseConfig struct {
	URL            string
	Host           string
	Port           string
	User           string
	Password       string
	Database       string
	MaxConnections int
	MinConnections int
}

type RedisConfig struct {
	Host     string
	Port     string
	Password string
	DB       int
}

type QueueConfig struct {
	Concurrency       int
	GoWorkerCount     int
	PythonWorkerCount int
}

type AuthConfig struct {
	JWTSecret      string
	JWTExpiryHours int
	BcryptCost     int
}

type GeminiConfig struct {
	APIKey string
}

type StorageConfig struct {
	Type   string
	Path   string
	Bucket string
}

type RateLimitConfig struct {
	Free   int
	Pro    int
	Window time.Duration
}

type LoggingConfig struct {
	Level  string
	Format string
}

func Load() (*Config, error) {
	// Load .env file if exists
	if err := godotenv.Load("config/.env"); err != nil {
		fmt.Println("Warning: .env file not found, using environment variables")
	}

	cfg := &Config{
		Server: ServerConfig{
			Port:        getEnv("API_PORT", "8080"),
			Host:        getEnv("API_HOST", "0.0.0.0"),
			Environment: getEnv("ENVIRONMENT", "development"),
		},
		Database: DatabaseConfig{
			URL:            getEnv("DATABASE_URL", ""),
			Host:           getEnv("DB_HOST", "localhost"),
			Port:           getEnv("DB_PORT", "5432"),
			User:           getEnv("DB_USER", "postgres"),
			Password:       getEnv("DB_PASSWORD", "postgres"),
			Database:       getEnv("DB_NAME", "article_extraction"),
			MaxConnections: getEnvInt("DB_MAX_CONNECTIONS", 25),
			MinConnections: getEnvInt("DB_MIN_CONNECTIONS", 5),
		},
		Redis: RedisConfig{
			Host:     getEnv("REDIS_HOST", "localhost"),
			Port:     getEnv("REDIS_PORT", "6379"),
			Password: getEnv("REDIS_PASSWORD", ""),
			DB:       getEnvInt("REDIS_DB", 0),
		},
		Queue: QueueConfig{
			Concurrency:       getEnvInt("QUEUE_CONCURRENCY", 10),
			GoWorkerCount:     getEnvInt("QUEUE_GO_WORKER_COUNT", 5),
			PythonWorkerCount: getEnvInt("QUEUE_PYTHON_WORKER_COUNT", 2),
		},
		Auth: AuthConfig{
			JWTSecret:      getEnv("JWT_SECRET", ""),
			JWTExpiryHours: getEnvInt("JWT_EXPIRY_HOURS", 24),
			BcryptCost:     getEnvInt("BCRYPT_COST", 10),
		},
		Gemini: GeminiConfig{
			APIKey: getEnv("GEMINI_API_KEY", ""),
		},
		Storage: StorageConfig{
			Type:   getEnv("STORAGE_TYPE", "local"),
			Path:   getEnv("STORAGE_PATH", "./storage"),
			Bucket: getEnv("STORAGE_BUCKET", ""),
		},
		RateLimit: RateLimitConfig{
			Free:   getEnvInt("RATE_LIMIT_FREE", 10),
			Pro:    getEnvInt("RATE_LIMIT_PRO", 100),
			Window: time.Duration(getEnvInt("RATE_LIMIT_WINDOW", 60)) * time.Second,
		},
		Logging: LoggingConfig{
			Level:  getEnv("LOG_LEVEL", "info"),
			Format: getEnv("LOG_FORMAT", "json"),
		},
	}

	if err := cfg.Validate(); err != nil {
		return nil, err
	}

	return cfg, nil
}

func (c *Config) Validate() error {
	if c.Auth.JWTSecret == "" {
		return fmt.Errorf("JWT_SECRET is required")
	}
	if c.Gemini.APIKey == "" {
		return fmt.Errorf("GEMINI_API_KEY is required")
	}
	if c.Database.URL == "" && c.Database.Host == "" {
		return fmt.Errorf("database configuration is required")
	}
	return nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		var intVal int
		fmt.Sscanf(value, "%d", &intVal)
		return intVal
	}
	return defaultValue
}


