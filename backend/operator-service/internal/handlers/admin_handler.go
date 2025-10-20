package handlers

import (
	"net/http"
	"operator-service/internal/models"
	"operator-service/internal/service"
	"strconv"

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

func (h *AdminHandler) ApproveRequest(c *gin.Context) {
	roleVal, exists := c.Get("role")
	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid role"})
	}
	role := roleVal.(string)

	var input struct {
		DomainID          uint     `json:"domain_id"`
		AllowedOrigins    []string `json:"allowed_origins"`
		IsActive          bool     `json:"isActive"`
		MaxRequestsPerDay int      `json:"max_requests"`
		AiModel           string   `json:"ai_model"`
	}
	if err := c.BindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid input data"})
		return
	}

	domain := models.Domain{
		ID:                input.DomainID,
		AllowedOrigins:    input.AllowedOrigins,
		IsActive:          input.IsActive,
		MaxRequestsPerDay: input.MaxRequestsPerDay,
		AiModel:           input.AiModel,
	}

	approvedRequest, err := h.AdminService.ApproveRequest(role, &domain)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "didnt approve"})
		return
	}

	c.JSON(http.StatusAccepted, gin.H{"approvedRequest": approvedRequest})
}

func (h *AdminHandler) GetDomain(c *gin.Context) {
	roleVal, exists := c.Get("role")
	if !exists {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid role to get domain"})
		return
	}
	role := roleVal.(string)

	requestIDstr := c.Param("id")
	requestID, err := strconv.Atoi(requestIDstr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "theres no request id"})
		return
	}

	domain, err := h.AdminService.GetDomain(role, uint(requestID))
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "didnt get domain"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"domain": domain})
}
