(function() {
    let url = "http://192.168.88.78"
    let socket = null;
    let chatId = null;

    // Получаем или создаем уникальный chatId для этого пользователя
    function getChatId() {
        // Пытаемся получить chatId из localStorage
        let storedChatId = localStorage.getItem('widget_chat_id');

        if (!storedChatId) {
            // Если нет - создаем новый и сохраняем
            storedChatId = 'chat-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9);
            localStorage.setItem('widget_chat_id', storedChatId);
            console.log('🆕 Создан новый chatId:', storedChatId);
        } else {
            console.log('♻️ Восстановлен chatId из localStorage:', storedChatId);
        }

        return storedChatId;
    }

    function insertWidget() {
        // Запросы идут через Kong Gateway (порт 8000)
        // Kong проверит домен в БД и добавит AI модель в headers
        Promise.all([
            fetch(`${url}:8000/widget/html`).then(r => {
                if (!r.ok) {
                    throw new Error('Access denied: Domain not authorized');
                }
                return r.json();
            }),
            fetch(`${url}:8000/widget/css`).then(r => r.json())
        ]).then(([htmlData, cssData]) => {
            // Создаем Shadow DOM
            const container = document.createElement('div');
            const shadow = container.attachShadow({mode: 'open'});

            // Добавляем стили в Shadow DOM
            const style = document.createElement('style');
            style.textContent = cssData.css;
            shadow.appendChild(style);

            // Добавляем HTML в Shadow DOM
            const content = document.createElement('div');
            content.innerHTML = htmlData.html;
            shadow.appendChild(content);

            // Добавляем контейнер на страницу
            document.body.appendChild(container);

            // Инициализируем функционал чата
            initializeChat(shadow);
        });
    }

    function initializeChat(shadow) {
        const header = shadow.querySelector('.widgetHeader');
        const chatGroup = shadow.querySelector('.widgetGroupChatInput');
        const messageInput = shadow.querySelector('#messageInput');
        const sendButton = shadow.querySelector('#sendButton');
        const chatDiv = shadow.querySelector('#widgetChat');

        // Обработчик сворачивания/разворачивания
        header.addEventListener('click', () => {
            chatGroup.classList.toggle('collapsed');
            header.classList.toggle('collapsed');

            // Подключаемся к чату при первом открытии
            if (!chatGroup.classList.contains('collapsed') && !socket) {
                connectToChat(shadow);
            }
        });

        // Отправка сообщения
        function sendMessage() {
            const message = messageInput.value.trim();
            if (message && socket) {
                socket.emit('message', { message });
                messageInput.value = '';
            }
        }

        sendButton.addEventListener('click', sendMessage);
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }

    function connectToChat(shadow) {
        // Получаем chatId (из localStorage или создаем новый)
        chatId = getChatId();

        // Загружаем Socket.IO
        const script = document.createElement('script');
        script.src = 'https://cdn.socket.io/4.5.4/socket.io.min.js';
        script.onload = () => {
            // Подключаемся к WebSocket серверу через Kong
            // Socket.IO автоматически использует путь /socket.io/
            socket = io(`${url}:8000`);

            socket.on('connect', () => {
                console.log('✅ Подключен к чату');
                console.log('📍 Используется chatId:', chatId);

                // Присоединяемся к чату
                socket.emit('join', { chatId });
            });

            socket.on('disconnect', () => {
                console.log('❌ Отключен от чата');
            });

            socket.on('message', (data) => {
                console.log('📨 Получено сообщение:', data);
                addMessage(shadow, data);
            });

            socket.on('history', (messages) => {
                console.log('📚 Получена история:', messages.length, 'сообщений');
                const chatDiv = shadow.querySelector('#widgetChat');
                chatDiv.innerHTML = '';

                messages.forEach(msg => {
                    addMessage(shadow, msg, false);
                });

                chatDiv.scrollTop = chatDiv.scrollHeight;
            });

            socket.on('system', (data) => {
                console.log('🔔 Системное сообщение:', data);
            });
        };

        document.head.appendChild(script);
    }

    function addMessage(shadow, data, autoScroll = true) {
        const chatDiv = shadow.querySelector('#widgetChat');
        const messageDiv = document.createElement('div');

        // Определяем тип сообщения
        // AI сообщения - любое username, начинающееся с 'AI' или содержащее 'помощник'
        const isAI = data.username.startsWith('AI') || data.username.includes('помощник');
        const isManager = data.username && data.username.includes('Оператор');
        const isUser = data.username === 'Пользователь' || (!isAI && !isManager);

        // Устанавливаем класс в зависимости от типа
        let messageClass = 'chatMessage';
        if (isAI) {
            messageClass += ' ai';
        } else if (isManager) {
            messageClass += ' manager';
        } else {
            messageClass += ' user';
        }

        messageDiv.className = messageClass;

        const time = new Date(data.timestamp).toLocaleTimeString('ru-RU', {
            hour: '2-digit',
            minute: '2-digit'
        });

        messageDiv.innerHTML = `
            <div class="messageUsername">${escapeHtml(data.username)}</div>
            <div class="messageText">${escapeHtml(data.message)}</div>
            <div class="messageTime">${time}</div>
        `;

        chatDiv.appendChild(messageDiv);

        if (autoScroll) {
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', insertWidget);
    } else {
        insertWidget();
    }
})();