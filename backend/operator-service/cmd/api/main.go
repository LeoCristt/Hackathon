package main

import (
	"log"

	"operator-service/internal/config"
	"operator-service/internal/server"
)

func main() {
	cfg := config.LoadConfig()

	srv := server.NewServer(cfg)

	if err := srv.Start(); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}
