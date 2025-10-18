package repository

import (
	"operator-service/internal/models"

	"gorm.io/gorm"
)

type AdminRepository struct {
	db *gorm.DB
}

func NewAdminRepository(db *gorm.DB) *AdminRepository {
	return &AdminRepository{db: db}
}

func (r *AdminRepository) GetAllRequests(requests *[]models.Request) error {
	return r.db.Find(requests).Error
}
