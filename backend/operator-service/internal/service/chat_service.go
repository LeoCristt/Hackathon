package service

import (
	"fmt"
	"operator-service/internal/models"
	"operator-service/internal/repository"
	"strings"
	"time"

	"gorm.io/gorm"
)

type ChatService struct {
	repo *repository.ChatRepository
}

func NewChatService(repo *repository.ChatRepository) *ChatService {
	return &ChatService{repo: repo}
}

func (s *ChatService) SaveMessage(chatID string, username, messageText string, createdAt time.Time) error {
	if chatID == "" {
		return fmt.Errorf("chatID cannot be empty")
	}

	// Получаем чат, если нет — создаём
	chat, err := s.repo.GetChatByID(chatID)
	if err != nil {
		if err == gorm.ErrRecordNotFound {
			chat = &models.Chat{
				ID: chatID,
			}
			if err := s.repo.CreateChat(chat); err != nil {
				return fmt.Errorf("failed to create chat with ID %s: %w", chatID, err)
			}
		} else {
			return fmt.Errorf("failed to get chat with ID %s: %w", chatID, err)
		}
	}

	// Получаем последнюю последовательность сообщений
	lastSeq, err := s.repo.GetLastMessageSequence(chatID)
	if err != nil {
		return fmt.Errorf("failed to get last message sequence for chat %s: %w", chatID, err)
	}

	for {
		message := &models.Message{
			ChatID:          chat.ID,
			Username:        username,
			Message:         messageText,
			MessageSequence: lastSeq + 1,
			CreatedAt:       createdAt,
		}

		err := s.repo.CreateMessage(message)
		if err != nil {
			if isUniqueConstraintError(err) {
				// Если последовательность уже занята, увеличиваем и пробуем снова
				lastSeq++
				continue
			}
			return fmt.Errorf("failed to create message for chat %s: %w", chatID, err)
		}
		break
	}

	// Обновляем timestamp чата
	if err := s.repo.UpdateChatTimestamp(chat.ID); err != nil {
		return fmt.Errorf("failed to update chat timestamp for chat %s: %w", chatID, err)
	}

	return nil
}

// Проверка ошибки уникального индекса для Postgres
func isUniqueConstraintError(err error) bool {
	return err != nil && strings.Contains(err.Error(), "idx_chat_sequence")
}

func (s *ChatService) GetAllChats(userID uint, role string) ([]models.Chat, error) {
	if role == "operator" {
		return s.repo.GetAllChatsByOperator(userID)
	}
	return nil, fmt.Errorf("unknown role: %s", role)
}
