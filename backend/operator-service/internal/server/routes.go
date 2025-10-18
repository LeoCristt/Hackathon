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
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"},
		AllowHeaders:     []string{"Accept", "Authorization", "Content-Type"},
		AllowCredentials: true,
	}))

	authRepo := repository.NewAuthRepository(s.db.DB())
	authService := service.NewAuthService(authRepo)
	authHandler := handlers.NewAuthHandler(authService)

	chatRepo := repository.NewChatRepository(s.db.DB())
	chatService := service.NewChatService(chatRepo)
	chatHandler := handlers.NewChatHandler(chatService)

	adminRepo := repository.NewAdminRepository(s.db.DB())
	adminService := service.NewAdminService(adminRepo)
	adminHandler := handlers.NewAdminHandler(adminService)

	userRepo := repository.NewUserRepository(s.db.DB())
	userService := service.NewUserService(userRepo)
	userHandler := handlers.NewUserHandler(userService)

	routes.RegisterAuthRoutes(r, authHandler)
	routes.RegisterChatRoutes(r, chatHandler)
	routes.RegisterAdminRoutes(r, adminHandler)
	routes.RegisterUserRoutes(r, userHandler)

	go func() {
		log.Printf("listening RabbitMQ queue: %s", s.rabbitCfg.Queue)
		chatHandler.ConsumeRabbitMQ(s.rabbitCfg.URL, s.rabbitCfg.Queue)
	}()

	return r
}
