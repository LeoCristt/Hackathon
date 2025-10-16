package server

import (
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
		AllowOrigins:     []string{"http://localhost:3000"},
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"},
		AllowHeaders:     []string{"Accept", "Authorization", "Content-Type"},
		AllowCredentials: true,
	}))

	userRepo := repository.NewUserRepository(s.db.DB())
	userService := service.NewUserService(userRepo)
	authHandler := handlers.NewAuthHandler(userService)

	routes.RegisterAuthRoutes(r, authHandler)

	return r
}
