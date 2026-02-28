# Resume Uniqueness Checking System

## Overview
The resume analyzer now includes a comprehensive uniqueness checking system that prevents duplicate resume uploads. The system analyzes key professional attributes and compares incoming resumes against existing ones to ensure diversity in the candidate pool.

## Features

### 1. **Multi-Factor Similarity Analysis**
The system extracts and compares multiple resume attributes:

- **Skills (40% weight)**: Technical and soft skills mentioned in the resume
- **Education (15% weight)**: Degrees and qualifications
- **Experience (15% weight)**: Years of professional experience
- **Projects (20% weight)**: Key projects and accomplishments
- **Roles/Titles (10% weight)**: Professional roles and job titles

### 2. **Similarity Threshold**
- **Default Threshold**: 75% similarity
- Resumes with similarity scores ≥ 75% are rejected as duplicates
- Resumes with similarity < 75% are accepted and stored in the fingerprint database

### 3. **Resume Fingerprinting**
Each accepted resume is stored with:
- **SHA256 Hash**: Unique fingerprint based on extracted features
- **Feature Set**: Extracted skills, education, experience, projects, and roles
- **Timestamp**: When the resume was stored

### 4. **Error Handling**
When a duplicate/similar resume is uploaded, users receive:
```
❌ Resume Upload Failed: This resume is too similar to an existing resume. 
Similarity Score: 85%

Your resume must be unique with distinct:
✓ Career insights and professional roles
✓ Technical skills and expertise areas
✓ Projects and accomplishments

Please upload a resume that represents a different professional profile.
```

## Implementation Details

### Modified Files

#### 1. Resume Analyzer Models
Updated in three locations for consistency:
- `/AIHiring/models/resume_analyzer.py`
- `/ar/models/resume_analyzer.py`
- `/core/ai_models/resume_analyzer.py`

#### 2. Flask Applications
Updated both resume analyzer apps:
- `/AIHiring/resume_analyzer_app.py`
- `/ar/resume_analyzer_app.py`

### Database Structure

Resume fingerprints are stored in JSON format at:
```
data/resumes/resume_fingerprints.json
```

Example structure:
```json
{
  "resumes": [
    {
      "hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
      "features": {
        "skills": ["Python", "JavaScript", "React", "Node.js"],
        "education": ["Bachelor", "Master"],
        "experience": "5",
        "projects": ["Project 1", "Project 2"],
        "roles": ["developer", "engineer"]
      },
      "timestamp": "2024-02-28 10:30:45"
    }
  ]
}
```

## Key Methods Added

### 1. `check_and_validate_resume(text)`
Main entry point for checking resume uniqueness.
- **Input**: Resume text content
- **Output**: `(is_valid: bool, error_message: str or None)`
- **Process**: Extracts features → Computes fingerprint → Checks similarity

### 2. `_extract_key_features(text)`
Extracts professional attributes from resume text.
- Skills by category
- Education levels
- Years of experience
- Projects and achievements
- Professional roles/titles

### 3. `_calculate_similarity(features1, features2)`
Computes similarity score between two resume feature sets.
- **Returns**: Float between 0.0 and 1.0
- **Uses**: Set intersection for categorical fields, SequenceMatcher for text fields

### 4. `_check_resume_uniqueness(features, similarity_threshold)`
Compares new resume against all existing resumes.
- Finds maximum similarity score
- Returns (is_unique, max_similarity, error_message)

### 5. `_store_resume_fingerprint(fingerprint_hash, features)`
Stores accepted resume fingerprint in database.
- Ensures future comparisons can be made
- Maintains historical record of uploaded resumes

## Workflow

```
Resume Upload
    ↓
Parse Resume Text
    ↓
Extract Key Features
    ↓
Compute Fingerprint Hash
    ↓
Check Uniqueness
    ├─→ Similarity ≥ 75%? → REJECT (Return Error)
    └─→ Similarity < 75%? → ACCEPT
         ↓
      Store Fingerprint
         ↓
      Analyze Resume
         ↓
      Return Analysis
```

## Usage Examples

### Accepting a Unique Resume
```python
resume_analyzer = ResumeAnalyzer()
resume_text = "Python, Java, 5 years experience, BS in CS..."

is_valid, error_msg = resume_analyzer.check_and_validate_resume(resume_text)
# is_valid = True, error_msg = None
# Resume fingerprint stored automatically
```

### Rejecting a Duplicate Resume
```python
resume_text = # Exact same resume or >75% similar
is_valid, error_msg = resume_analyzer.check_and_validate_resume(resume_text)
# is_valid = False
# error_msg = "Resume Upload Failed: This resume is too similar..."
```

## API Response Codes

- **200 OK**: Resume uploaded successfully (unique)
- **409 Conflict**: Resume rejected (too similar to existing)
- **400 Bad Request**: Invalid file format
- **500 Internal Server Error**: Processing error

## Configuration

To adjust the similarity threshold, modify in the resume analyzer class:

```python
# Default: 0.75 (75%)
is_unique, similarity_score, error_msg = self._check_resume_uniqueness(
    features, 
    similarity_threshold=0.75
)
```

Lower values = stricter uniqueness requirements
Higher values = more lenient uniqueness requirements

## Minimal Similarities Allowed

The system allows minimal similarities while still requiring distinct:
- Primary technical skill sets
- Career progression and roles
- Educational background (if significant)
- Major project achievements

Example of accepted variation:
- Resume A: Python, Django, 3 years, Bachelor's, E-commerce project
- Resume B: JavaScript, React, 4 years, Master's, SaaS project
- Similarity: ~45% (Different enough to accept)

Example of rejected duplication:
- Resume A: Python, Java, React, 5 years, BS, Startup work
- Resume B: Python, Java, React, 5 years, BS, Startup work
- Similarity: ~92% (Too similar - rejected)

## Future Enhancements

Potential improvements:
1. **Weighted similarity**: Different weights for different roles
2. **Skill category matching**: Only compare relevant skill types
3. **Machine learning**: Use NLP models to detect paraphrased resumes
4. **Geographic diversity**: Track location-based resume distribution
5. **Admin override**: Allow manual resume acceptance

## Testing

To test the uniqueness system:

```bash
# Test with duplicate resume
python -c "
from models.resume_analyzer import ResumeAnalyzer
analyzer = ResumeAnalyzer()

resume1 = 'Python, Java, 5 years, Experience with Django and Flask'
resume2 = 'Python, Java, 5 years, Experience with Django and Flask'

is_valid1, error1 = analyzer.check_and_validate_resume(resume1)
print(f'Resume 1: Valid={is_valid1}')

is_valid2, error2 = analyzer.check_and_validate_resume(resume2)
print(f'Resume 2: Valid={is_valid2}, Error={error2}')
"
```

## Troubleshooting

### Issue: All resumes are rejected
- **Cause**: Threshold too low (< 0.5)
- **Solution**: Increase threshold value

### Issue: Similar resumes are accepted
- **Cause**: Threshold too high (> 0.85)
- **Solution**: Decrease threshold value

### Issue: Fingerprint file not found
- **Cause**: Directory not created
- **Solution**: Run `mkdir -p data/resumes/` in each app directory

### Issue: Permission denied error
- **Cause**: Insufficient write permissions
- **Solution**: Check directory permissions and file ownership

## Summary

The resume uniqueness checking system provides:
- ✅ Prevents duplicate resume submissions
- ✅ Allows minimal acceptable variations
- ✅ Maintains detailed comparison metrics
- ✅ Stores historical record of all uploads
- ✅ Provides clear user feedback on rejection
- ✅ Scalable to large resume databases
