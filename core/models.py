from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    ROLE_CHOICES = (
        ('STUDENT', 'Student'),
        ('TEACHER', 'Teacher'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STUDENT')
    image = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Resume(models.Model):
    ANALYSIS_STATUS = (
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )
    
    student = models.OneToOneField(User, on_delete=models.CASCADE, related_name='resume')
    file = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    analysis_status = models.CharField(max_length=20, choices=ANALYSIS_STATUS, default='PENDING')
    ai_analysis = models.TextField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    skills_extracted = models.JSONField(null=True, blank=True, help_text="Extracted skills from resume")
    suggestions = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - Resume"

class ProctoringSession(models.Model):
    SESSION_STATUS = (
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('FLAGGED', 'Flagged for Review'),
    )
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proctoring_sessions')
    role_type = models.CharField(max_length=100)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=SESSION_STATUS, default='IN_PROGRESS')
    video_file = models.FileField(upload_to='proctoring_videos/', null=True, blank=True)
    audio_file = models.FileField(upload_to='proctoring_audio/', null=True, blank=True)
    transcript = models.TextField(null=True, blank=True)
    ai_analysis = models.TextField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    integrity_score = models.FloatField(null=True, blank=True, help_text="Score from 0-10 indicating exam integrity")
    flagged_issues = models.JSONField(null=True, blank=True, help_text="List of potential issues detected")

    def __str__(self):
        return f"{self.student.username} - {self.role_type} Proctoring"

class ProctoringQuestion(models.Model):
    session = models.ForeignKey(ProctoringSession, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:50]}"

class ProctoringResponse(models.Model):
    question = models.ForeignKey(ProctoringQuestion, on_delete=models.CASCADE, related_name='responses')
    response_text = models.TextField()
    response_audio = models.FileField(upload_to='responses_audio/', null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    ai_evaluation = models.TextField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response to Q{self.question.order}"

class Interview(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interviews')
    role_type = models.CharField(max_length=100)
    score = models.FloatField(null=True, blank=True)
    ai_recommendation = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.role_type}"

class Assignment(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_assignments')
    title = models.CharField(max_length=255)
    description = models.TextField()
    rubric = models.TextField(null=True, blank=True, help_text="Criteria for marking this assignment")
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    file = models.FileField(upload_to='submissions/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    score = models.FloatField(null=True, blank=True)
    ai_feedback = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"
