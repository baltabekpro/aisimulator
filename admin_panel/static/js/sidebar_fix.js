/**
 * Автоматический фикс для бокового меню в админ-панели
 * Самоустанавливающийся скрипт, который решает проблему с закрытием бокового меню
 */
(function() {
    // Функция для создания и вставки CSS стилей
    function addStyles() {
        const style = document.createElement('style');
        style.innerHTML = `
            /* Стили для адаптивного меню */
            @media (max-width: 768px) {
                .sidebar {
                    position: fixed;
                    width: 100% !important;
                    height: 100%;
                    z-index: 9999;
                    transform: translateX(0);
                    transition: transform 0.3s ease;
                }
                
                .sidebar.toggled {
                    transform: translateX(-100%) !important;
                    width: 0 !important;
                }
                
                #content-wrapper {
                    margin-left: 0 !important;
                }
                
                #overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background-color: rgba(0, 0, 0, 0.5);
                    z-index: 9998;
                    display: none;
                }
                
                #overlay.show {
                    display: block;
                }
            }
            
            /* Общие стили для меню */
            .sidebar {
                overflow-y: auto;
                transition: all 0.3s ease;
            }
            
            /* Кнопка переключения меню */
            #sidebarToggleTop {
                cursor: pointer;
            }
        `;
        document.head.appendChild(style);
    }
    
    // Функция для добавления оверлея
    function addOverlay() {
        if (!document.getElementById('overlay')) {
            const overlay = document.createElement('div');
            overlay.id = 'overlay';
            document.body.appendChild(overlay);
            
            // Закрываем меню при клике на оверлей
            overlay.addEventListener('click', function() {
                toggleSidebar(true); // Принудительное закрытие
            });
        }
    }
    
    // Функция переключения меню
    function toggleSidebar(forceClose = false) {
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.getElementById('overlay');
        
        if (!sidebar) return;
        
        // Если нужно принудительно закрыть
        if (forceClose && !sidebar.classList.contains('toggled')) {
            sidebar.classList.add('toggled');
            document.body.classList.add('sidebar-toggled');
            if (overlay) overlay.classList.remove('show');
            return;
        }
        
        // Обычное переключение
        sidebar.classList.toggle('toggled');
        document.body.classList.toggle('sidebar-toggled');
        
        // Управление оверлеем
        if (overlay) {
            if (sidebar.classList.contains('toggled')) {
                overlay.classList.remove('show');
            } else {
                overlay.classList.add('show');
            }
        }
    }
    
    // Функция для добавления обработчиков событий
    function addEventListeners() {
        // Для кнопок переключения
        const toggleButtons = document.querySelectorAll('#sidebarToggle, #sidebarToggleTop');
        toggleButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                toggleSidebar();
            });
        });
        
        // Для пунктов меню на мобильных устройствах
        if (window.innerWidth <= 768) {
            const menuItems = document.querySelectorAll('.sidebar .nav-item a');
            menuItems.forEach(item => {
                item.addEventListener('click', function() {
                    setTimeout(() => toggleSidebar(true), 100);
                });
            });
        }
        
        // Автоматическое закрытие на мобильных при загрузке
        if (window.innerWidth <= 768) {
            setTimeout(() => toggleSidebar(true), 500);
        }
    }
    
    // Инициализация фикса
    function init() {
        addStyles();
        addOverlay();
        addEventListeners();
        
        // Адаптация при изменении размера окна
        window.addEventListener('resize', function() {
            if (window.innerWidth <= 768) {
                const sidebar = document.querySelector('.sidebar');
                if (sidebar && !sidebar.classList.contains('toggled')) {
                    toggleSidebar(true);
                }
            }
        });
        
        console.log('Sidebar fix initialized successfully');
    }
    
    // Запускаем фикс при загрузке страницы
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
