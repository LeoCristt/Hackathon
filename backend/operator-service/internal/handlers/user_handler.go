package handlers

import (
	"net/http"
	"operator-service/internal/models"
	"operator-service/internal/service"
	"strconv"

	"github.com/gin-gonic/gin"
)

type UserHandler struct {
	UserService *service.UserService
}

func NewUserHandler(UserService *service.UserService) *UserHandler {
	return &UserHandler{UserService: UserService}
}

func (h *UserHandler) CreateRequest(c *gin.Context) {
	var input struct {
		Content string `json:"content"`
		Domain  string `json:"domain"`
	}
	if err := c.BindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}

	existingDomain, err := h.UserService.FindExistingDomain(input.Domain)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	userIdVal, exists := c.Get("userID")
	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid user id"})
		return
	}
	userID := uint(userIdVal.(float64))

	req := models.Request{
		Content:  input.Content,
		UserID:   &userID,
		DomainID: existingDomain,
	}

	createdReq, err := h.UserService.CreateRequest(&req)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"request": createdReq})
}

func (h *UserHandler) UserProfile(c *gin.Context) {
	_, exists := c.Get("role")
	if !exists {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "no role"})
		return
	}

	userIDStr := c.Param("id")
	userID, err := strconv.Atoi(userIDStr)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "no id in params"})
		return
	}

	profile, err := h.UserService.UserProfile(uint(userID))
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "cant get user profile"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"profile": profile})
}
