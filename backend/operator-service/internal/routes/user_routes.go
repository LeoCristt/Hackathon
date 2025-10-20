package routes

import (
	"operator-service/internal/handlers"
	"operator-service/internal/utils"

	"github.com/gin-gonic/gin"
)

func RegisterUserRoutes(r *gin.Engine, UserHandler *handlers.UserHandler) {
	api := r.Group("/api/user")
	{
		api.GET("/profile/:id", utils.AuthMiddleware(), UserHandler.UserProfile)

		api.POST("/requests/add", utils.AuthMiddleware(), UserHandler.CreateRequest)
	}
}
