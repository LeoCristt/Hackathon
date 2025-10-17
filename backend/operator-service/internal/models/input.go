package models

import "time"

type CreateUser struct {
	Email      string `json:"email"`
	Password   string `json:"password"`
	FirstName  string `json:"first_name"`
	MiddleName string `json:"middle_name"`
	LastName   string `json:"last_name"`
	RoleID     uint   `json:"role_id"`
}

type CreateRequest struct {
	ID        uint      `json:"id"`
	Content   string    `gorm:"type:text; not null" json:"content"`
	CreatedAt time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"createdAt"`

	UserID *uint `gorm:"type:integer" json:"user_id"`
	User   User  `gorm:"foreignKey:UserID" json:"user"`
}

type GetChatSummary struct {
	ChatID      string    `json:"chatID"`
	LastMessage string    `json:"lastMessage"`
	UpdatedAt   time.Time `json:"updatedAt"`
}
