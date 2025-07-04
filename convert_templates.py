"""
Script to convert existing HTML templates to use the base_layout.html template.
This script will:
1. Identify HTML templates in the app/templates directory
2. For each template, convert it to extend base_layout.html
3. Preserve the content, head_extra, and scripts blocks
"""

import os
import re
from pathlib import Path

# Directory containing the templates
templates_dir = Path('app/templates')

# Templates to skip (already converted or special cases)
skip_templates = ['base_layout.html', 'login.html', 'index.html', 'sql_editor.html', 'partials']

# Process each HTML file in the templates directory
def process_template_files():
    for template_file in templates_dir.glob('**/*.html'):
        # Skip templates in the skip list
        if any(skip in str(template_file) for skip in skip_templates):
            print(f"Skipping {template_file}")
            continue
            
        print(f"Converting {template_file}...")
        
        # Read the template content
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract the title
        title_match = re.search(r'<title>([^<]+)</title>', content)
        title = title_match.group(1) if title_match else 'DQX'
        
        # Find where the body content starts (after navigation)
        body_start = content.find('{% include "partials/main_nav.html" %}')
        if body_start == -1:
            body_start = content.find('<body>') + 6
        else:
            body_start = content.find('>', body_start) + 1
            
        # Find where the scripts start
        scripts_start = content.find('<script')
        if scripts_start == -1:
            scripts_start = content.find('</body>')
            
        # Find any extra head content
        head_extra = ''
        head_start = content.find('<head>')
        head_end = content.find('</head>')
        if head_start != -1 and head_end != -1:
            head_content = content[head_start:head_end]
            # Extract any non-standard head content
            extra_links = re.findall(r'<link(?!.*bootstrap|.*bootstrap-icons|.*style.css).*?>', head_content)
            extra_scripts = re.findall(r'<script.*?</script>', head_content)
            extra_meta = re.findall(r'<meta(?!.*charset|.*viewport).*?>', head_content)
            
            head_extra = '\n'.join(extra_meta + extra_links + extra_scripts)
            
        # Extract the body content
        body_content = content[body_start:scripts_start].strip()
        
        # Extract the scripts
        scripts_content = ''
        if scripts_start != -1:
            scripts_content = content[scripts_start:content.find('</body>')].strip()
            
        # Create the new template content
        new_template = f'''{{{{ extends "base_layout.html" }}}}

{{{{ block title }}}}{title}{{{{ endblock }}}}

'''
        
        if head_extra:
            new_template += f'''{{{{ block head_extra }}}}
{head_extra}
{{{{ endblock }}}}

'''
            
        new_template += f'''{{{{ block content }}}}
{body_content}
{{{{ endblock }}}}

'''

        if scripts_content:
            new_template += f'''{{{{ block scripts }}}}
{scripts_content}
{{{{ endblock }}}}
'''

        # Write the new template content
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(new_template)
            
        print(f"Converted {template_file}")

if __name__ == "__main__":
    process_template_files()
