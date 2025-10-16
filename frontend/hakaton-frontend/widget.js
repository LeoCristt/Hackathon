(function() {
    function insertWidget() {
        Promise.all([
            fetch('http://localhost:4000/html').then(r => r.json()),
            fetch('http://localhost:4000/css').then(r => r.json())
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
            
            // Добавляем обработчик клика для кнопки сворачивания
            const header = shadow.querySelector('.widgetHeader');
            const chat = shadow.querySelector('.widgetGroupChatInput');

            header.addEventListener('click', () => {
                chat.classList.toggle('collapsed');
                header.classList.toggle('collapsed');
            });
        });
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', insertWidget);
    } else {
        insertWidget();
    }
})();