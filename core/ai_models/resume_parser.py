try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
from docx import Document
import re

class ResumeParser:
    def __init__(self):
        self.skills_keywords = [
            'python', 'java', 'javascript', 'html', 'css', 'react', 'angular', 'vue',
            'node.js', 'express', 'django', 'flask', 'spring', 'sql', 'mongodb',
            'postgresql', 'aws', 'azure', 'docker', 'kubernetes', 'git', 'jenkins',
            'machine learning', 'ai', 'data analysis', 'project management', 'agile',
            'scrum', 'leadership', 'communication', 'problem solving', 'teamwork'
        ]
    
    def parse_resume(self, file):
        filename = file.filename.lower()
        
        if filename.endswith('.pdf'):
            return self._parse_pdf(file)
        elif filename.endswith('.docx'):
            return self._parse_docx(file)
        elif filename.endswith('.txt'):
            return file.read().decode('utf-8')
        else:
            raise ValueError("Unsupported file format")
    
    def _parse_pdf(self, file):
        if not PDF_SUPPORT:
            return "PDF parsing not available - PyPDF2 not installed"

        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    
    def _parse_docx(self, file):
        doc = Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    
    def extract_skills(self, text):
        text_lower = text.lower()
        found_skills = []
        
        for skill in self.skills_keywords:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        return list(set(found_skills))  # Remove duplicates
    
    def extract_experience(self, text):
        # Simple experience extraction using regex
        experience_patterns = [
            r'(\d+)\s*years?\s*experience',
            r'experience\s*:\s*(\d+)\s*years?',
            r'(\d+)\s*years?\s*in\s*.*experience'
        ]
        
        for pattern in experience_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Not specified"