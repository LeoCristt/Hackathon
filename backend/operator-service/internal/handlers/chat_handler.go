package handlers

import (
	"encoding/json"
	"log"
	"net/http"
	"operator-service/internal/service"
	"operator-service/internal/utils"
	"time"

	"github.com/gin-gonic/gin"
)

type ChatHandler struct {
	chatService *service.ChatService
}

func NewChatHandler(chatService *service.ChatService) *ChatHandler {
	return &ChatHandler{chatService: chatService}
}

func (h *ChatHandler) ConsumeChatQueue(connStr, queueName string) error {
	return utils.RabbitMQConsumer(connStr, queueName, func(msg []byte) error {
		var payload struct {
			ChatID          string    `json:"chatId"`
			MessageSequence int       `json:"sequence"`
			Username        string    `json:"username"`
			Message         string    `json:"message"`
			IsManager       bool      `json:"isManager"`
			CreatedAt       time.Time `json:"timestamp"`
		}

		if err := json.Unmarshal(msg, &payload); err != nil {
			log.Printf("failed to parse message from queue %s: %v", queueName, err)
			return err
		}

		return h.chatService.SaveMessage(
			payload.ChatID,
			payload.Username,
			payload.Message,
			payload.IsManager,
			payload.CreatedAt,
		)
	})
}

func (h *ChatHandler) GetAllChats(c *gin.Context) {
	roleVal, exists := c.Get("role")
	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid role"})
		return
	}
	role := roleVal.(string)

	userIdVal, exists := c.Get("userID")
	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}
	userID := uint(userIdVal.(float64))

	chats, err := h.chatService.GetAllChats(userID, role)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"chats": chats})
}

func (h *ChatHandler) GetChatSummaries(c *gin.Context) {
	roleVal, exists := c.Get("role")
	if !exists {
		c.JSON(http.StatusForbidden, gin.H{"error": "forbidden"})
		return
	}
	role := roleVal.(string)

	summaries, err := h.chatService.GetChatSummaries(role)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, summaries)
}
