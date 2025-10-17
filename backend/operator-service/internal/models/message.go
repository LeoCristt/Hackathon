package models

import "time"

type Message struct {
	ID              uint      `gorm:"primaryKey" json:"id"`
	Username        string    `gorm:"type:varchar(30); not null" json:"username"`
	Content         string    `gorm:"type:text; not null" json:"content"`
	MessageSequence int       `gorm:"type:integer; not null; unique" json:"message_sequence"`
	CreatedAt       time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"createdAt"`

	ChatID uint `gorm:"type:integer; not null" json:"chat_id"`
	Chat   Chat `gorm:"foreignKey:ChatID" json:"chat"`
}
