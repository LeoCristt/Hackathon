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

func (s *AdminService) ApproveRequest(role string, domain *models.Domain) (*models.Domain, error) {
	if role != "admin" {
		return nil, errors.New("u should be admin to approve request")
	}

	approved, err := s.repo.ApproveRequest(domain)
	if err != nil {
		return nil, errors.New("didnt approve")
	}

	return approved, nil
}

func (s *AdminService) GetDomain(role string, requestID uint) (*models.Request, error) {
	if role != "admin" {
		return nil, errors.New("u should be admin to get info about domain")
	}

	domain, err := s.repo.GetDomain(requestID)
	if err != nil {
		return nil, errors.New("request not found")
	}

	return domain, nil
}
