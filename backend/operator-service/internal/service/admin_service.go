package service

import (
	"errors"
	"operator-service/internal/models"
	"operator-service/internal/repository"
)

type AdminService struct {
	repo *repository.AdminRepository
}

func NewAdminService(repo *repository.AdminRepository) *AdminService {
	return &AdminService{repo: repo}
}

func (s *AdminService) GetAllRequests(role string) ([]models.Request, error) {
	if role != "admin" {
		return nil, errors.New("u should be admin to get all requests")
	}

	var requests []models.Request
	if err := s.repo.GetAllRequests(&requests); err != nil {
		return nil, err
	}

	return requests, nil
}
