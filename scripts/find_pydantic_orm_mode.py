import os
import re

def find_orm_mode_usages(base_directory):
    """Find all Python files with 'orm_mode' usage in the project."""
    orm_mode_pattern = re.compile(r'orm_mode\s*=\s*True')
    files_with_matches = []
    
    for root, _, files in os.walk(base_directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if orm_mode_pattern.search(content):
                            files_with_matches.append(filepath)
                            print(f"Found 'orm_mode' in: {filepath}")
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")
    
    if not files_with_matches:
        print("No 'orm_mode' usages found.")
    else:
        print("\nUpdate these files to use 'from_attributes = True' instead of 'orm_mode = True'")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"Searching for 'orm_mode' in: {base_dir}")
    find_orm_mode_usages(base_dir)
