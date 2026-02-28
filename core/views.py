from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
from .forms import SignUpForm, AssignmentForm, SubmissionForm, ResumeUploadForm, ProctoringSessionForm, ProctoringResponseForm
from .models import Profile, Assignment, Submission, Interview, Resume, ProctoringSession, ProctoringQuestion, ProctoringResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from .ai_engine import evaluate_assignment, generate_interview_recommendation, analyze_resume, evaluate_proctoring_response, analyze_proctoring_session
from .utils import extract_resume_text, parse_ai_evaluation_response
from datetime import datetime
from .ai_models.question_generator import QuestionGenerator
from .ai_models.ai_interviewer import AIInterviewer
from .ai_models.physical_analyzer import PhysicalAnalyzer
from .ai_models.config import Config

question_generator = QuestionGenerator()
ai_interviewer = AIInterviewer()
physical_analyzer = PhysicalAnalyzer()

class HomeView(TemplateView):
    template_name = 'core/home.html'

class SignUpView(CreateView):
    form_class = SignUpForm
    success_url = reverse_lazy('login')
    template_name = 'core/signup.html'

@login_required
def dashboard(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        # Fallback if profile signal failed for some reason
        profile = Profile.objects.create(user=request.user)
    
    if profile.role == 'TEACHER':
        assignments = Assignment.objects.filter(teacher=request.user)
        return render(request, 'core/teacher_dashboard.html', {'assignments': assignments})
    else:
        # Student logic
        submissions = Submission.objects.filter(student=request.user)
        available_assignments = Assignment.objects.exclude(submissions__student=request.user)
        return render(request, 'core/student_dashboard.html', {
            'submissions': submissions,
            'available_assignments': available_assignments
        })

@login_required
def create_assignment(request):
    if request.user.profile.role != 'TEACHER':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AssignmentForm(request.POST)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.teacher = request.user
            assignment.save()
            return redirect('dashboard')
    else:
        form = AssignmentForm()
    
    return render(request, 'core/create_assignment.html', {'form': form})

@login_required
def view_assignment(request, pk):
    assignment = Assignment.objects.get(pk=pk)
    submission = Submission.objects.filter(assignment=assignment, student=request.user).first()
    return render(request, 'core/assignment_detail.html', {
        'assignment': assignment,
        'submission': submission
    })

@login_required
def submit_assignment(request, pk):
    assignment = Assignment.objects.get(pk=pk)
    if request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.assignment = assignment
            submission.student = request.user
            submission.save() # Save first to get the file path
            
            # Read file content for AI Evaluation
            content = "No readable content."
            try:
                with submission.file.open('r') as f:
                    content = f.read(5000) # Read first 5k characters
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"Error reading submission file: {e}")
            
            # Call AI for Evaluation
            score, feedback = evaluate_assignment(
                assignment.title, 
                assignment.description, 
                content,
                rubric=assignment.rubric
            )
            
            submission.score = score
            submission.ai_feedback = feedback
            submission.save()
            
            return redirect('dashboard')
    else:
        form = SubmissionForm()
    
    return render(request, 'core/submit_assignment.html', {
        'form': form,
        'assignment': assignment
    })

@login_required
def interview_setup(request):
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
    return render(request, 'core/interview_setup.html')

@login_required
def start_interview_with_name(request):
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
        
    if request.method == 'POST':
        candidate_name = request.POST.get('candidate_name', '').strip()
    else:
        candidate_name = request.GET.get('candidate_name', '').strip()

    if not candidate_name:
        return JsonResponse({'error': 'Candidate name is required'}, status=400)

    # Clear previous interview specific session vars
    for key in ['candidate_name', 'job_role', 'interview_id', 'current_question', 'score', 'responses', 'start_time', 'enable_voice', 'questions', 'total_questions_target']:
        if key in request.session:
            del request.session[key]

    request.session['candidate_name'] = candidate_name
    request.session['job_role'] = 'software_engineer'
    
    interview = Interview.objects.create(
        student=request.user,
        role_type='software_engineer',
        score=0,
        ai_recommendation=''
    )
    request.session['interview_id'] = interview.id

    request.session['current_question'] = 0
    request.session['score'] = 0
    request.session['responses'] = []
    request.session['start_time'] = datetime.now().isoformat()
    request.session['enable_voice'] = True

    target_total = max(Config.MIN_QUESTIONS, min(Config.MAX_QUESTIONS, Config.DEFAULT_QUESTIONS))
    request.session['total_questions_target'] = target_total

    resume_analysis = request.session.get('resume_analysis', {})
    print(f"DEBUG: Generating questions for {candidate_name}...")
    questions = question_generator.generate_questions_raw('software_engineer', resume_analysis, target_total)
    print(f"DEBUG: Generated {len(questions) if questions else 0} questions.")

    if not questions:
        questions = [{
            "question": "Tell me about yourself and your most relevant experience for this role.",
            "type": "behavioral",
            "difficulty": "easy"
        }]

    request.session['questions'] = questions
    
    xreq = request.headers.get('X-Requested-With', '')
    accept_header = request.headers.get('Accept', '')
    if xreq != 'XMLHttpRequest' and 'application/json' not in accept_header:
        request.session.modified = True 
        return redirect('interview_room')

    request.session.modified = True
    from django.urls import reverse
    return JsonResponse({
        'success': True,
        'redirect': reverse('interview_room')
    })

@login_required
def interview_room(request):
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
        
    if 'interview_id' not in request.session:
        return redirect('dashboard')
    
    if 'total_questions_target' not in request.session:
        request.session['total_questions_target'] = max(Config.MIN_QUESTIONS, min(Config.MAX_QUESTIONS, Config.DEFAULT_QUESTIONS))

    if 'questions' not in request.session or not request.session['questions']:
        job_role = request.session.get('job_role', 'software_engineer')
        resume_analysis = request.session.get('resume_analysis', {})
        first_batch = question_generator.generate_questions_raw(job_role, resume_analysis, 1)
        request.session['questions'] = first_batch if first_batch else [{
            "question": "Tell me about yourself and your most relevant experience for this role.",
            "type": "behavioral",
            "difficulty": "easy"
        }]
        request.session['current_question'] = 0
    
    current_q = request.session.get('current_question', 0)
    questions = request.session.get('questions', [])
    target_total = request.session.get('total_questions_target', len(questions))
    
    if current_q >= target_total:
        return redirect('interview_results')

    if current_q >= len(questions):
        job_role = request.session.get('job_role', 'software_engineer')
        resume_analysis = request.session.get('resume_analysis', {})
        prev_answer = None
        if request.session.get('responses'):
            prev_answer = request.session['responses'][-1].get('answer')
        next_q = question_generator.generate_next_question(job_role, resume_analysis, questions, prev_answer)
        questions.append(next_q)
        request.session['questions'] = questions
        request.session.modified = True
    
    question = questions[current_q]
    return render(request, 'core/interview_room.html', {
        'question': question,
        'question_num': current_q + 1,
        'total_questions': target_total,
        'enable_voice': request.session.get('enable_voice', True)
    })

@login_required
def get_next_question(request):
    if 'interview_id' not in request.session:
        return JsonResponse({'error': 'No active interview'}, status=400)
    
    current_q = request.session.get('current_question', 0)
    questions = request.session.get('questions', [])
    target_total = request.session.get('total_questions_target', len(questions))
    
    if current_q >= target_total:
        return JsonResponse({'completed': True})
    
    if current_q >= len(questions):
        job_role = request.session.get('job_role', 'software_engineer')
        resume_analysis = request.session.get('resume_analysis', {})
        prev_answer = None
        if request.session.get('responses'):
            prev_answer = request.session['responses'][-1].get('answer')
        next_q = question_generator.generate_next_question(job_role, resume_analysis, questions, prev_answer)
        questions.append(next_q)
        request.session['questions'] = questions
        request.session.modified = True

    question = questions[current_q]
    return JsonResponse({
        'question': question['question'],
        'question_num': current_q + 1,
        'total_questions': target_total,
        'type': question.get('type', 'технический')
    })

@login_required
@require_http_methods(["POST"])
def submit_answer(request):
    if 'interview_id' not in request.session:
        return JsonResponse({'error': 'No active interview'}, status=400)
    
    current_q = request.session.get('current_question', 0)
    questions = request.session.get('questions', [])
    
    if current_q >= len(questions):
        return JsonResponse({
            'completed': True,
            'next_question': current_q,
            'score': 0,
            'feedback': 'Interview completed!',
            'detailed_analysis': {}
        })
    
    answer = request.POST.get('answer', '')
    job_role = request.session.get('job_role', 'software_engineer')
    resume_analysis = request.session.get('resume_analysis', {})
    
    score, feedback, detailed_analysis = ai_interviewer.analyze_answer(
        job_role, current_q, answer, resume_analysis
    )
    
    if score >= 8:
        ai_feedback = f"Excellent! {feedback} That was a well-structured response."
    elif score >= 6:
        ai_feedback = f"Good job. {feedback} You're on the right track."
    elif score >= 4:
        ai_feedback = f"Okay. {feedback} Let's work on improving this."
    else:
        ai_feedback = f"I see. {feedback} We'll practice more on this area."
    
    response_data = {
        'question_index': current_q,
        'question': questions[current_q]['question'],
        'answer': answer,
        'score': score,
        'feedback': ai_feedback,
        'detailed_analysis': detailed_analysis
    }
    
    responses = request.session.get('responses', [])
    responses.append(response_data)
    request.session['responses'] = responses
    
    current_score = request.session.get('score', 0)
    request.session['score'] = current_score + score
    request.session['current_question'] = current_q + 1
    
    target_total = request.session.get('total_questions_target', len(questions))
    completed = request.session['current_question'] >= target_total

    if completed:
        avg_score = request.session['score'] / len(responses) if responses else 0
        interview_id = request.session.get('interview_id')
        if interview_id:
            try:
                interview = Interview.objects.get(id=interview_id)
                interview.score = round(avg_score, 1)
                transcript = "\\n".join([f"Q: {r['question']}\\nA: {r['answer']}" for r in responses])
                overall_score, rec = generate_interview_recommendation(job_role, transcript)
                interview.ai_recommendation = rec
                interview.save()
            except Exception as e:
                print(f"Error saving interview: {e}")

    if not completed:
        next_index = request.session.get('current_question')
        if next_index >= len(request.session.get('questions', [])):
            next_q = question_generator.generate_next_question(
                job_role,
                resume_analysis,
                request.session.get('questions', []),
                last_answer=answer
            )
            request.session['questions'].append(next_q)
            
    request.session.modified = True
    
    return JsonResponse({
        'next_question': request.session['current_question'],
        'score': score,
        'feedback': ai_feedback,
        'detailed_analysis': detailed_analysis,
        'completed': completed
    })

@login_required
@require_http_methods(["POST"])
def update_physical_analysis(request):
    """Update physical analysis with single frame/audio segment"""
    if 'interview_id' not in request.session:
        return JsonResponse({'error': 'No active interview'}, status=400)
    
    try:
        current_q = request.session.get('current_question', 0)
        
        # Get single frame or audio segment
        video_frame = request.POST.get('video_frame')  # Base64 encoded
        audio_segment = request.POST.get('audio_segment')  # Base64 encoded
        
        if not video_frame and not audio_segment:
            return JsonResponse({'success': False, 'error': 'No data provided'})
        
        # Initialize storage if needed
        if 'physical_analysis' not in request.session:
            request.session['physical_analysis'] = {}
        
        if f'question_{current_q}' not in request.session['physical_analysis']:
            request.session['physical_analysis'][f'question_{current_q}'] = {
                'confidence': 0.0,
                'voice_quality': 0.0,
                'body_language': 0.0,
                'overall_physical_score': 0.0,
                'details': {
                    'confidence_scores': [],
                    'voice_scores': [],
                    'posture_scores': [],
                    'frame_count': 0,
                    'audio_segment_count': 0
                }
            }
        
        current_data = request.session['physical_analysis'][f'question_{current_q}']
        details = current_data['details']
        
        # Analyze video frame if provided
        if video_frame:
            frame_analysis = physical_analyzer.analyze_video_frame(video_frame)
            if frame_analysis:
                details['confidence_scores'].append(frame_analysis.get('confidence', 5.0))
                details['posture_scores'].append(frame_analysis.get('posture_score', 5.0))
                details['frame_count'] += 1
                
                # Recalculate averages
                if details['confidence_scores']:
                    current_data['confidence'] = round(
                        sum(details['confidence_scores']) / len(details['confidence_scores']), 2
                    )
                if details['posture_scores']:
                    current_data['body_language'] = round(
                        sum(details['posture_scores']) / len(details['posture_scores']), 2
                    )
        
        # Analyze audio segment if provided
        if audio_segment:
            audio_analysis = physical_analyzer.analyze_audio(audio_segment)
            if audio_analysis:
                details['voice_scores'].append(audio_analysis.get('voice_score', 5.0))
                details['audio_segment_count'] += 1
                
                # Recalculate average
                if details['voice_scores']:
                    current_data['voice_quality'] = round(
                        sum(details['voice_scores']) / len(details['voice_scores']), 2
                    )
        
        # Recalculate overall physical score
        current_data['overall_physical_score'] = round(
            (current_data['confidence'] * Config.CONFIDENCE_WEIGHT +
             current_data['voice_quality'] * Config.VOICE_WEIGHT +
             current_data['body_language'] * Config.BODY_LANGUAGE_WEIGHT), 2
        )
        
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'current_analysis': current_data,
            'summary': {
                'confidence': current_data['confidence'],
                'voice_quality': current_data['voice_quality'],
                'body_language': current_data['body_language'],
                'overall_physical_score': current_data['overall_physical_score']
            }
        })
        
    except Exception as e:
        print(f"Error updating physical analysis: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def interview_results(request):

    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
        
    interview_id = request.session.get('interview_id')
    if not interview_id:
        return redirect('dashboard')
        
    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return redirect('dashboard')
        
    responses = request.session.get('responses', [])
            
    return render(request, 'core/results.html', {
        'interview': interview,
        'responses': responses
    })

from .forms import ProfileForm

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user.profile)
    
    # Explicit context for template counts
    sub_count = request.user.submissions.count()
    int_count = request.user.interviews.count()
    
    return render(request, 'core/profile.html', {
        'form': form,
        'submission_count': sub_count,
        'interview_count': int_count
    })

@login_required
def upload_resume(request):
    """Upload and analyze student resume."""
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
    
    resume, created = Resume.objects.get_or_create(student=request.user)
    
    if request.method == 'POST':
        form = ResumeUploadForm(request.POST, request.FILES, instance=resume)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.student = request.user
            resume.analysis_status = 'PROCESSING'
            resume.save()
            
            # Extract text from resume
            resume_text = extract_resume_text(request.FILES['file'], request.FILES['file'].name)
            
            if resume_text:
                # Analyze resume with AI
                score, skills, suggestions = analyze_resume(resume_text)
                
                resume.score = score
                resume.skills_extracted = skills
                resume.suggestions = suggestions
                resume.ai_analysis = parse_ai_evaluation_response(suggestions)['suggestions']
                resume.analysis_status = 'COMPLETED'
                resume.save()
            else:
                resume.analysis_status = 'FAILED'
                resume.save()
            
            return redirect('resume_detail')
    else:
        form = ResumeUploadForm(instance=resume)
    
    return render(request, 'core/upload_resume.html', {'form': form, 'resume': resume})

@login_required
def resume_detail(request):
    """View resume analysis results."""
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
    
    try:
        resume = request.user.resume
    except Resume.DoesNotExist:
        return render(request, 'core/no_resume.html')
    
    return render(request, 'core/resume_detail.html', {'resume': resume})

@login_required
def start_proctoring(request):
    """Start a new proctoring session."""
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ProctoringSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.student = request.user
            session.status = 'IN_PROGRESS'
            session.save()
            
            # Generate interview questions
            questions = [
                "Describe a challenging project you worked on and how you solved it.",
                "What are your strongest technical skills and why?",
                "Tell us about a time you had to collaborate with difficult team members.",
                "How do you stay updated with new technologies and industry trends?",
                "What attracted you to this role and our company?"
            ]
            
            for i, question_text in enumerate(questions, 1):
                ProctoringQuestion.objects.create(
                    session=session,
                    question_text=question_text,
                    order=i
                )
            
            return redirect('proctoring_room', session_id=session.id)
    else:
        form = ProctoringSessionForm()
    
    return render(request, 'core/start_proctoring.html', {'form': form})

@login_required
def proctoring_room(request, session_id):
    """Main proctoring interview room."""
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
    
    try:
        session = ProctoringSession.objects.get(id=session_id, student=request.user)
    except ProctoringSession.DoesNotExist:
        return redirect('dashboard')
    
    # Get next unanswered question
    answered_questions = ProctoringResponse.objects.filter(
        question__session=session
    ).values_list('question_id', flat=True)
    
    current_question = ProctoringQuestion.objects.filter(
        session=session
    ).exclude(id__in=answered_questions).first()
    
    if not current_question:
        return redirect('proctoring_completed', session_id=session.id)
    
    if request.method == 'POST':
        form = ProctoringResponseForm(request.POST, request.FILES)
        if form.is_valid():
            response = form.save(commit=False)
            response.question = current_question
            response.save()
            
            # Evaluate response with AI
            score, evaluation = evaluate_proctoring_response(
                current_question.question_text,
                response.response_text,
                session.role_type
            )
            
            response.score = score
            response.ai_evaluation = evaluation
            response.save()
            
            return redirect('proctoring_room', session_id=session.id)
    else:
        form = ProctoringResponseForm()
    
    progress = {
        'answered': answered_questions.count(),
        'total': session.questions.count(),
        'current': current_question.order
    }
    
    return render(request, 'core/proctoring_room.html', {
        'session': session,
        'question': current_question,
        'form': form,
        'progress': progress
    })

@login_required
def proctoring_completed(request, session_id):
    """Proctoring session completion and analysis."""
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
    
    try:
        session = ProctoringSession.objects.get(id=session_id, student=request.user)
    except ProctoringSession.DoesNotExist:
        return redirect('dashboard')
    
    if session.status == 'IN_PROGRESS':
        # Get all responses
        responses = ProctoringResponse.objects.filter(question__session=session)
        
        # Build session transcript
        transcript = ""
        responses_data = []
        for resp in responses:
            transcript += f"Q: {resp.question.question_text}\nA: {resp.response_text}\n\n"
            responses_data.append({
                'question': resp.question.question_text,
                'score': resp.score or 0,
                'evaluation': resp.ai_evaluation
            })
        
        # Analyze overall session
        duration = (session.started_at and (
            (request.user.proctoring_sessions.filter(id=session_id).first().ended_at or 
             timezone.now()) - session.started_at
        ).total_seconds() / 60) or 0
        
        integrity_score, quality_score, issues, recommendations = analyze_proctoring_session(
            transcript,
            responses_data,
            int(duration)
        )
        
        session.transcript = transcript
        session.score = quality_score
        session.integrity_score = integrity_score
        session.flagged_issues = issues
        session.ai_analysis = recommendations
        session.status = 'COMPLETED'
        session.save()
    
    return render(request, 'core/proctoring_completed.html', {'session': session})

@login_required
def proctoring_history(request):
    """View all proctoring sessions for a student."""
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
    
    sessions = ProctoringSession.objects.filter(student=request.user).order_by('-started_at')
    
    return render(request, 'core/proctoring_history.html', {'sessions': sessions})

@login_required
def assignment_submissions(request, pk):
    assignment = Assignment.objects.get(pk=pk)
    # Security check: only the teacher who created the assignment can see submissions
    if assignment.teacher != request.user:
        return redirect('dashboard')
    
    # Get all students (for now, all registered students who are not teachers)
    # In a real app, this would be filtered by a specific class or enrollment
    students = User.objects.filter(profile__role='STUDENT')
    
    submitted_submissions = assignment.submissions.all().select_related('student')
    submitted_student_ids = submitted_submissions.values_list('student_id', flat=True)
    
    pending_students = students.exclude(id__in=submitted_student_ids)
    
    return render(request, 'core/view_submissions.html', {
        'assignment': assignment,
        'submissions': submitted_submissions,
        'pending_students': pending_students
    })
