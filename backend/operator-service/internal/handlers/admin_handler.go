package handlers

import (
	"net/http"
	"operator-service/internal/service"

	"github.com/gin-gonic/gin"
)

type AdminHandler struct {
	AdminService *service.AdminService
}

func NewAdminHandler(AdminService *service.AdminService) *AdminHandler {
	return &AdminHandler{AdminService: AdminService}
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
