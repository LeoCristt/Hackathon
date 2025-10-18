package service

import (
	"operator-service/internal/models"
	"operator-service/internal/repository"
)

type UserService struct {
	repo *repository.UserRepository
}

func NewUserService(repo *repository.UserRepository) *UserService {
	return &UserService{repo: repo}
}

func (s *UserService) CreateRequest(req *models.Request) (*models.Request, error) {
	if err := s.repo.CreateRequest(req); err != nil {
		return nil, err
	}
	return req, nil
}
