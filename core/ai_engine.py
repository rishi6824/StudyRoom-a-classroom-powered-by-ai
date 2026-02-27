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

def evaluate_assignment(assignment_title, assignment_description, submission_content):
    """Evaluates an assignment using Ollama."""
    prompt = f"""
    You are an expert academic evaluator. Please evaluate the following student submission for the assignment titled '{assignment_title}'.
    
    Assignment Description:
    {assignment_description}
    
    Student Submission:
    {submission_content}
    
    Please provide:
    1. A score out of 10.
    2. Detailed constructive feedback.
    
    Format your response EXACTLY like this:
    Score: [Number]
    Feedback: [Text]
    """
    
    response = get_ai_response(prompt)
    if not response:
        return 0, "Evaluation failed due to AI engine error."
    
    # Simple parsing logic
    try:
        score_line = [line for line in response.split('\n') if 'Score:' in line][0]
        score = float(score_line.split(':')[1].strip().split('/')[0])
        feedback = response.split('Feedback:')[1].strip()
        return score, feedback
    except Exception:
        return 5.0, response # Fallback: return raw response as feedback with a neutral score

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
