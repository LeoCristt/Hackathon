package service

import (
	"errors"
	"operator-service/internal/models"
	"operator-service/internal/repository"
	"operator-service/internal/utils"
	"os"
	"time"

	"github.com/golang-jwt/jwt"
)

type UserService struct {
	repo *repository.UserRepository
}

func NewUserService(repo *repository.UserRepository) *UserService {
	return &UserService{repo: repo}
}

func (s *UserService) Register(res *models.User, role string) (*models.User, error) {
	if role != "admin" {
		return nil, errors.New("u should be admin")
	}

	hash, err := utils.HashPassword(res.Password)
	if err != nil {
		return nil, err
	}

	user := &models.User{
		Email:      res.Email,
		Password:   hash,
		FirstName:  res.FirstName,
		MiddleName: res.MiddleName,
		LastName:   res.LastName,
		RoleID:     res.RoleID,
	}

	if err := s.repo.Create(user); err != nil {
		return nil, err
	}

	return user, nil
}

func (s *UserService) Login(email, password string) (*models.User, string, error) {
	user, err := s.repo.GetByEmail(email)
	if err != nil {
		return nil, "", errors.New("user not found")
	}

	if !utils.CheckPassword(user.Password, password) {
		return nil, "", errors.New("invalid password")
	}

	accessToken := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"id":   user.ID,
		"role": user.Role.Name,
		"exp":  time.Now().Add(time.Minute * 15).Unix(),
	})

	accessString, err := accessToken.SignedString([]byte(os.Getenv("JWT_SECRET")))
	if err != nil {
		return nil, "", err
	}

	return user, accessString, nil
}
