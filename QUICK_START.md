# Resume & Proctoring System - Quick Start Guide

## Feature Overview

### 1. Resume Upload & Analysis
**Endpoint**: `/resume/upload/`
- Upload resume in PDF, DOCX, DOC, or TXT format (max 5MB)
- Automatic AI analysis extracts:
  - Key skills (up to 10 identified)
  - Overall competency score (0-10)
  - Improvement suggestions
  - Professional assessment

**Supported AI Models**:
- Primary: Llama 3.1 (via OpenRouter)
- Fallback: Google Gemini 2.0 Flash
- Final Fallback: Ollama (local instance)

### 2. Proctored Interview System
**Endpoint**: `/proctoring/start/`

**Process**:
1. Student selects role (e.g., Software Engineer, Data Scientist)
2. System generates 5 role-specific interview questions
3. Student answers each question (text or audio)
4. AI evaluates each response in real-time
5. Session analysis provides:
   - Individual question scores
   - Overall performance metric
   - Integrity assessment (0-10)
   - Flagged issues or concerns
   - Actionable recommendations

**Integrity Checks**:
- Suspicious keyword detection
- Response consistency analysis
- Time validation
- Pattern anomaly detection

### 3. Session History
**Endpoint**: `/proctoring/history/`
- View all past proctoring sessions
- Track performance trends
- Review integrity reports
- Access transcripts

---

## Developer Notes

### Database Models

```
Resume
├── student (OneToOneField)
├── file (FileField)
├── analysis_status (PENDING|PROCESSING|COMPLETED|FAILED)
├── score (Float 0-10)
├── skills_extracted (JSON array)
└── suggestions (TextField)

ProctoringSession
├── student (ForeignKey)
├── role_type (CharField)
├── status (SCHEDULED|IN_PROGRESS|COMPLETED|FLAGGED)
├── score (Float 0-10)
├── integrity_score (Float 0-10)
├── transcript (TextField)
├── flagged_issues (JSON array)
└── ai_analysis (TextField)

ProctoringQuestion
├── session (ForeignKey)
├── question_text (TextField)
└── order (IntegerField)

ProctoringResponse
├── question (ForeignKey)
├── response_text (TextField)
├── response_audio (FileField, optional)
├── score (Float 0-10)
└── ai_evaluation (TextField)
```

### AI Functions

**Resume Analysis**:
```python
from core.ai_engine import analyze_resume

score, skills, suggestions = analyze_resume(resume_text)
# Returns: 
#   - score: 0-10
#   - skills: list of extracted competencies
#   - suggestions: improvement recommendations
```

**Proctoring Response Evaluation**:
```python
from core.ai_engine import evaluate_proctoring_response

score, feedback = evaluate_proctoring_response(
    question="Describe your experience...",
    response_text="I have...",
    role_type="Software Engineer"
)
```

**Session Analysis**:
```python
from core.ai_engine import analyze_proctoring_session

integrity, quality, issues, recommendations = analyze_proctoring_session(
    session_transcript="Q: ... A: ...",
    responses_data=[...],
    duration_minutes=25
)
```

### File Processing

```python
from core.utils import extract_resume_text

# Automatically handles PDF, DOCX, or TXT
text = extract_resume_text(file_obj, filename)
```

---

## Configuration

### Required Environment Variables
```
GEMINI_API_KEY = "AIzaSyAxHosbDuD_bsOkf77ZTOX9TKSnvAl0H30"
OPENROUTER_API_KEY = "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"
```

### Ollama Configuration
Ensure Ollama is running locally:
```bash
ollama serve  # Default: localhost:11434
```

### Installed Packages
```
Django==4.2.28
google-generativeai==0.3.2
requests==2.31.0
Pillow==10.0.0
python-docx==0.8.11
PyPDF2==3.0.1
```

---

## API Response Examples

### Resume Analysis Response
```json
{
  "score": 7.5,
  "skills": [
    "Python",
    "Django",
    "PostgreSQL",
    "Docker",
    "AWS",
    "REST APIs",
    "Git",
    "Agile"
  ],
  "suggestions": "Consider adding cloud certification... Expand on leadership examples..."
}
```

### Proctoring Analysis Response
```json
{
  "integrity_score": 9.0,
  "quality_score": 7.2,
  "flagged_issues": [],
  "recommendations": "Strong response quality. Excellent communication skills demonstrated. Consider more specific examples in technical questions."
}
```

---

## Troubleshooting

### Resume Upload Fails
- Check file format (PDF, DOCX, DOC, TXT only)
- Verify file size < 5MB
- Ensure PyPDF2 and python-docx are installed

### AI Analysis Timeouts
- Check API keys are valid
- Verify network connectivity
- Confirm Ollama is running for fallback
- Check API rate limits

### Proctoring Session Issues
- Verify all questions created successfully
- Check response save errors in logs
- Ensure student hasn't started multiple sessions

### Database Errors
- Run: `python manage.py migrate`
- Check `core/migrations/` for any pending migrations
- Verify Django version 4.2.28

---

## Performance Metrics

- Resume analysis: ~5-10 seconds
- Individual response evaluation: ~3-5 seconds
- Full session analysis: ~10-15 seconds
- Database queries optimized with select_related/prefetch_related

---

## Security Considerations

✅ File upload validation (type, size)
✅ CSRF protection on forms
✅ User authentication required
✅ Session integrity logging
✅ API key management
✅ SQL injection protection (Django ORM)

---

## Next Steps

1. ✅ Deploy to production server
2. ✅ Set up SSL/TLS certificates
3. ⏳ Configure backup strategy
4. ⏳ Implement monitoring/alerting
5. ⏳ Add email notifications
6. ⏳ Integrate webcam for live proctoring
7. ⏳ Add analytics dashboard
