package models

import (
	"time"

	"github.com/lib/pq"
)

type Domain struct {
	ID                uint           `json:"id"`
	Domain            string         `gorm:"type:varchar(255); not null" json:"domain"`
	AiModel           string         `gorm:"type:varchar(100); not null; default:gpt-4" json:"ai_model"`
	IsActive          bool           `gorm:"type:boolean; default:true" json:"isActive"`
	MaxRequestsPerDay int            `gorm:"type:integer; default:100" json:"max_requests"`
	AllowedOrigins    pq.StringArray `gorm:"type:text[]" json:"allowed_origins"`
	CreatedAt         time.Time      `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"createdAt"`
	UpdatedAt         time.Time      `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"updatedAt"`
}

func (Domain) TableName() string {
	return "widget_domains"
}
