# Plagiarism Detection - Quick Reference Guide

## What It Does
Detects how much a resume is copied/plagiarized using AI, returning a **0-100% plagiarism score**.

## How It Works

### Dual Detection System
```
Hugging Face + Router AI
        ↓
  Combined Analysis
        ↓
 Plagiarism % + Risk Level
```

## Output Format

```json
{
  "percentage": 45.5,                    // 0-100 plagiarism score
  "authenticity_score": 72.0,            // How genuine it sounds
  "risk_level": "medium",                // low / medium / high
  "sources_checked": ["huggingface", "router_ai"],
  "details": {
    "huggingface": {
      "percentage": 48,
      "detected_templates": ["Generic objective"],
      "suspicious_sections": ["Summary", "Skills"]
    },
    "router_ai": {
      "percentage": 43,
      "authenticity_score": 72,
      "observations": ["Some buzzwords", "Good context"],
      "risk_level": "medium"
    }
  }
}
```

## Plagiarism Score Interpretation

| Score | Risk | Status |
|-------|------|--------|
| 0-30% | ✅ Low | Authentic, Original |
| 31-60% | ⚠️ Medium | Some Concerns |
| 61-100% | ❌ High | Heavily Copied/Templated |

## Authenticity Score

| Score | Assessment |
|-------|------------|
| 80-100% | Highly authentic, personal writing |
| 50-79% | Mostly authentic with some generic sections |
| 0-49% | Heavily templated or copied |

## Risk Levels

- **Low**: Proceed normally, resume appears authentic
- **Medium**: Verify achievements and claims in interview
- **High**: Strong evidence of plagiarism, consider rejecting

## Integration

Plagiarism detection is **automatically included** when analyzing a resume:

```python
analysis = resume_analyzer.analyze_resume_text(resume_text)
plagiarism_info = analysis['plagiarism']  # Contains plagiarism detection results
```

## API Keys Required

```bash
export HUGGINGFACE_API_KEY="hf_xxxxx"
export ROUTER_API_KEY="sk-xxxxx"
```

## Using in Flask App

```python
@app.route('/analyze_resume', methods=['POST'])
def analyze_resume():
    # ... file handling ...
    
    analysis = resume_analyzer.analyze_resume_text(resume_text)
    
    # Plagiarism info is in analysis['plagiarism']
    plagiarism = analysis['plagiarism']
    
    if plagiarism['risk_level'] == 'high':
        # Alert recruiter about high plagiarism
        pass
    
    return render_template('resume_analysis.html', analysis=analysis)
```

## Standalone Usage

```python
# Direct plagiarism check only
result = analyzer._get_plagiarism_percentage(resume_text)

print(f"Plagiarism: {result['percentage']:.1f}%")
print(f"Risk: {result['risk_level']}")
```

## Detection Examples

### ✅ Low Plagiarism (Original Resume)
```
"Led 8 developers in rebuilding monolith → microservices,
reducing deployment time 45min → 5min, saving $2.4M annually"

Plagiarism: 15% | Authenticity: 92% | Risk: LOW
Reason: Specific metrics, clear impact, unique achievement
```

### ⚠️ Medium Plagiarism (Some Templates)
```
"Spearheaded implementation of new processes and technologies
to drive innovation and maximize team productivity"

Plagiarism: 50% | Authenticity: 65% | Risk: MEDIUM
Reason: Generic buzzwords, lacks specific examples
```

### ❌ High Plagiarism (Heavily Templated)
```
"Passionate about leveraging cutting-edge technologies to
deliver innovative solutions and drive business value"

Plagiarism: 82% | Authenticity: 35% | Risk: HIGH
Reason: Almost entirely from templates, no personal context
```

## Methods Available

### Main Method
```python
result = analyzer._get_plagiarism_percentage(text)
```
Returns complete plagiarism analysis with both AI sources

### Individual Detectors
```python
hf_result = analyzer._detect_plagiarism_hf(text)
router_result = analyzer._detect_plagiarism_router_ai(text)
```

## Response Times
- Hugging Face: 5-20 seconds
- Router AI: 3-10 seconds
- **Total: 8-30 seconds per resume**

## Error Handling
If APIs are unavailable:
- Returns default scores (0% plagiarism, 50% authenticity)
- Includes error message in response
- Allows resume to proceed with warning

## Best Practices

### For Recruiters
1. Use as screening tool for initial assessment
2. High plagiarism score = investigate further
3. Verify claims in interview stage
4. Don't reject solely based on plagiarism %

### For Candidates
1. Write experiences in your own words
2. Include specific numbers and metrics
3. Show impact with concrete examples
4. Let your personality show through
5. Avoid overused buzzwords without context

## Troubleshooting

**High score for legitimate resume?**
- Add more specific metrics
- Include personal achievements
- Vary sentence structure
- Add context and impact

**API errors?**
- Check API keys are set
- Verify network connection
- Check rate limiting
- Retry with smaller text

**Conflicting scores?**
- Normal - different AI models have different sensitivity
- Use average score (already calculated)
- Review observations from both sources

## What Gets Detected

✅ Detected by Hugging Face:
- Resume templates usage
- Generic objectives and summaries
- Overused action verbs without context
- Standard resume structures
- Common industry jargons

✅ Detected by Router AI:
- Copied content from job descriptions
- Generic vs personal writing patterns
- Inconsistencies suggesting copying
- Buzzwords without specific examples
- Lack of personal voice

## Files Modified

All resume analyzers now include plagiarism detection:
- `AIHiring/models/resume_analyzer.py`
- `ar/models/resume_analyzer.py`
- `core/ai_models/resume_analyzer.py`
- `AIHiring/resume_analyzer_app.py`
- `ar/resume_analyzer_app.py`

## Related Documentation

See `PLAGIARISM_DETECTION_DOCUMENTATION.md` for detailed information including:
- Architecture and implementation details
- Complete API response examples
- Advanced usage scenarios
- Performance benchmarks
- Future enhancements
