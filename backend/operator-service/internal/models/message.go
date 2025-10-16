package models

type Message struct {
	ID     uint `gorm:"primaryKey" json:"id"`
	ChatID uint `gorm:"type:integer; not null" json:"chat_id"`
	Chat   Chat `gorm:"foreignKey:ChatID" json:"chat"`
}
