#!/usr/bin/env python3
"""
Script to update admin panel templates to include avatar preview functionality
"""
import os
import re

def update_base_template():
    """Add the avatar preview JS to the base template"""
    template_path = '/Users/macbook/Desktop/aisimulator/admin_panel/templates/base.html'
    
    if not os.path.exists(template_path):
        print(f"Template not found: {template_path}")
        return False
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check if our script is already included
    if 'avatar_preview.js' in content:
        print("Avatar preview script is already included in the base template.")
        return True
    
    # Find the position to insert our script (before the closing </body> tag)
    if '</body>' in content:
        new_content = content.replace('</body>', 
                                      '    <!-- Avatar preview functionality -->\n'
                                      '    <script src="{{ url_for(\'static\', filename=\'js/avatar_preview.js\') }}"></script>\n'
                                      '</body>')
        
        with open(template_path, 'w') as f:
            f.write(new_content)
        
        print("Successfully added avatar_preview.js to base.html")
        return True
    else:
        print("Could not locate </body> tag in base.html")
        return False

def update_character_list_template():
    """Update the character list template to use the avatar preview"""
    template_path = '/Users/macbook/Desktop/aisimulator/admin_panel/templates/characters/list.html'
    
    if not os.path.exists(template_path):
        print(f"Template not found: {template_path}")
        return False
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Find where character info is displayed in the table
    table_row_pattern = r'(<tr>\s*<td>.*?</td>)'
    
    if re.search(table_row_pattern, content, re.DOTALL):
        modified_content = re.sub(
            table_row_pattern,
            r'\1\n                    <td class="text-center">'
            r'\n                        {% if character.avatar_url %}'
            r'\n                        <img src="{{ character.avatar_url }}" '
            r'alt="Avatar" class="rounded-circle" width="40" height="40" '
            r'data-avatar-url="{{ character.avatar_url }}">'
            r'\n                        {% else %}'
            r'\n                        <span class="avatar-placeholder">🧑</span>'
            r'\n                        {% endif %}'
            r'\n                    </td>',
            content,
            flags=re.DOTALL
        )
        
        # Add Avatar to the table header
        modified_content = modified_content.replace(
            '<thead>\n                    <tr>',
            '<thead>\n                    <tr>\n                        <th>Avatar</th>'
        )
        
        with open(template_path, 'w') as f:
            f.write(modified_content)
        
        print("Successfully updated character list template with avatar display")
        return True
    else:
        print("Could not locate character table rows in the template")
        return False

def update_character_view_template():
    """Update character view template to display the avatar"""
    template_path = '/Users/macbook/Desktop/aisimulator/admin_panel/templates/characters/view.html'
    
    if not os.path.exists(template_path):
        print(f"Template not found: {template_path}")
        return False
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check if avatar section already exists
    if 'character-avatar' in content:
        print("Avatar section already exists in character view template.")
        return True
    
    # Find the card body where we want to add the avatar
    card_body_pattern = r'<div class="card-body">\s*<div class="row mb-3">'
    
    if re.search(card_body_pattern, content):
        modified_content = re.sub(
            card_body_pattern,
            '<div class="card-body">\n'
            '                <div class="text-center mb-4">\n'
            '                    <div class="character-avatar" data-avatar-url="{{ character.avatar_url }}">\n'
            '                        {% if character.avatar_url %}\n'
            '                        <img src="{{ character.avatar_url }}" alt="{{ character.name }}" '
            'class="img-fluid rounded mb-3" style="max-height: 200px;">\n'
            '                        {% else %}\n'
            '                        <div class="avatar-placeholder display-4">🧑</div>\n'
            '                        {% endif %}\n'
            '                    </div>\n'
            '                </div>\n'
            '                <div class="row mb-3">',
            content
        )
        
        with open(template_path, 'w') as f:
            f.write(modified_content)
        
        print("Successfully updated character view template with avatar display")
        return True
    else:
        print("Could not locate card body in character view template")
        return False

def update_character_edit_form():
    """Update character edit form to preview uploaded avatars"""
    template_path = '/Users/macbook/Desktop/aisimulator/admin_panel/templates/characters/edit.html'
    
    if not os.path.exists(template_path):
        print(f"Template not found: {template_path}")
        return False
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check if preview functionality already exists
    if 'avatar-preview' in content:
        print("Avatar preview already exists in character edit template.")
        return True
    
    # Add preview functionality to avatar input
    avatar_input_pattern = r'<input type="file" class="form-control" id="avatar" name="avatar" accept="image/\*">'
    
    if re.search(avatar_input_pattern, content):
        modified_content = content.replace(
            avatar_input_pattern,
            '<input type="file" class="form-control" id="avatar" name="avatar" accept="image/*" '
            'onchange="loadAvatarPreview(this, \'avatarPreview\')">\n'
            '                    <div id="avatarPreview" class="mt-3">\n'
            '                        {% if character.avatar_url %}\n'
            '                        <img src="{{ character.avatar_url }}" alt="Current Avatar" '
            'class="img-fluid rounded" style="max-height: 200px;">\n'
            '                        {% endif %}\n'
            '                    </div>'
        )
        
        with open(template_path, 'w') as f:
            f.write(modified_content)
        
        print("Successfully updated character edit template with avatar preview")
        return True
    else:
        print("Could not locate avatar input in character edit template")
        return False

if __name__ == '__main__':
    print("Updating admin panel templates for avatar preview...")
    update_base_template()
    update_character_list_template()
    update_character_view_template()
    update_character_edit_form()
    print("Done!")
