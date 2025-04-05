/**
 * СРОЧНЫЙ ФИКС ДЛЯ ПРЕДОТВРАЩЕНИЯ АВТОЗАКРЫТИЯ МЕНЮ
 * Этот скрипт решает проблему автоматического закрытия меню
 */

// Исполняем скрипт сразу при загрузке
(function() {
    // Функция для фиксации меню при загрузке DOM
    function fixMenu() {
        // Находим необходимые элементы
        var sidebar = document.querySelector('.sidebar');
        var toggleButtons = document.querySelectorAll('#sidebarToggle, #sidebarToggleTop');
        var body = document.body;
        
        // Если элементы не найдены, ничего не делаем
        if (!sidebar || toggleButtons.length === 0) {
            console.log('Элементы меню не найдены');
            return;
        }
        
        console.log('Фикс меню запущен - отключаем автозакрытие');
        
        // 1. УСТРАНЯЕМ СУЩЕСТВУЮЩИЕ ОБРАБОТЧИКИ
        // Создаем новые кнопки, заменяя старые
        toggleButtons.forEach(function(button) {
            var newButton = button.cloneNode(true);
            button.parentNode.replaceChild(newButton, button);
        });
        
        // 2. ДОБАВЛЯЕМ НАШИ СОБСТВЕННЫЕ ОБРАБОТЧИКИ
        // Получаем новые кнопки после замены
        var newToggleButtons = document.querySelectorAll('#sidebarToggle, #sidebarToggleTop');
        
        // Добавляем обработчики на новые кнопки
        newToggleButtons.forEach(function(button) {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                // Переключаем классы для body и sidebar
                body.classList.toggle('sidebar-toggled');
                sidebar.classList.toggle('toggled');
                
                // Сохраняем состояние в localStorage
                localStorage.setItem('sidebar_state', sidebar.classList.contains('toggled') ? 'closed' : 'open');
                
                console.log('Переключено состояние меню: ' + (sidebar.classList.contains('toggled') ? 'закрыто' : 'открыто'));
                
                return false; // Останавливаем дальнейшую обработку
            });
        });
        
        // 3. УСТАНАВЛИВАЕМ НАЧАЛЬНОЕ СОСТОЯНИЕ
        // Проверяем сохраненное состояние
        var savedState = localStorage.getItem('sidebar_state');
        var isMobile = window.innerWidth < 768;
        
        // Если мы на мобильном устройстве, закрываем меню
        if (isMobile) {
            if (!sidebar.classList.contains('toggled')) {
                sidebar.classList.add('toggled');
                body.classList.add('sidebar-toggled');
            }
        } 
        // На десктопе открываем меню, если не было явно закрыто
        else if (savedState !== 'closed') {
            sidebar.classList.remove('toggled');
            body.classList.remove('sidebar-toggled');
        }
        
        // 4. УДАЛЯЕМ ОБРАБОТЧИКИ ДЛЯ ЗАКРЫТИЯ МЕНЮ НА МОБИЛЬНЫХ
        // Только для мобильных добавляем закрытие при клике на ссылки
        if (isMobile) {
            var navLinks = document.querySelectorAll('.sidebar .nav-item .nav-link');
            navLinks.forEach(function(link) {
                link.addEventListener('click', function() {
                    if (window.innerWidth < 768) {
                        sidebar.classList.add('toggled');
                        body.classList.add('sidebar-toggled');
                    }
                });
            });
        }
        
        // 5. ОТКЛЮЧАЕМ АВТОМАТИЧЕСКОЕ ЗАКРЫТИЕ ПРИ ИЗМЕНЕНИИ РАЗМЕРА ОКНА
        window.removeEventListener('resize', null); // Удаляем все обработчики resize
        
        // Добавляем только нашу логику изменения размера
        window.addEventListener('resize', function() {
            var currentIsMobile = window.innerWidth < 768;
            
            // Только на мобильных устройствах
            if (currentIsMobile) {
                if (savedState !== 'open') {
                    sidebar.classList.add('toggled');
                    body.classList.add('sidebar-toggled');
                }
            }
        });
        
        console.log('Фикс меню успешно применен');
    }
    
    // Запускаем фикс после загрузки DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', fixMenu);
    } else {
        fixMenu(); // DOM уже загружен
    }
    
    // Дополнительно запускаем после полной загрузки страницы
    window.addEventListener('load', fixMenu);
    
    // Запускаем еще раз через небольшую задержку для надежности
    setTimeout(fixMenu, 500);
})();
