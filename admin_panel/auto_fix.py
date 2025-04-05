"""
Автоматический фикс для проблем с меню в админ-панели.
Этот скрипт встраивается в админ-панель и исправляет проблемы с меню.
"""
import os
import logging
from functools import wraps
from flask import Flask, request, g, current_app, render_template_string

# Структура инъекции для JavaScript/CSS
MENU_FIX_INJECTION = """
<!-- Menu Fix Injection -->
<link rel="stylesheet" href="/static/css/menu_override.css">
<script src="/static/js/menu_toggle.js"></script>
<!-- Add an overlay for mobile -->
<div class="sidebar-overlay" style="display:none;"></div>
"""

# HTML для оверлея (будет добавлен в DOM)
OVERLAY_HTML = """
<div class="sidebar-overlay" style="display:none;"></div>
<script>
    // Добавляем оверлей для закрытия меню на мобильных
    document.addEventListener('DOMContentLoaded', function() {
        const overlay = document.querySelector('.sidebar-overlay');
        if (overlay) {
            overlay.addEventListener('click', function() {
                const sidebar = document.querySelector('.sidebar');
                if (sidebar && !sidebar.classList.contains('toggled')) {
                    sidebar.classList.add('toggled');
                    document.body.classList.add('sidebar-toggled');
                    overlay.style.display = 'none';
                }
            });
            
            // Показываем оверлей при открытии меню на мобильных
            const toggleButtons = document.querySelectorAll('#sidebarToggle, #sidebarToggleTop');
            toggleButtons.forEach(button => {
                button.addEventListener('click', function() {
                    if (window.innerWidth < 768) {
                        const sidebar = document.querySelector('.sidebar');
                        if (sidebar) {
                            // Проверяем новое состояние после переключения
                            setTimeout(function() {
                                if (!sidebar.classList.contains('toggled')) {
                                    overlay.style.display = 'block';
                                } else {
                                    overlay.style.display = 'none';
                                }
                            }, 50);
                        }
                    }
                });
            });
        }
    });
</script>
"""

def create_files(app_instance):
    """Создает необходимые файлы для фикса меню, если они не существуют"""
    try:
        # Создаем директории, если они не существуют
        static_dir = os.path.join(app_instance.root_path, 'static')
        css_dir = os.path.join(static_dir, 'css')
        js_dir = os.path.join(static_dir, 'js')
        
        for directory in [static_dir, css_dir, js_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # Получаем содержимое JS/CSS файлов
        js_file_path = os.path.join(js_dir, 'menu_toggle.js')
        css_file_path = os.path.join(css_dir, 'menu_override.css')
        
        # Проверяем и создаем JS файл
        if not os.path.exists(js_file_path):
            with open(__file__, 'r') as f:
                content = f.read()
                start_js = content.find('// filepath: c:\\Users\\workb\\aibot\\admin_panel\\static\\js\\menu_toggle.js')
                end_js = content.find('// filepath: c:\\Users\\workb\\aibot\\admin_panel\\static\\css\\menu_override.css')
                if start_js > 0 and end_js > 0:
                    js_content = content[start_js:end_js].strip()
                    # Извлекаем только содержимое после первой строки с комментарием
                    js_content = '\n'.join(js_content.split('\n')[1:])
                    with open(js_file_path, 'w') as js_file:
                        js_file.write(js_content)
                        logging.info(f"Created menu_toggle.js file at {js_file_path}")
        
        # Проверяем и создаем CSS файл
        if not os.path.exists(css_file_path):
            with open(__file__, 'r') as f:
                content = f.read()
                start_css = content.find('// filepath: c:\\Users\\workb\\aibot\\admin_panel\\static\\css\\menu_override.css')
                end_css = content.find('// filepath: c:\\Users\\workb\\aibot\\admin_panel\\auto_fix.py')
                if start_css > 0 and end_css > 0:
                    css_content = content[start_css:end_css].strip()
                    # Извлекаем только содержимое после первой строки с комментарием
                    css_content = '\n'.join(css_content.split('\n')[1:])
                    with open(css_file_path, 'w') as css_file:
                        css_file.write(css_content)
                        logging.info(f"Created menu_override.css file at {css_file_path}")
        
        return True
    except Exception as e:
        logging.error(f"Error creating menu fix files: {e}")
        return False

def apply_menu_fix(app_instance):
    """Применяет фикс меню к Flask-приложению админ-панели"""
    if not app_instance:
        logging.error("No Flask app instance provided")
        return
    
    # Создаем необходимые файлы
    if not create_files(app_instance):
        logging.error("Failed to create menu fix files")
        return
    
    # Добавляем обработчик after_request для инъекции скриптов
    @app_instance.after_request
    def inject_menu_fix(response):
        # Инъекция только для HTML-ответов
        if response.content_type and response.content_type.startswith('text/html'):
            # Конвертируем байты в строку, если необходимо
            if isinstance(response.data, bytes):
                html = response.data.decode('utf-8')
            else:
                html = response.data
            
            # Вставляем скрипты перед закрывающим тегом </body>
            if '</body>' in html:
                if MENU_FIX_INJECTION not in html and OVERLAY_HTML not in html:
                    modified_html = html.replace('</body>', f'{MENU_FIX_INJECTION}\n{OVERLAY_HTML}\n</body>')
                    response.data = modified_html.encode('utf-8') if isinstance(response.data, bytes) else modified_html
        
        return response
    
    # Добавляем маршрут для проверки работоспособности
    @app_instance.route('/menu-fix-status')
    def menu_fix_status():
        js_path = os.path.join(app_instance.root_path, 'static', 'js', 'menu_toggle.js')
        css_path = os.path.join(app_instance.root_path, 'static', 'css', 'menu_override.css')
        
        status = {
            'js_exists': os.path.exists(js_path),
            'css_exists': os.path.exists(css_path),
            'js_size': os.path.getsize(js_path) if os.path.exists(js_path) else 0,
            'css_size': os.path.getsize(css_path) if os.path.exists(css_path) else 0
        }
        
        return f"""
        <h2>Menu Fix Status</h2>
        <ul>
            <li>JS File: {'✅ Exists' if status['js_exists'] else '❌ Missing'} ({status['js_size']} bytes)</li>
            <li>CSS File: {'✅ Exists' if status['css_exists'] else '❌ Missing'} ({status['css_size']} bytes)</li>
        </ul>
        <p>Add this to your app.py to enable the menu fix:</p>
        <pre>
        from auto_fix import apply_menu_fix
        
        # After creating the Flask app:
        apply_menu_fix(app)
        </pre>
        """
    
    # Добавляем глобальный контекст для шаблонов
    @app_instance.context_processor
    def inject_menu_globals():
        return {
            'show_sidebar': True,  # Всегда показываем сайдбар по умолчанию
            'menu_fixed': True     # Флаг, указывающий что фикс применен
        }
    
    logging.info("Menu fix applied to Flask app")

# Если запускается напрямую, создаем файлы
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Находим путь к папке с приложением
    current_dir = os.path.dirname(os.path.abspath(__file__))
    app_instance = Flask("menu_fix")
    app_instance.root_path = current_dir
    
    create_files(app_instance)
    print("Menu fix files created successfully!")
    print("To apply the fix, add the following to your app.py:")
    print("from auto_fix import apply_menu_fix")
    print("apply_menu_fix(app)")
