package routes

import (
	"operator-service/internal/handlers"
	"operator-service/internal/utils"

	"github.com/gin-gonic/gin"
)

func RegisterChatRoutes(r *gin.Engine, chatHandler *handlers.ChatHandler) {
	api := r.Group("/api/chats")
	{
		api.GET("/all", utils.AuthMiddleware(), chatHandler.GetAllChats)
		api.GET("/info", utils.AuthMiddleware(), chatHandler.GetChatSummaries)
	}
}
