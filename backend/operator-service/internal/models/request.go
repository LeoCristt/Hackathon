package models

import "time"

type Request struct {
	ID        uint      `json:"id"`
	Content   string    `gorm:"type:text;not null" json:"content"`
	CreatedAt time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"createdAt"`

	DomainID uint   `gorm:"type:integer;not null" json:"domain_id"`
	Domain   Domain `gorm:"foreignKey:DomainID" json:"domain"`

	UserID *uint `gorm:"type:integer" json:"user_id"`
	User   User  `gorm:"foreignKey:UserID" json:"user"`
}
