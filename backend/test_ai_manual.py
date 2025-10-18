import pika
import json
import time

print("🧪 Manual AI Response Tester")
print("=" * 50)
print("Этот скрипт эмулирует AI service")
print("Вы будете вручную отправлять ответы в RabbitMQ")
print("=" * 50)

def connect_rabbitmq():
    """Подключение к RabbitMQ"""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost', port=5672)
        )
        print("✅ Подключено к RabbitMQ (localhost:5672)")
        return connection
    except Exception as e:
        print(f"❌ Ошибка подключения к RabbitMQ: {e}")
        print("Убедитесь, что RabbitMQ запущен: docker-compose ps")
        exit(1)

def send_ai_response(channel, chat_id, answer, bot_username, is_manager=False):
    """Отправка ответа в очередь ai_responses"""
    response = {
        'chatId': chat_id,
        'answer': answer,
        'botUsername': bot_username,
        'isManager': is_manager
    }

    channel.basic_publish(
        exchange='',
        routing_key='ai_responses',
        body=json.dumps(response),
        properties=pika.BasicProperties(
            delivery_mode=2,  # Персистентное сообщение
        )
    )

    print(f"\n✅ Ответ отправлен в очередь 'ai_responses':")
    print(f"   Chat ID: {chat_id}")
    print(f"   Answer: {answer}")
    print(f"   Bot Username: {bot_username}")
    print(f"   isManager: {is_manager}")

def listen_requests(channel):
    """Слушаем очередь ai_requests и выводим их"""

    def callback(ch, method, properties, body):
        try:
            request = json.loads(body)
            print("\n" + "=" * 50)
            print("📨 ПОЛУЧЕН ЗАПРОС ОТ CHAT SERVICE:")
            print("=" * 50)
            print(f"Chat ID: {request.get('chatId')}")
            print(f"Message: {request.get('message')}")
            print(f"AI Model: {request.get('aiId', 'N/A')}")
            print(f"History Length: {len(request.get('messageHistory', []))}")
            print("=" * 50)

            # Подтверждаем получение
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"❌ Ошибка обработки запроса: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue='ai_requests',
        on_message_callback=callback,
        auto_ack=False
    )

    print("\n🎧 Слушаю очередь 'ai_requests'...")
    print("Ожидаю сообщений от пользователей...\n")

def manual_mode(channel):
    """Режим ручной отправки ответов"""
    print("\n" + "=" * 50)
    print("📝 РЕЖИМ РУЧНОЙ ОТПРАВКИ")
    print("=" * 50)
    print("Введите данные для отправки ответа:")
    print("(Оставьте пустым для отмены)\n")

    chat_id = input("Chat ID: ").strip()
    if not chat_id:
        print("❌ Отменено")
        return

    answer = input("Ответ AI: ").strip()
    if not answer:
        print("❌ Отменено")
        return

    bot_username = input("Bot Username [AI-помощник]: ").strip()
    if not bot_username:
        bot_username = "AI-помощник"

    is_manager_input = input("Требуется менеджер? (y/n) [n]: ").strip().lower()
    is_manager = is_manager_input == 'y'

    send_ai_response(channel, chat_id, answer, bot_username, is_manager)

if __name__ == '__main__':
    connection = connect_rabbitmq()
    channel = connection.channel()

    # Проверяем/создаем очереди
    channel.queue_declare(queue='ai_requests', durable=True)
    channel.queue_declare(queue='ai_responses', durable=True)
    print("✅ Очереди 'ai_requests' и 'ai_responses' готовы\n")

    print("Выберите режим:")
    print("1. Слушать ai_requests (показывать входящие запросы)")
    print("2. Отправить ответ вручную (эмулировать AI ответ)")
    print("3. Оба режима (слушать + возможность ответить)")

    mode = input("\nВыберите режим (1/2/3): ").strip()

    if mode == '1':
        # Только слушаем
        listen_requests(channel)
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            print("\n🛑 Остановлено")

    elif mode == '2':
        # Только отправка
        while True:
            manual_mode(channel)
            again = input("\nОтправить еще один ответ? (y/n): ").strip().lower()
            if again != 'y':
                break

    elif mode == '3':
        # Гибридный режим
        import threading

        # Запускаем слушатель в отдельном потоке
        def consume():
            listen_requests(channel)
            channel.start_consuming()

        consumer_thread = threading.Thread(target=consume, daemon=True)
        consumer_thread.start()

        time.sleep(1)

        print("\n" + "=" * 50)
        print("Команды:")
        print("  'send' - отправить ответ вручную")
        print("  'quit' - выйти")
        print("=" * 50 + "\n")

        while True:
            cmd = input("Команда: ").strip().lower()
            if cmd == 'send':
                manual_mode(channel)
            elif cmd == 'quit':
                break
            else:
                print("❌ Неизвестная команда")

    else:
        print("❌ Неверный выбор")

    connection.close()
    print("\n👋 Отключено от RabbitMQ")
