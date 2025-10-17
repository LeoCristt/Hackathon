package server

import (
	"fmt"
	"net/http"

	"operator-service/internal/config"
	"operator-service/internal/database"
)

type Server struct {
	port      int
	db        database.Service
	rabbitCfg config.RabbitMQConfig
}

func NewServer(cfg *config.Config, rabbitCfg config.RabbitMQConfig) *Server {
	db := database.New(cfg)
	return &Server{
		port:      cfg.Port,
		db:        db,
		rabbitCfg: rabbitCfg,
	}
}

func (s *Server) Start() error {
	server := &http.Server{
		Addr:    fmt.Sprintf("0.0.0.0:%d", s.port),
		Handler: s.RegisterRoutes(),
	}
	return server.ListenAndServe()
}
