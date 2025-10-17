package main

import (
	"log"

	"operator-service/internal/config"
	"operator-service/internal/server"
)

func main() {
	cfg := config.LoadConfig()
	rabbitCfg := config.LoadRabbitMQConfig()

	srv := server.NewServer(cfg, rabbitCfg)

	if err := srv.Start(); err != nil {
		log.Fatalf("server failed to start: %v", err)
	}
}
