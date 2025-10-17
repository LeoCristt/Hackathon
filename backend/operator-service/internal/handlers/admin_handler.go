package handlers

import (
	"net/http"
	"operator-service/internal/models"
	"operator-service/internal/service"

	"github.com/gin-gonic/gin"
)

type AdminHandler struct {
	AdminService *service.AdminService
}

func NewAdminHandler(AdminService *service.AdminService) *AdminHandler {
	return &AdminHandler{AdminService: AdminService}
}

func (h *AdminHandler) CreateRequest(c *gin.Context) {
	var req models.CreateRequest
	if err := c.BindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}

	roleVal, exists := c.Get("role")
	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid role"})
		return
	}
	role := roleVal.(string)

	userIdVal, exists := c.Get("userID")
	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid user id"})
		return
	}
	userID := userIdVal.(uint)

	req.UserID = &userID

	createdReq, err := h.AdminService.CreateRequest(&req, role)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"request": createdReq})
}

func (h *AdminHandler) GetAllRequests(c *gin.Context) {
	roleVal, exists := c.Get("role")
	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid role"})
		return
	}
	role := roleVal.(string)

	requests, err := h.AdminService.GetAllRequests(role)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, gin.H{"requests": requests})
}
