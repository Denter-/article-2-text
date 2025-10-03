package handlers

import (
	"github.com/Denter-/article-extraction/api/internal/service"
	ws "github.com/Denter-/article-extraction/api/internal/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/websocket/v2"
)

type WebSocketHandler struct {
	hub     *ws.Hub
	authSvc *service.AuthService
}

func NewWebSocketHandler(hub *ws.Hub, authSvc *service.AuthService) *WebSocketHandler {
	return &WebSocketHandler{
		hub:     hub,
		authSvc: authSvc,
	}
}

func (h *WebSocketHandler) HandleConnection(c *fiber.Ctx) error {
	// Check if WebSocket upgrade
	if !websocket.IsWebSocketUpgrade(c) {
		return c.Status(fiber.StatusBadRequest).JSON(fiber.Map{
			"error": "WebSocket upgrade required",
		})
	}

	// Get token from query parameter for WebSocket auth
	token := c.Query("token")
	if token == "" {
		// Try from header as fallback
		token = c.Get("Authorization")
		if len(token) > 7 && token[:7] == "Bearer " {
			token = token[7:]
		}
	}

	if token == "" {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "Token required",
		})
	}

	// Verify token
	user, err := h.authSvc.ValidateToken(token)
	if err != nil {
		return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
			"error": "Invalid token",
		})
	}

	// Upgrade to WebSocket
	return websocket.New(func(conn *websocket.Conn) {
		userID := user.ID.String()

		// Register client
		h.hub.RegisterClient(userID, conn)
		defer h.hub.UnregisterClient(userID, conn)

		// Send welcome message
		conn.WriteJSON(fiber.Map{
			"type":    "connected",
			"message": "WebSocket connection established",
			"user_id": userID,
		})

		// Keep connection alive and handle disconnect
		for {
			_, _, err := conn.ReadMessage()
			if err != nil {
				break
			}
		}
	})(c)
}
