package database

import (
	"context"
	"fmt"
	"time"

	"github.com/Denter-/article-extraction/api/internal/config"
	"github.com/jackc/pgx/v5/pgxpool"
)

func NewPostgresPool(cfg *config.DatabaseConfig) (*pgxpool.Pool, error) {
	var connString string
	if cfg.URL != "" {
		connString = cfg.URL
	} else {
		connString = fmt.Sprintf(
			"host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
			cfg.Host, cfg.Port, cfg.User, cfg.Password, cfg.Database,
		)
	}

	poolConfig, err := pgxpool.ParseConfig(connString)
	if err != nil {
		return nil, fmt.Errorf("unable to parse database config: %w", err)
	}

	poolConfig.MaxConns = int32(cfg.MaxConnections)
	poolConfig.MinConns = int32(cfg.MinConnections)
	poolConfig.MaxConnLifetime = time.Hour
	poolConfig.MaxConnIdleTime = 30 * time.Minute

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	pool, err := pgxpool.NewWithConfig(ctx, poolConfig)
	if err != nil {
		return nil, fmt.Errorf("unable to create connection pool: %w", err)
	}

	// Test connection
	if err := pool.Ping(ctx); err != nil {
		return nil, fmt.Errorf("unable to ping database: %w", err)
	}

	return pool, nil
}


