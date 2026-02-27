import json
from datetime import datetime

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file."""
    try:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return None

def extract_text_from_docx(docx_file):
    """Extract text from DOCX file."""
    try:
        from docx import Document
        doc = Document(docx_file)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except Exception as e:
        print(f"Error extracting DOCX text: {e}")
        return None

def extract_resume_text(file_obj, file_name):
    """Extract text from resume file (PDF or DOCX)."""
    if file_name.lower().endswith('.pdf'):
        return extract_text_from_pdf(file_obj)
    elif file_name.lower().endswith('.docx'):
        return extract_text_from_docx(file_obj)
    else:
        try:
            return file_obj.read().decode('utf-8', errors='ignore')
        except:
            return None

def parse_ai_evaluation_response(response_text):
    """Parse AI evaluation response to extract structured data."""
    try:
        lines = response_text.split('\n')
        score = None
        skills = []
        suggestions = ""
        
        for i, line in enumerate(lines):
            if 'Score:' in line:
                try:
                    score = float(line.split(':')[1].strip().split('/')[0])
                except:
                    score = 5.0
            elif 'Skills:' in line or 'Key Skills:' in line:
                # Extract skills until next section
                j = i + 1
                while j < len(lines) and not any(x in lines[j] for x in ['Suggestions:', 'Feedback:', 'Areas:']):
                    skill = lines[j].strip()
                    if skill and not skill.startswith('['):
                        skills.append(skill.lstrip('- '))
                    j += 1
            elif 'Suggestions:' in line or 'Recommendations:' in line:
                suggestions = response_text.split('Suggestions:')[1] if 'Suggestions:' in response_text else response_text.split('Recommendations:')[1]
                suggestions = suggestions.strip()
        
        return {
            'score': score or 5.0,
            'skills': skills,
            'suggestions': suggestions or response_text
        }
    except Exception as e:
        print(f"Error parsing evaluation response: {e}")
        return {
            'score': 5.0,
            'skills': [],
            'suggestions': response_text
        }

def detect_integrity_issues(transcript, response_data):
    """Analyze proctoring session for potential integrity issues."""
    issues = []
    
    # Check for suspicious patterns
    if transcript:
        transcript_lower = transcript.lower()
        
        # Check for potential cheating indicators
        suspicious_keywords = ['look away', 'phone', 'other person', 'copy', 'help', 'chat']
        for keyword in suspicious_keywords:
            if keyword in transcript_lower:
                issues.append(f"Detected reference to '{keyword}' in transcript")
    
    # Check response consistency
    if response_data:
        try:
            if isinstance(response_data, list):
                for i, resp in enumerate(response_data):
                    if resp.get('score', 0) < 3:
                        issues.append(f"Low score on question {i+1}")
        except:
            pass
    
    return issues
