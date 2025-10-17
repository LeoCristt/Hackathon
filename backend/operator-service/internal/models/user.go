package models

type User struct {
	ID         uint   `gorm:"primaryKey" json:"id"`
	Email      string `gorm:"type:varchar(50);not null;unique" json:"email" binding:"required,email"`
	Password   string `gorm:"type:varchar(200);not null" json:"password" binding:"required"`
	FirstName  string `gorm:"type:varchar(30);not null" json:"first_name" binding:"required"`
	MiddleName string `gorm:"type:varchar(30)" json:"middle_name" binding:"required"`
	LastName   string `gorm:"type:varchar(30);not null" json:"last_name" binding:"required"`

	RoleID uint `gorm:"not null" json:"role_id"`
	Role   Role `gorm:"foreignKey:RoleID" json:"role"`
}
