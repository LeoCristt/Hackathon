package repository

import (
	"errors"
	"operator-service/internal/models"
	"time"

	"gorm.io/gorm"
)

type AdminRepository struct {
	db *gorm.DB
}

func NewAdminRepository(db *gorm.DB) *AdminRepository {
	return &AdminRepository{db: db}
}

func (r *AdminRepository) GetAllRequests(requests *[]models.Request) error {
	return r.db.Preload("Domain").Preload("User").Find(requests).Error
}

func (r *AdminRepository) ApproveRequest(domain *models.Domain) (*models.Domain, error) {
	if err := r.db.Model(&models.Domain{}).Where("id = ?", domain.ID).
		Updates(map[string]interface{}{
			"allowed_origins":      domain.AllowedOrigins,
			"is_active":            domain.IsActive,
			"max_requests_per_day": domain.MaxRequestsPerDay,
			"ai_model":             domain.AiModel,
			"updated_at":           time.Now(),
		}).Error; err != nil {
		return nil, err
	}
	return domain, nil
}

func (r *AdminRepository) GetDomain(requestID uint) (*models.Request, error) {
	var request models.Request
	if err := r.db.Preload("Domain").Preload("User").First(&request, requestID).Error; err != nil {
		return nil, errors.New("request with this domain id not found")
	}

	return &request, nil
}
