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

type GetChatSummary struct {
	ChatID      string    `json:"chatID"`
	LastMessage string    `json:"lastMessage"`
	UpdatedAt   time.Time `json:"updatedAt"`
}
