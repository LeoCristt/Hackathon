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

func (s *AdminService) CreateRequest(req *models.CreateRequest, role string) (*models.CreateRequest, error) {
	if role != "admin" {
		return nil, errors.New("access denied: only admin can create requests")
	}

	if err := s.repo.CreateRequest(req); err != nil {
		return nil, err
	}
	return req, nil
}

func (s *AdminService) GetAllRequests(role string) ([]models.Request, error) {
	var requests []models.Request
	if err := s.repo.GetAllRequests(&requests); err != nil {
		return nil, err
	}

	return requests, nil
}
