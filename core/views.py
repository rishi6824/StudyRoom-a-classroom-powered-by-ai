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
def start_interview(request):
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
    return render(request, 'core/interview_start.html')

@login_required
def interview_room(request):
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
    
    # Mock question for now
    question = "Describe a challenging project you worked on and how you handled it."
    return render(request, 'core/interview_room.html', {'question': question})

@login_required
def interview_results(request):
    if request.user.profile.role != 'STUDENT':
        return redirect('dashboard')
    
    # Mock summary for now (in a real app, this would be gathered from session['responses'])
    session_summary = "Candidate answered questions about Python, databases, and problem solving with good clarity."
    
    # Call Ollama for Recommendation
    score, recommendation = generate_interview_recommendation(
        "Software Engineer",
        session_summary
    )
    
    # Create the interview result
    interview = Interview.objects.create(
        student=request.user,
        role_type="Software Engineer",
        score=score,
        ai_recommendation=recommendation
    )
    
    return render(request, 'core/interview_results.html', {'interview': interview})

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
