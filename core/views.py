from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, CreateView
from django.urls import reverse_lazy
from .forms import SignUpForm, AssignmentForm, SubmissionForm
from .models import Profile, Assignment, Submission, Interview
from django.contrib.auth.mixins import LoginRequiredMixin
from .ai_engine import evaluate_assignment, generate_interview_recommendation

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
            
            # Call Ollama for Evaluation
            score, feedback = evaluate_assignment(
                assignment.title, 
                assignment.description, 
                content
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
    return render(request, 'core/profile.html', {'form': form})
