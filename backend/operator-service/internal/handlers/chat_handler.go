package handlers

import (
	"encoding/json"
	"log"
	"net/http"
	"operator-service/internal/service"

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
				ChatID          uint `json:"chat_id"`
				ClientID        uint `json:"client_id"`
				MessageSequence uint `json:"message_sequence"`
				Message         struct {
					Username string `json:"username"`
					Content  string `json:"content"`
				} `json:"message"`
			}

			if err := json.Unmarshal(d.Body, &payload); err != nil {
				log.Printf("failed to parse message from queue %s: %v", queueName, err)
				d.Nack(false, true)
				continue
			}

			if err := h.chatService.SaveMessage(
				payload.ChatID,
				payload.ClientID,
				payload.MessageSequence,
				payload.Message.Username,
				payload.Message.Content,
			); err != nil {
				log.Printf("failed to save message from queue %s: %v", queueName, err)
				d.Nack(false, true)
			} else {
				log.Printf("message saved successfully from queue %s: chat %d", queueName, payload.ChatID)
				d.Ack(false)
			}
		}
	}()

	log.Printf("waiting for messages...")
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
	userID := userIdVal.(uint)

	chats, err := h.chatService.GetAllChats(userID, role)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"chats": chats})
}
