package routes

import (
	"operator-service/internal/handlers"
	"operator-service/internal/utils"

	"github.com/gin-gonic/gin"
)

func RegisterAdminRoutes(r *gin.Engine, AdminHandler *handlers.AdminHandler) {
	api := r.Group("/api/admin")
	{
		api.GET("/requests/all", utils.AuthMiddleware(), AdminHandler.GetAllRequests)
		api.GET("/requests/:id/domain", utils.AuthMiddleware(), AdminHandler.GetDomain)

		api.PUT("/requests/approve", utils.AuthMiddleware(), AdminHandler.ApproveRequest)
	}
}
