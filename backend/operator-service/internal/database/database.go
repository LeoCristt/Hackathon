package database

import (
	"fmt"
	"log"
	"sync"

	"operator-service/internal/config"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

type Service interface {
	Close() error
	DB() *gorm.DB
}

type service struct {
	db *gorm.DB
}

var (
	dbInstance *service
	once       sync.Once
)

func New(cfg *config.Config) Service {
	once.Do(func() {
		dsn := fmt.Sprintf(
			"host=%s port=%s user=%s dbname=%s password=%s sslmode=disable",
			cfg.PostgresHost,
			cfg.PostgresPort,
			cfg.PostgresUser,
			cfg.PostgresDB,
			cfg.PostgresPass,
		)

		db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
		if err != nil {
			log.Fatalf("Не удалось подключиться к базе данных: %v", err)
		}

		dbInstance = &service{db: db}
	})

	return dbInstance
}

func (s *service) Close() error {
	sqlDB, err := s.db.DB()
	if err != nil {
		return err
	}
	return sqlDB.Close()
}

func (s *service) DB() *gorm.DB {
	return s.db
}
