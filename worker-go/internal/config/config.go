package config

import (
	"fmt"
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	Database DatabaseConfig
	Redis    RedisConfig
	Gemini   GeminiConfig
	Storage  StorageConfig
	Queue    QueueConfig
}

type DatabaseConfig struct {
	URL      string
	Host     string
	Port     string
	User     string
	Password string
	Database string
}

type RedisConfig struct {
	Host string
	Port string
}

type GeminiConfig struct {
	APIKey string
}

type StorageConfig struct {
	Type   string
	Path   string
	Bucket string
}

type QueueConfig struct {
	Concurrency int
}

func Load() (*Config, error) {
	// Load .env file
	if err := godotenv.Load("config/.env"); err != nil {
		fmt.Println("Warning: .env file not found, using environment variables")
	}

	cfg := &Config{
		Database: DatabaseConfig{
			URL:      getEnv("DATABASE_URL", ""),
			Host:     getEnv("DB_HOST", "localhost"),
			Port:     getEnv("DB_PORT", "5432"),
			User:     getEnv("DB_USER", "postgres"),
			Password: getEnv("DB_PASSWORD", "postgres"),
			Database: getEnv("DB_NAME", "article_extraction"),
		},
		Redis: RedisConfig{
			Host: getEnv("REDIS_HOST", "localhost"),
			Port: getEnv("REDIS_PORT", "6379"),
		},
		Gemini: GeminiConfig{
			APIKey: getEnv("GEMINI_API_KEY", ""),
		},
		Storage: StorageConfig{
			Type:   getEnv("STORAGE_TYPE", "local"),
			Path:   getEnv("STORAGE_PATH", "./storage"),
			Bucket: getEnv("STORAGE_BUCKET", ""),
		},
		Queue: QueueConfig{
			Concurrency: getEnvInt("QUEUE_CONCURRENCY", 10),
		},
	}

	if err := cfg.Validate(); err != nil {
		return nil, err
	}

	return cfg, nil
}

func (c *Config) Validate() error {
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


