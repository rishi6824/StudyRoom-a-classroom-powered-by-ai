import os
import re

template_dir = '/home/rushikesh/ai/core/templates/core'

for root, dirs, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()

            # If the file has {% static but no {% load static %}
            if '{% static' in content and '{% load static %}' not in content:
                # Insert right after the {% extends ... %} tag if it exists, otherwise at the top
                if '{% extends' in content:
                    content = re.sub(r'(\{%\s*extends[^\}]*%\})', r'\1\n{% load static %}', content, count=1)
                else:
                    content = '{% load static %}\n' + content
                    
                with open(filepath, 'w') as f:
                    f.write(content)
                print(f"Added {{% load static %}} to {file}")

print("Added load static tags.")
