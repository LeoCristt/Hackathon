package config

import (
	"log"
	"os"
	"strconv"
)

type Config struct {
	Port         int
	PostgresHost string
	PostgresPort string
	PostgresUser string
	PostgresDB   string
	PostgresPass string
}

func LoadConfig() *Config {
	port, err := strconv.Atoi(os.Getenv("PORT"))
	if err != nil || port <= 0 {
		port = 8080
	}

	host := os.Getenv("POSTGRES_HOST")
	user := os.Getenv("POSTGRES_USER")
	pass := os.Getenv("POSTGRES_PASSWORD")
	db := os.Getenv("POSTGRES_DB")
	dbPort := os.Getenv("POSTGRES_PORT")
	if dbPort == "" {
		dbPort = "5432"
	}

	if host == "" || user == "" || pass == "" || db == "" {
		log.Fatal("Отсутствуют обязательные переменные окружения: POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB")
	}

	return &Config{
		Port:         port,
		PostgresHost: host,
		PostgresPort: dbPort,
		PostgresUser: user,
		PostgresDB:   db,
		PostgresPass: pass,
	}
}
