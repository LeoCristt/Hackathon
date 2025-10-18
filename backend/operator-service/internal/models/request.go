package models

import "time"

type Request struct {
	ID        uint      `json:"id"`
	Content   string    `gorm:"type:text; not null" json:"content"`
	CreatedAt time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"createdAt"`

	UserID *uint `gorm:"type:integer" json:"user_id"`
	User   User  `gorm:"foreignKey:UserID" json:"user"`
}
