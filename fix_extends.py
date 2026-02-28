import os
import re

template_dir = '/home/rushikesh/ai/core/templates/core'

for root, dirs, files in os.walk(template_dir):
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                content = f.read()

            new_content = re.sub(r'\{%\s*extends\s+["\']base_interview\.html["\']\s*%\}', r'{% extends "core/base_interview.html" %}', content)

            if new_content != content:
                with open(filepath, 'w') as f:
                    f.write(new_content)
                print(f"Updated {file}")

print("Template extends fixed.")
