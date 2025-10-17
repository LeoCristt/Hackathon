package service

import (
	"fmt"
	"operator-service/internal/models"
	"operator-service/internal/repository"
)

type ChatService struct {
	repo *repository.ChatRepository
}

func NewChatService(repo *repository.ChatRepository) *ChatService {
	return &ChatService{repo: repo}
}

func (s *ChatService) SaveMessage(chatID, clientID, operatorID uint, username, content string) error {
	var chat *models.Chat
	var err error

	if chatID != 0 {
		chat, err = s.repo.GetChatByID(chatID)
		if err != nil {
			return err
		}
	} else {
		chat = &models.Chat{
			ClientID:   clientID,
			OperatorID: &operatorID,
		}
		if err := s.repo.CreateChat(chat); err != nil {
			return err
		}
	}

	lastSeq, err := s.repo.GetLastMessageSequence(chat.ID)
	if err != nil {
		return err
	}

	message := &models.Message{
		ChatID:          chat.ID,
		Username:        username,
		Content:         content,
		MessageSequence: lastSeq + 1,
	}

	if err := s.repo.CreateMessage(message); err != nil {
		return err
	}

	return s.repo.UpdateChatTimestamp(chat.ID)
}

func (s *ChatService) GetAllChats(userID uint, role string) ([]models.Chat, error) {
	if role == "operator" {
		return s.repo.GetAllChatsByOperator(userID)
	}
	return nil, fmt.Errorf("unknown role: %s", role)
}
