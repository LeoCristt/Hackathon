package server

import (
	"log"
	"net/http"
	"operator-service/internal/handlers"
	"operator-service/internal/repository"
	"operator-service/internal/routes"
	"operator-service/internal/service"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

func (s *Server) RegisterRoutes() http.Handler {
	r := gin.Default()

	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:3000", "http://localhost:5173"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"},
		AllowHeaders:     []string{"Accept", "Authorization", "Content-Type"},
		AllowCredentials: true,
	}))

	userRepo := repository.NewUserRepository(s.db.DB())
	userService := service.NewUserService(userRepo)
	authHandler := handlers.NewAuthHandler(userService)

	chatRepo := repository.NewChatRepository(s.db.DB())
	chatService := service.NewChatService(chatRepo)
	chatHandler := handlers.NewChatHandler(chatService)

	adminRepo := repository.NewAdminRepository(s.db.DB())
	adminService := service.NewAdminService(adminRepo)
	adminHandler := handlers.NewAdminHandler(adminService)

	routes.RegisterAuthRoutes(r, authHandler)
	routes.RegisterChatRoutes(r, chatHandler)
	routes.RegisterAdminRoutes(r, adminHandler)

	go func() {
		log.Printf("listening RabbitMQ queue: %s", s.rabbitCfg.Queue)
		chatHandler.ConsumeRabbitMQ(s.rabbitCfg.URL, s.rabbitCfg.Queue)
	}()

	return r
}
