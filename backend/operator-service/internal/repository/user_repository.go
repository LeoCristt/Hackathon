package repository

import (
	"operator-service/internal/models"

	"gorm.io/gorm"
)

type UserRepository struct {
	db *gorm.DB
}

func NewUserRepository(db *gorm.DB) *UserRepository {
	return &UserRepository{db: db}
}

func (r *UserRepository) CreateRequest(req *models.Request) error {
	return r.db.Create(req).Error
}

func (r *UserRepository) FindExistingDomain(domainName string) (*models.Domain, error) {
	var domain models.Domain
	if err := r.db.Where("domain = ?", domainName).First(&domain).Error; err != nil {
		return nil, err
	}

	return &domain, nil
}

func (r *UserRepository) CreateDomain(domain *models.Domain) error {
	return r.db.Create(domain).Error
}

func (r *UserRepository) UserProfile(userID uint) (*models.User, error) {
	var user models.User

	if err := r.db.Preload("Role").First(&user, userID).Error; err != nil {
		return nil, err
	}

	return &user, nil
}
