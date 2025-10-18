package models

import "time"

type Message struct {
	ID              uint      `gorm:"primaryKey" json:"id"`
	Username        string    `gorm:"type:varchar(30);not null" json:"username"`
	Message         string    `gorm:"type:text;not null" json:"message"`
	MessageSequence int       `gorm:"not null;index:idx_chat_sequence,unique" json:"sequence"`
	CreatedAt       time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"timestamp"`

	ChatID string `gorm:"type:varchar(50);not null;index:idx_chat_sequence,unique" json:"chatId"`
	Chat   Chat   `gorm:"foreignKey:ChatID" json:"chat"`
}
