package handlers

import (
	"encoding/json"
	"log"
	"net/http"
	"operator-service/internal/service"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/streadway/amqp"
)

type ChatHandler struct {
	chatService *service.ChatService
}

func NewChatHandler(chatService *service.ChatService) *ChatHandler {
	return &ChatHandler{chatService: chatService}
}

func (h *ChatHandler) ConsumeRabbitMQ(connStr, queueName string) error {
	conn, err := amqp.Dial(connStr)
	if err != nil {
		log.Fatalf("failed to connect to RabbitMQ: %v", err)
	}
	defer conn.Close()

	ch, err := conn.Channel()
	if err != nil {
		log.Fatalf("failed to open channel: %v", err)
		return err
	}
	defer ch.Close()

	_, err = ch.QueueInspect(queueName)
	if err != nil {
		log.Printf("Queue %s does not exist: %v", queueName, err)
		return err
	}

	msgs, err := ch.Consume(
		queueName,
		"",
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		log.Fatalf("failed to register consumer: %v", err)
	}

	forever := make(chan bool)

	go func() {
		for d := range msgs {
			var payload struct {
				ChatID          string    `json:"chatId"`
				MessageSequence int       `json:"sequence"`
				Username        string    `json:"username"`
				Message         string    `json:"message"`
				IsManager       bool      `json:"isManager"`
				CreatedAt       time.Time `json:"timestamp"`
			}

			if err := json.Unmarshal(d.Body, &payload); err != nil {
				log.Printf("failed to parse message from queue %s: %v", queueName, err)
				continue
			}

			err := h.chatService.SaveMessage(
				payload.ChatID,
				payload.Username,
				payload.Message,
				payload.IsManager,
				payload.CreatedAt,
			)
			if err != nil {
				log.Printf("failed to save message from queue %s: %v", queueName, err)
			} else {
				log.Printf("message saved successfully from queue %s: chat %s", queueName, payload.ChatID)
			}

		}
	}()

	log.Printf("waiting for messages in queue %s...", queueName)
	<-forever

	return nil
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
