"""
Запуск для автоматического применения фикса меню
"""
import os
import sys
import logging

# Настраиваем логирование
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def apply_fix():
    try:
        # Импортируем модуль auto_fix
        from auto_fix import create_files
        
        # Создаем необходимые файлы
        create_files_result = create_files(None)
        
        if create_files_result:
            logger.info("Menu fix files created successfully!")
            
            # Находим файл app.py
            app_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')
            
            if os.path.exists(app_py_path):
                # Проверяем, есть ли уже строки импорта в app.py
                with open(app_py_path, 'r') as f:
                    content = f.read()
                
                if 'from auto_fix import apply_menu_fix' not in content:
                    # Добавляем код для применения фикса в app.py
                    # Находим строку, после которой нужно добавить импорт
                    import_point = content.find('app = Flask(__name__)')
                    
                    if import_point >= 0:
                        # Добавляем импорт перед созданием приложения
                        modified_content = content[:import_point] + \
                                           '\n# Import menu fix\nfrom auto_fix import apply_menu_fix\n\n' + \
                                           content[import_point:]
                        
                        # Находим точку для применения фикса
                        apply_point = modified_content.find('app.config')
                        
                        if apply_point >= 0:
                            # Добавляем вызов apply_menu_fix после настройки конфигурации
                            config_end = modified_content.find('\n', apply_point)
                            if config_end >= 0:
                                modified_content = modified_content[:config_end+1] + \
                                                  '\n# Apply menu fix\napply_menu_fix(app)\n' + \
                                                  modified_content[config_end+1:]
                                
                                # Сохраняем изменения
                                with open(app_py_path, 'w') as f:
                                    f.write(modified_content)
                                
                                logger.info(f"Successfully modified {app_py_path} to apply menu fix")
                                return True
                    
                    logger.error("Could not find appropriate place to insert fix code in app.py")
                else:
                    logger.info("Menu fix already applied in app.py")
                    return True
            else:
                logger.error(f"app.py not found at {app_py_path}")
        else:
            logger.error("Failed to create menu fix files")
        
        return False
    except Exception as e:
        logger.error(f"Error applying menu fix: {e}")
        return False

if __name__ == "__main__":
    success = apply_fix()
    
    if success:
        print("\n✅ Menu fix applied successfully!")
        print("Restart your admin panel application for changes to take effect.\n")
    else:
        print("\n❌ Failed to apply menu fix automatically.")
        print("Please add the following code to your app.py manually:\n")
        print("from auto_fix import apply_menu_fix")
        print("apply_menu_fix(app)")
