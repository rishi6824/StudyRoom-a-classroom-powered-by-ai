# System Architecture & Data Flow

## Database Schema

```
User (Django Auth)
├── Profile 1:1
│   ├── Resume 1:1
│   ├── ProctoringSession 1:N
│   │   ├── ProctoringQuestion 1:N
│   │   │   └── ProctoringResponse 1:N
│   ├── Submission 1:N (Legacy)
│   └── Interview 1:N (Legacy)
└── Created Assignments 1:N (Legacy)
```

## AI Processing Pipeline

### Resume Analysis Flow
```
Upload Resume
    ↓
[File Type Check]
    ├─ PDF → PyPDF2 extraction
    ├─ DOCX → python-docx extraction
    └─ TXT → Direct read
    ↓
[Text Preprocessing]
    ├─ Clean
    ├─ Normalize
    └─ Extract metadata
    ↓
[AI Analysis (Multi-step)]
    1. OpenRouter (LLaMA 3.1)
    2. Gemini 2.0 Flash (fallback)
    3. Ollama (final fallback)
    ↓
[Parse Response]
    ├─ Extract Score (0-10)
    ├─ Extract Skills (list)
    └─ Extract Suggestions (text)
    ↓
[Store in Database]
    ├─ Update Resume model
    ├─ Set analysis_status = COMPLETED
    └─ Cache results for display
    ↓
Display Results to User
```

### Proctoring Session Flow
```
Start Session
    ↓
Generate 5 Interview Questions
    ├─ Question 1: Project experience
    ├─ Question 2: Technical skills
    ├─ Question 3: Team collaboration
    ├─ Question 4: Learning/growth
    └─ Question 5: Company fit
    ↓
For Each Question:
    ├─ Display question to student
    ├─ Capture response (text/audio)
    ├─ AI Evaluate response
    │   ├─ Score 0-10
    │   ├─ Provide feedback
    │   └─ Store evaluation
    └─ Continue to next question
    ↓
Session Complete
    ├─ Generate full transcript
    ├─ Aggregate all scores
    ├─ Run integrity analysis
    └─ Detect suspicious patterns
    ↓
[Integrity Analysis]
    ├─ Keyword pattern matching
    ├─ Response consistency check
    ├─ Time validation
    └─ Anomaly detection
    ↓
[Final Scoring]
    ├─ Quality Score = avg(all response scores)
    ├─ Integrity Score = integrity_analysis()
    ├─ Overall Assessment = quality + integrity check
    └─ Flag if integrity_score < threshold
    ↓
Generate Report
    ├─ Performance metrics
    ├─ Transcript
    ├─ AI recommendations
    └─ Flagged issues
```

## API Integration Architecture

```
┌─────────────────────────────────────┐
│     Django Application              │
│  (Resume & Proctoring Views)        │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        ↓             ↓
┌──────────────┐ ┌──────────────┐
│  OpenRouter  │ │   Gemini     │
│  (Primary)   │ │   (Fallback) │
└──────────────┘ └──────────────┘
        │             │
        └──────┬──────┘
               ↓
      ┌──────────────────┐
      │  Local Ollama    │
      │  (Final Fallback)│
      └──────────────────┘
        (localhost:11434)
```

## Data Flow Diagrams

### Resume Upload
```
Student uploads resume (PDF/DOCX/TXT)
                ↓
         Django form validation
         (type, size checks)
                ↓
         Extract text from file
         (PyPDF2 / python-docx)
                ↓
         Send to AI API
         (with retry logic)
                ↓
         Parse AI response
         (score, skills, suggestions)
                ↓
         Save to Resume model
         (analysis_status = COMPLETED)
                ↓
         Redirect to resume_detail view
         (display results)
```

### Proctoring Session
```
Student initiates session → Select role → System generates 5 questions
                                                    ↓
                                         Display Question #1
                                                    ↓
                                    Capture student response
                                    (text or audio file)
                                                    ↓
                                    Send to AI for evaluation
                                                    ↓
                                    Store response & score
                                                    ↓
                                    Loop: Questions 2-5
                                                    ↓
                                    Compile full transcript
                                                    ↓
                                    Run integrity check
                                    (suspicious keywords, etc.)
                                                    ↓
                                    Store final scores & flags
                                                    ↓
                                    Redirect to completion page
                                    (show results & report)
```

## File Storage Structure

```
Django Project Root
├── db.sqlite3
├── media/
│   ├── profile_pics/        (Profile photos)
│   ├── resumes/             (Uploaded resume files)
│   │   ├── student_1_resume.pdf
│   │   └── student_2_resume.docx
│   ├── proctoring_videos/   (Session videos)
│   │   └── session_1_video.mp4
│   ├── proctoring_audio/    (Session audio)
│   │   └── session_1_audio.wav
│   ├── responses_audio/     (Individual response audio)
│   │   ├── response_1.wav
│   │   └── response_2.wav
│   └── submissions/         (Legacy assignment submissions)
└── static/                  (CSS, JS, images)
```

## Configuration & Environment

```
Settings:
├── API Keys
│   ├── GEMINI_API_KEY
│   └── OPENROUTER_API_KEY
├── Model Configuration
│   ├── OLLAMA_API_URL = "http://localhost:11434/api/generate"
│   ├── DEFAULT_MODEL = "llama3.2"
│   └── OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct"
├── File Upload Settings
│   ├── MAX_FILE_SIZE = 5MB
│   ├── ALLOWED_RESUME_FORMATS = [pdf, docx, doc, txt]
│   └── MEDIA_URL = "/media/"
└── Proctoring Settings
    ├── QUESTIONS_PER_SESSION = 5
    ├── SCORE_SCALE = 0-10
    └── INTEGRITY_THRESHOLD = 6.0
```

## Error Handling Flow

```
AI API Call
    ↓
[Try OpenRouter]
    ├─ Success → Return response
    └─ Fail → Log error & try Gemini
              ↓
         [Try Gemini]
         ├─ Success → Return response
         └─ Fail → Log error & try Ollama
                   ↓
              [Try Ollama]
              ├─ Success → Return response
              └─ Fail → Return default score (5.0)
                        & generic feedback
                        & Log critical error
```

## Performance Optimization

### Database Queries
- Resume detail: `select_related('student__profile')`
- Session detail: `prefetch_related('questions__responses')`
- History view: bulk queries with select_related

### Caching
- Session results cached during analysis
- AI responses stored immediately (no re-analysis)
- Skills list cached in JSON field

### Async Processing (Future)
- Resume analysis in background task (Celery)
- Session integrity checks async
- Email notifications async
- Transcription processing async

## Security Implementation

```
Authentication
├─ Django User model
├─ Login required decorator
└─ Permission checks for teacher-only views

File Security
├─ MIME type validation
├─ File size limits
├─ Virus scanning (future)
└─ Secure storage location

API Security
├─ Rate limiting (future)
├─ Request signing
├─ API key rotation
└─ HTTPS only (production)

Session Security
├─ CSRF tokens
├─ Session cookies secure flag
├─ Integrity checks on resume
└─ Flagging of suspicious sessions
```

## Monitoring & Logging

```
Django Logging:
├── AI API calls (request/response)
├── File upload operations
├── Analysis status updates
├── Error tracking
└── User activity

Database Monitoring:
├── Query performance
├── Storage usage
├── Backup status
└── Integrity checks

Application Metrics:
├── API response times
├── Success/failure rates
├── Active sessions
└── Resume analysis queue
```

## Deployment Checklist

- [ ] Set environment variables (API keys)
- [ ] Run migrations (`python manage.py migrate`)
- [ ] Collect static files (`python manage.py collectstatic`)
- [ ] Configure Ollama (if local fallback desired)
- [ ] Set up media file storage
- [ ] Configure webhooks (if async processing)
- [ ] Enable SSL/TLS
- [ ] Set up backup strategy
- [ ] Configure logging & monitoring
- [ ] Load test before production
- [ ] Create admin superuser
- [ ] Test all AI fallback paths

## Scalability Considerations

**Current Setup**: Single server, single database
**Scale-up Path**:
1. Database replication (read replicas)
2. API caching layer (Redis)
3. Load balancing for API calls
4. Message queue for async tasks (Celery + RabbitMQ)
5. File storage (S3 or similar)
6. Microservices for AI analysis

**Expected Load**:
- 100s students/day: Current setup sufficient
- 1000s students/day: Add caching & async
- 10000s students/day: Full scaling required
