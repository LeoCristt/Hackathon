package models

import "time"

type Chat struct {
	ID        uint      `gorm:"primaryKey" json:"id"`
	CreatedAt time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"createdAt"`
	UpdatedAt time.Time `gorm:"type:timestamp with time zone;default:CURRENT_TIMESTAMP;not null" json:"updatedAt"`

	ClientID uint `gorm:"type:integer; not null; unique" json:"client_id"`
	Client   User `gorm:"foreignKey:ClientID" json:"client"`

	OperatorID *uint `gorm:"type:integer" json:"operator_id"`
	Operator   User  `gorm:"foreignKey:OperatorID" json:"operator"`
}
