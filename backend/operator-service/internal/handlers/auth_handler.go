package handlers

import (
	"net/http"
	"operator-service/internal/models"
	"operator-service/internal/service"

	"github.com/gin-gonic/gin"
)

type AuthHandler struct {
	userService *service.UserService
}

func NewAuthHandler(userService *service.UserService) *AuthHandler {
	return &AuthHandler{userService: userService}
}

func (h *AuthHandler) Register(c *gin.Context) {
	var input models.CreateUser
	if err := c.BindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request"})
		return
	}

	res := &models.User{
		Email:      input.Email,
		Password:   input.Password,
		FirstName:  input.FirstName,
		MiddleName: input.MiddleName,
		LastName:   input.LastName,
		RoleID:     input.RoleID,
	}

	user, err := h.userService.Register(res)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"id": user.ID, "email": user.Email})
}

func (h *AuthHandler) Login(c *gin.Context) {
	var req struct {
		Email    string `json:"email"`
		Password string `json:"password"`
	}
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request"})
		return
	}

	user, token, refresh, err := h.userService.Login(req.Email, req.Password)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}

	c.SetCookie(
		"refresh_token",
		refresh,
		60*60*24*7,
		"/",
		"",
		false,
		true,
	)

	c.JSON(http.StatusOK, gin.H{
		"message": "login successful",
		"user": gin.H{
			"id":    user.ID,
			"email": user.Email,
		},
		"token":   token,
		"refresh": refresh,
	})
}

func (h *AuthHandler) Logout(c *gin.Context) {
	c.SetCookie("refresh_token", "", -1, "/", "", true, true)

	c.JSON(http.StatusOK, gin.H{
		"message": "successfully logout",
	})
}

func (h *AuthHandler) Refresh(c *gin.Context) {
	refreshString, err := c.Cookie("refresh_token")
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "no refresh"})
		return
	}

	newAccess, err := h.userService.Refresh(refreshString)
	if err != nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"access_token": newAccess,
	})
}
