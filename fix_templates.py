"""
Fix Jinja2 template delimiters in HTML templates.
This script will replace incorrect {{ block }} with {% block %}.
"""

import os
from pathlib import Path
import re

# Directory containing the templates
templates_dir = Path('app/templates')

# Skip these templates
skip_templates = ['base_layout.html', 'partials']

def fix_templates():
    """Fix Jinja2 template delimiters in all HTML files."""
    for template_file in templates_dir.glob('**/*.html'):
        # Skip templates in the skip list
        if any(skip in str(template_file) for skip in skip_templates):
            print(f"Skipping {template_file}")
            continue
            
        print(f"Fixing {template_file}...")
        
        # Read the template content
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace incorrect delimiters
        modified_content = content
        
        # Fix block delimiters
        modified_content = re.sub(r'{{(\s*)(extends|block|endblock|if|else|elif|endif|for|endfor)(\s+.*?)}}', 
                                 r'{%\1\2\3%}', modified_content)
        
        # Write back if changed
        if modified_content != content:
            with open(template_file, 'w', encoding='utf-8') as f:
                f.write(modified_content)
            print(f"Fixed {template_file}")
        else:
            print(f"No changes needed for {template_file}")

if __name__ == "__main__":
    fix_templates()
