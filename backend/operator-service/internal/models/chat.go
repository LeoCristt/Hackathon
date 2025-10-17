package models

import "time"

type Chat struct {
	ID        string    `gorm:"primaryKey" json:"id"`
	CreatedAt time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"createdAt"`
	UpdatedAt time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"updatedAt"`
}
