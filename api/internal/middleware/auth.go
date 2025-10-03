package middleware

import (
	"strings"

	"github.com/Denter-/article-extraction/api/internal/service"
	"github.com/gofiber/fiber/v2"
)

func AuthRequired(authSvc *service.AuthService) fiber.Handler {
	return func(c *fiber.Ctx) error {
		// Try Bearer token first
		authHeader := c.Get("Authorization")
		if authHeader != "" {
			parts := strings.Split(authHeader, " ")
			if len(parts) == 2 && parts[0] == "Bearer" {
				user, err := authSvc.ValidateToken(parts[1])
				if err == nil {
					c.Locals("user", user)
					return c.Next()
				}
			}
		}

		// Try API key
		apiKey := c.Get("X-API-Key")
		if apiKey != "" {
			user, err := authSvc.ValidateAPIKey(c.Context(), apiKey)
			if err == nil {
				c.Locals("user", user)
				return c.Next()
			}
		}

		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "Unauthorized",
		})
	}
}


