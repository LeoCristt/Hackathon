package service

import (
	"operator-service/internal/models"
	"operator-service/internal/repository"
)

type UserService struct {
	repo *repository.UserRepository
}

func NewUserService(repo *repository.UserRepository) *UserService {
	return &UserService{repo: repo}
}

func (s *UserService) CreateRequest(req *models.Request) (*models.Request, error) {
	if err := s.repo.CreateRequest(req); err != nil {
		return nil, err
	}

	return user, nil
}

func (s *UserService) Login(email, password string) (*models.User, string, string, error) {
	user, err := s.repo.GetByEmail(email)
	if err != nil {
		return nil, "", "", errors.New("user not found")
	}

	if !utils.CheckPassword(user.Password, password) {
		return nil, "", "", errors.New("invalid password")
	}

	// Create username in format "Оператор {FirstName}"
	username := "Оператор " + user.FirstName

	accessToken := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"id":       user.ID,
		"role":     user.Role.Name,
		"username": username,
		"exp":      time.Now().Add(time.Minute * 15).Unix(),
	})
	refreshToken := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"id":       user.ID,
		"role":     user.Role.Name,
		"username": username,
		"exp":      time.Now().Add(time.Hour * 24 * 7).Unix(),
	})

	accessString, err := accessToken.SignedString([]byte(os.Getenv("JWT_SECRET")))
	if err != nil {
		return nil, "", "", err
	}
	refreshString, err := refreshToken.SignedString([]byte(os.Getenv("JWT_REFRESH_SECRET")))
	if err != nil {
		return nil, "", "", err
	}

	return user, accessString, refreshString, nil
}

func (s *UserService) Refresh(refreshString string) (string, error) {
	token, err := jwt.Parse(refreshString, func(token *jwt.Token) (interface{}, error) {
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return []byte(os.Getenv("JWT_REFRESH_SECRET")), nil
	})
	if err != nil || !token.Valid {
		return "", errors.New("invalid refresh token")
	}

	claims, ok := token.Claims.(jwt.MapClaims)
	if !ok {
		return "", errors.New("invalid token claims")
	}

	userID, ok := claims["id"].(float64)
	if !ok {
		return "", errors.New("invalid user id in token")
	}
	role, ok := claims["role"].(string)
	if !ok {
		return "", errors.New("invalid role in token")
	}
	username, ok := claims["username"].(string)
	if !ok {
		return "", errors.New("invalid username in token")
	}

	newAccess := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"id":       uint(userID),
		"role":     role,
		"username": username,
		"exp":      time.Now().Add(15 * time.Minute).Unix(),
	})

	newAccessString, err := newAccess.SignedString([]byte(os.Getenv("JWT_SECRET")))
	if err != nil {
		return "", fmt.Errorf("failed to sign access token: %w", err)
	}

	return newAccessString, nil
}
