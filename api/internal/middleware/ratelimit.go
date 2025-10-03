package middleware

import (
	"context"
	"fmt"
	"time"

	"github.com/Denter-/article-extraction/api/internal/config"
	"github.com/Denter-/article-extraction/api/internal/models"
	"github.com/gofiber/fiber/v2"
	"github.com/redis/go-redis/v9"
)

func RateLimit(rdb *redis.Client, cfg *config.RateLimitConfig) fiber.Handler {
	return func(c *fiber.Ctx) error {
		user, ok := c.Locals("user").(*models.User)
		if !ok {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error": "Unauthorized",
			})
		}

		// Determine rate limit based on tier
		var limit int
		switch user.Tier {
		case models.TierFree:
			limit = cfg.Free
		case models.TierPro:
			limit = cfg.Pro
		default:
			limit = cfg.Pro
		}

		key := fmt.Sprintf("ratelimit:%s:%s", user.ID, time.Now().Format("2006-01-02-15"))
		ctx := context.Background()

		// Increment counter
		count, err := rdb.Incr(ctx, key).Result()
		if err != nil {
			// Don't block on Redis errors
			return c.Next()
		}

		// Set expiry on first request
		if count == 1 {
			rdb.Expire(ctx, key, cfg.Window)
		}

		if count > int64(limit) {
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"error":       "Rate limit exceeded",
				"limit":       limit,
				"window":      cfg.Window.String(),
				"retry_after": cfg.Window.Seconds(),
			})
		}

		// Add rate limit headers
		c.Set("X-RateLimit-Limit", fmt.Sprintf("%d", limit))
		c.Set("X-RateLimit-Remaining", fmt.Sprintf("%d", limit-int(count)))

		return c.Next()
	}
}


