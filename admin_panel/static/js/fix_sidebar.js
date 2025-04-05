/**
 * Скрипт для корректной работы бокового меню
 * Предотвращает автоматическое закрытие меню
 */
document.addEventListener('DOMContentLoaded', function() {
    // Получаем элементы
    const sidebar = document.querySelector('.sidebar');
    const toggleButtons = document.querySelectorAll('#sidebarToggle, #sidebarToggleTop');
    const body = document.body;
    
    // Функция переключения меню
    function toggleSidebar(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        body.classList.toggle('sidebar-toggled');
        sidebar.classList.toggle('toggled');
        
        // Сохраняем состояние в localStorage
        localStorage.setItem('sidebarToggled', sidebar.classList.contains('toggled'));
    }
    
    // Отключаем существующие обработчики событий
    toggleButtons.forEach(function(btn) {
        const newBtn = btn.cloneNode(true);
        if (btn.parentNode) {
            btn.parentNode.replaceChild(newBtn, btn);
        }
        
        // Добавляем новый обработчик
        newBtn.addEventListener('click', toggleSidebar);
    });
    
    // Восстанавливаем состояние из localStorage
    const savedState = localStorage.getItem('sidebarToggled');
    const isMobile = window.innerWidth < 768;
    
    // На десктопах держим меню открытым по умолчанию
    if (savedState === 'true') {
        body.classList.add('sidebar-toggled');
        sidebar.classList.add('toggled');
    } else if (!isMobile) {
        // Явно открываем меню на десктопах
        body.classList.remove('sidebar-toggled');
        sidebar.classList.remove('toggled');
    }
    
    // На мобильных устройствах закрываем меню по умолчанию
    if (isMobile && savedState !== 'false') {
        body.classList.add('sidebar-toggled');
        sidebar.classList.add('toggled');
    }
    
    console.log('Меню исправлено: боковая панель не будет автоматически закрываться');
});
