package service

import (
	"errors"
	"operator-service/internal/models"
	"operator-service/internal/repository"

	"gorm.io/gorm"
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

func (s *UserService) FindExistingDomain(domain string) (uint, error) {
	findDomain, err := s.repo.FindExistingDomain(domain)
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			newDomain := models.Domain{
				Domain:   domain,
				IsActive: false,
			}
			if err := s.repo.CreateDomain(&newDomain); err != nil {
				return 0, err
			}
			return newDomain.ID, nil
		}
		return 0, err
	}

	return findDomain.ID, nil
}

func (s *UserService) UserProfile(userID uint) (*models.User, error) {
	profile, err := s.repo.UserProfile(userID)
	if err != nil {
		return nil, err
	}

	return profile, nil
}
