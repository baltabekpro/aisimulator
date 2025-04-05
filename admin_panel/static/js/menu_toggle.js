/**
 * Корректный скрипт для меню админ-панели
 * Фиксит проблему с автоматическим закрытием
 */
document.addEventListener('DOMContentLoaded', function() {
    // Выбираем элементы DOM
    const sidebar = document.querySelector('.sidebar');
    const sidebarToggle = document.querySelector('#sidebarToggle');
    const sidebarToggleTop = document.querySelector('#sidebarToggleTop');
    const contentWrapper = document.querySelector('#content-wrapper');
    
    // Проверяем на мобильное устройство
    const isMobile = window.innerWidth < 768;
    
    // Опция: не закрывать автоматически
    const keepOpen = true;
    
    // Функция переключения меню
    function toggleSidebar(forceClose = false) {
        if (sidebar) {
            if (forceClose) {
                sidebar.classList.add('toggled');
                document.body.classList.add('sidebar-toggled');
            } else {
                sidebar.classList.toggle('toggled');
                document.body.classList.toggle('sidebar-toggled');
            }
            
            // Проверяем, является ли меню закрытым после переключения
            const isToggled = sidebar.classList.contains('toggled');
            
            // Сохраняем состояние в localStorage
            localStorage.setItem('sidebarToggled', isToggled ? 'true' : 'false');
        }
    }
    
    // Добавляем обработчики событий
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }
    
    if (sidebarToggleTop) {
        sidebarToggleTop.addEventListener('click', function(e) {
            e.preventDefault();
            toggleSidebar();
        });
    }
    
    // Восстановление состояния из localStorage
    const savedState = localStorage.getItem('sidebarToggled');
    if (savedState === 'true' && !keepOpen) {
        toggleSidebar(true);
    } else if (keepOpen && sidebar && sidebar.classList.contains('toggled')) {
        // Если keepOpen=true, гарантируем, что меню открыто при загрузке страницы
        sidebar.classList.remove('toggled');
        document.body.classList.remove('sidebar-toggled');
    }
    
    // Если мы на мобильном устройстве и keepOpen=false, закрываем меню
    if (isMobile && !keepOpen) {
        toggleSidebar(true);
    }
    
    // Добавляем обработчик события для закрытия подменю при закрытии меню
    if (sidebar) {
        sidebar.addEventListener('transitionend', function() {
            if (sidebar.classList.contains('toggled')) {
                const collapseElements = sidebar.querySelectorAll('.collapse.show');
                collapseElements.forEach(function(element) {
                    // Используем Bootstrap API для закрытия
                    if (window.jQuery && window.jQuery(element).collapse) {
                        window.jQuery(element).collapse('hide');
                    }
                });
            }
        });
    }
    
    console.log('Menu toggle script loaded successfully!');
});
