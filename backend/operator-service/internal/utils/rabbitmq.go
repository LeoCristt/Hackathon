package utils

import (
	"log"

	"github.com/streadway/amqp"
)

func RabbitMQConsumer(connStr, queueName string, handler func(msg []byte) error) error {
	conn, err := amqp.Dial(connStr)
	if err != nil {
		log.Fatalf("failed to connect to RabbitMQ: %v", err)
		return err
	}
	defer conn.Close()

	ch, err := conn.Channel()
	if err != nil {
		log.Fatalf("failed to open channel: %v", err)
		return err
	}
	defer ch.Close()

	_, err = ch.QueueInspect(queueName)
	if err != nil {
		log.Printf("Queue %s does not exist: %v", queueName, err)
		return err
	}

	msgs, err := ch.Consume(
		queueName,
		"",
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		log.Fatalf("failed to register consumer: %v", err)
		return err
	}

	forever := make(chan bool)

	go func() {
		for d := range msgs {
			if err := handler(d.Body); err != nil {
				log.Printf("failed to handle message from queue %s: %v", queueName, err)
			}
		}
	}()

	log.Printf("waiting for messages in queue %s...", queueName)
	<-forever

	return nil
}
