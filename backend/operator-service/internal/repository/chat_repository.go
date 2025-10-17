package repository

import (
	"operator-service/internal/models"
	"time"

	"gorm.io/gorm"
)

type ChatRepository struct {
	db *gorm.DB
}

func NewChatRepository(db *gorm.DB) *ChatRepository {
	return &ChatRepository{db: db}
}

func (r *ChatRepository) GetChatByID(chatID string) (*models.Chat, error) {
	var chat models.Chat
	err := r.db.Where("id = ?", chatID).First(&chat).Error
	if err != nil {
		return nil, err
	}
	return &chat, nil
}

func (r *ChatRepository) CreateChat(chat *models.Chat) error {
	return r.db.Create(chat).Error
}

func (r *ChatRepository) CreateMessage(msg *models.Message) error {
	return r.db.Create(msg).Error
}

func (r *ChatRepository) UpdateChatTimestamp(chatID string) error {
	return r.db.Model(&models.Chat{}).
		Where("id = ?", chatID).
		Update("updated_at", time.Now()).Error
}

func (r *ChatRepository) GetLastMessageSequence(chatID string) (int, error) {
	var msg models.Message
	err := r.db.Where("chat_id = ?", chatID).Order("message_sequence desc").First(&msg).Error
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			return 0, nil
		}
		return 0, err
	}
	return msg.MessageSequence, nil
}

func (r *ChatRepository) GetAllChatsByOperator(userID uint) ([]models.Chat, error) {
	var chats []models.Chat
	err := r.db.Order("updated_at DESC").Find(&chats).Error
	return chats, err
}

func (r *ChatRepository) GetChatSummaries() ([]models.GetChatSummary, error) {
	var summaries []models.GetChatSummary

	subQuery := r.db.Table("messages").
		Select("DISTINCT ON (chat_id) chat_id, message, created_at").
		Order("chat_id, message_sequence DESC")

	err := r.db.Table("chats").
		Select("chats.id as chat_id, sub.message as last_message, chats.updated_at").
		Joins("LEFT JOIN (?) as sub ON chats.id = sub.chat_id", subQuery).
		Order("chats.updated_at DESC").
		Scan(&summaries).Error

	if err != nil {
		return nil, err
	}

	return summaries, nil
}
