package routes

import (
	"operator-service/internal/handlers"
	"operator-service/internal/utils"

	"github.com/gin-gonic/gin"
)

func RegisterAuthRoutes(r *gin.Engine, authHandler *handlers.AuthHandler) {
	api := r.Group("/api/auth")
	{
		api.POST("/register", utils.AuthMiddleware(), authHandler.Register)
		api.POST("/login", authHandler.Login)
	}
}
