import requests
import json
import google.generativeai as genai

OLLAMA_API_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2"

# Gemini Configuration
GEMINI_API_KEY = "AIzaSyAxHosbDuD_bsOkf77ZTOX9TKSnvAl0H30"
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash')

# OpenRouter Configuration
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct"

def call_openrouter(prompt):
    """Utility to call OpenRouter API."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000", # Required for OpenRouter
        "X-Title": "StudyRoom", # Optional for OpenRouter
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"OpenRouter API Error: {e}")
        return None

def get_ai_response(prompt):
    """Hybrid logic: Try OpenRouter first, then Gemini, then fallback to Ollama."""
    res = call_openrouter(prompt)
    if not res:
        print("OpenRouter failed, trying Gemini...")
        res = call_gemini(prompt)
    
    if not res:
        print("Gemini failed, falling back to Ollama...")
        res = call_ollama(prompt)
    return res

def call_gemini(prompt):
    """Utility to call Gemini API."""
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None

def call_ollama(prompt, model=DEFAULT_MODEL):
    """Utility to call Ollama API."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"Ollama API Error: {e}")
        return None

def evaluate_assignment(assignment_title, assignment_description, submission_content, rubric=None):
    """Evaluates an assignment using AI with optional rubric."""
    rubric_section = f"\n    Marking Rubric/Criteria:\n    {rubric}\n" if rubric else ""
    
    prompt = f"""
    You are an expert academic evaluator. Please evaluate the following student submission for the assignment titled '{assignment_title}'.
    
    Assignment Description:
    {assignment_description}
    {rubric_section}
    
    Student Submission:
    {submission_content}
    
    Please provide a professional evaluation including:
    1. A score out of 10.
    2. Detailed feedback broken down into:
       - Strengths: What the student did well.
       - Areas for Improvement: Specific suggestions for growth.
       - Conclusion: A brief summarizing thought.
    
    Format your response EXACTLY like this:
    Score: [Number]
    Feedback:
    Strengths: [Text]
    Areas for Improvement: [Text]
    Conclusion: [Text]
    """
    
    response = get_ai_response(prompt)
    if not response:
        return 0, "Evaluation failed due to AI engine error."
    
    # Advanced parsing logic
    try:
        lines = response.split('\n')
        score_line = [l for l in lines if 'Score:' in l][0]
        score = float(score_line.split(':')[1].strip().split('/')[0])
        
        # Extract feedback starting from "Strengths:"
        feedback_raw = response.split('Feedback:')[1].strip()
        return score, feedback_raw
    except Exception:
        # Fallback parsing
        try:
            score_line = [l for l in lines if 'Score:' in l][0]
            score = float(score_line.split(':')[1].strip().split('/')[0])
            return score, response
        except:
            return 5.0, response

def generate_interview_recommendation(role_type, responses_summary):
    """Generates an interview recommendation using Ollama."""
    prompt = f"""
    You are an AI career advisor. Based on a student's practice interview for the role of '{role_type}', provide a career recommendation and performance summary.
    
    Interview Summary:
    {responses_summary}
    
    Please provide:
    1. A score out of 10.
    2. A career recommendation and suggested improvements.
    
    Format your response EXACTLY like this:
    Score: [Number]
    Recommendation: [Text]
    """
    
    response = get_ai_response(prompt)
    if not response:
        return 0, "Recommendation failed due to AI engine error."
    
    try:
        score_line = [line for line in response.split('\n') if 'Score:' in line][0]
        score = float(score_line.split(':')[1].strip().split('/')[0])
        recommendation = response.split('Recommendation:')[1].strip()
        return score, recommendation
    except Exception:
        return 5.0, response # Fallback

def analyze_resume(resume_text):
    """Analyzes a resume and extracts key information using AI."""
    prompt = f"""
    You are an expert HR consultant and resume analyst. Please analyze the following resume and provide detailed feedback.
    
    Resume Content:
    {resume_text[:5000]}  # Limit to first 5000 chars to avoid token limits
    
    Please provide your analysis in the following format:
    Score: [Number out of 10]
    
    Key Skills Identified:
    - [Skill 1]
    - [Skill 2]
    - [Skill 3]
    (list up to 10 key skills)
    
    Suggestions for Improvement:
    - [Suggestion 1]
    - [Suggestion 2]
    - [Suggestion 3]
    
    Overall Assessment: [Brief paragraph about strengths and areas to improve]
    """
    
    response = get_ai_response(prompt)
    if not response:
        return 5.0, [], "Resume analysis failed due to AI engine error."
    
    # Parse response
    try:
        lines = response.split('\n')
        score = 5.0
        skills = []
        suggestions = ""
        assessment = ""
        
        for i, line in enumerate(lines):
            if 'Score:' in line:
                try:
                    score = float(line.split(':')[1].strip().split('/')[0])
                except:
                    score = 5.0
            elif 'Key Skills' in line:
                j = i + 1
                while j < len(lines) and lines[j].strip().startswith('-'):
                    skill = lines[j].strip().lstrip('- ')
                    if skill:
                        skills.append(skill)
                    j += 1
            elif 'Suggestions' in line:
                j = i + 1
                suggestions_list = []
                while j < len(lines) and lines[j].strip().startswith('-'):
                    sugg = lines[j].strip().lstrip('- ')
                    if sugg:
                        suggestions_list.append(sugg)
                    j += 1
                suggestions = "\n".join(suggestions_list)
            elif 'Overall Assessment' in line or 'Assessment:' in line:
                assessment = response.split('Overall Assessment:' if 'Overall Assessment' in response else 'Assessment:')[1].strip()
        
        return score, skills, assessment if assessment else suggestions
    except Exception as e:
        print(f"Error parsing resume analysis: {e}")
        return 5.0, [], response

def evaluate_proctoring_response(question, response_text, role_type):
    """Evaluates a response during a proctoring session."""
    prompt = f"""
    You are an expert interview evaluator for '{role_type}' positions. 
    
    Question: {question}
    
    Candidate Response: {response_text}
    
    Please evaluate this response and provide:
    1. A score out of 10.
    2. Key strengths in the response.
    3. Areas for improvement.
    4. Overall feedback.
    
    Format your response EXACTLY like this:
    Score: [Number]
    Strengths: [Text]
    Areas for Improvement: [Text]
    Feedback: [Text]
    """
    
    response = get_ai_response(prompt)
    if not response:
        return 5.0, "Evaluation failed due to AI engine error."
    
    try:
        score_line = [line for line in response.split('\n') if 'Score:' in line][0]
        score = float(score_line.split(':')[1].strip().split('/')[0])
        feedback = response.split('Feedback:')[1].strip() if 'Feedback:' in response else response
        return score, feedback
    except Exception:
        return 5.0, response

def analyze_proctoring_session(session_transcript, responses_data, duration_minutes):
    """Analyzes an entire proctoring session for integrity and quality."""
    prompt = f"""
    You are an expert exam proctoring analyst. Please analyze the following proctoring session data.
    
    Session Duration: {duration_minutes} minutes
    
    Session Transcript:
    {session_transcript[:3000]}
    
    Response Quality Summary:
    {json.dumps(responses_data)[:2000]}
    
    Please provide:
    1. Integrity Score (0-10): Assessment of exam integrity and lack of cheating indicators.
    2. Overall Quality Score (0-10): Quality of candidate's responses.
    3. Flagged Issues (if any): List any suspicious activities or concerns.
    4. Recommendations: Suggest next steps (pass, retake, manual review, etc.).
    
    Format your response EXACTLY like this:
    Integrity Score: [Number]
    Quality Score: [Number]
    Flagged Issues: [List or "None"]
    Recommendations: [Text]
    """
    
    response = get_ai_response(prompt)
    if not response:
        return 5.0, 5.0, [], "Analysis failed due to AI engine error."
    
    try:
        integrity_score = 5.0
        quality_score = 5.0
        issues = []
        recommendations = ""
        
        for line in response.split('\n'):
            if 'Integrity Score:' in line:
                integrity_score = float(line.split(':')[1].strip().split('/')[0])
            elif 'Quality Score:' in line:
                quality_score = float(line.split(':')[1].strip().split('/')[0])
            elif 'Flagged Issues:' in line:
                issues_text = line.split(':')[1].strip()
                if 'None' not in issues_text:
                    issues = [x.strip() for x in issues_text.split(',') if x.strip()]
        
        if 'Recommendations:' in response:
            recommendations = response.split('Recommendations:')[1].strip()
        
        return integrity_score, quality_score, issues, recommendations
    except Exception as e:
        print(f"Error analyzing proctoring session: {e}")
        return 5.0, 5.0, [], response
