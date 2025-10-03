package websocket

import (
	"sync"

	"github.com/gofiber/websocket/v2"
	"github.com/rs/zerolog/log"
)

// Hub maintains the set of active clients and broadcasts messages to clients
type Hub struct {
	// Registered clients
	clients map[string]map[*websocket.Conn]bool // userID -> connections

	// Inbound messages from clients
	broadcast chan *Message

	// Register requests from clients
	register chan *Client

	// Unregister requests from clients
	unregister chan *Client

	mu sync.RWMutex
}

type Client struct {
	UserID string
	Conn   *websocket.Conn
}

type Message struct {
	UserID  string                 `json:"user_id"`
	Type    string                 `json:"type"`
	Payload map[string]interface{} `json:"payload"`
}

func NewHub() *Hub {
	return &Hub{
		broadcast:  make(chan *Message, 256),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		clients:    make(map[string]map[*websocket.Conn]bool),
	}
}

func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.mu.Lock()
			if h.clients[client.UserID] == nil {
				h.clients[client.UserID] = make(map[*websocket.Conn]bool)
			}
			h.clients[client.UserID][client.Conn] = true
			log.Info().Str("user_id", client.UserID).Msg("WebSocket client connected")
			h.mu.Unlock()

		case client := <-h.unregister:
			h.mu.Lock()
			if connections, ok := h.clients[client.UserID]; ok {
				if _, ok := connections[client.Conn]; ok {
					delete(connections, client.Conn)
					client.Conn.Close()
					if len(connections) == 0 {
						delete(h.clients, client.UserID)
					}
					log.Info().Str("user_id", client.UserID).Msg("WebSocket client disconnected")
				}
			}
			h.mu.Unlock()

		case message := <-h.broadcast:
			h.mu.RLock()
			connections := h.clients[message.UserID]
			h.mu.RUnlock()

			for conn := range connections {
				err := conn.WriteJSON(message)
				if err != nil {
					log.Error().Err(err).Str("user_id", message.UserID).Msg("Failed to send WebSocket message")
					h.unregister <- &Client{UserID: message.UserID, Conn: conn}
				}
			}
		}
	}
}

func (h *Hub) BroadcastToUser(userID string, messageType string, payload map[string]interface{}) {
	h.broadcast <- &Message{
		UserID:  userID,
		Type:    messageType,
		Payload: payload,
	}
}

func (h *Hub) RegisterClient(userID string, conn *websocket.Conn) {
	h.register <- &Client{UserID: userID, Conn: conn}
}

func (h *Hub) UnregisterClient(userID string, conn *websocket.Conn) {
	h.unregister <- &Client{UserID: userID, Conn: conn}
}


