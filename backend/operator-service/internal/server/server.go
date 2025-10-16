package server

import (
	"fmt"
	"net/http"

	"operator-service/internal/config"
	"operator-service/internal/database"
)

type Server struct {
	port int
	db   database.Service
}

func NewServer(cfg *config.Config) *Server {
	db := database.New(cfg)
	return &Server{
		port: cfg.Port,
		db:   db,
	}
}

func (s *Server) Start() error {
	server := &http.Server{
		Addr:    fmt.Sprintf("0.0.0.0:%d", s.port),
		Handler: s.RegisterRoutes(),
	}
	return server.ListenAndServe()
}
