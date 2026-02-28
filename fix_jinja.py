import os
import re

template_dir = '/home/rushikesh/ai/core/templates/core'

for root, dirs, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()

            # Fix remaining url_for("...") or url_for('...') that didn't match the regex perfectly
            # e.g. {{ url_for('route') }} -> {% url 'route' %}
            content = re.sub(r'\{\{\s*url_for\([\'"](\w+)[\'"]\)\s*\}\}', r"{% url '\1' %}", content)
            
            # Fix url_for('static', filename='...')
            content = re.sub(r'\{\{\s*url_for\([\'"]static[\'"],\s*filename=[\'"]([^\'"]+)[\'"]\)\s*\}\}', r"{% static 'core/\1' %}", content)

            with open(filepath, 'w') as f:
                f.write(content)

print("Jinja tags replaced.")
