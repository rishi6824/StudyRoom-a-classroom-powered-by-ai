from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile, Assignment, Submission, Resume, ProctoringSession, ProctoringQuestion, ProctoringResponse

class SignUpForm(UserCreationForm):
    # ... existing ...
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, required=True)

    class Meta:
        model = User
        fields = ("username", "email")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            Profile.objects.update_or_create(user=user, defaults={'role': self.cleaned_data['role']})
        return user

class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ['title', 'description', 'rubric', 'due_date']
        widgets = {
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['file']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']

class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'accept': '.pdf,.docx,.doc,.txt',
                'class': 'form-control'
            })
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            allowed_extensions = ['pdf', 'docx', 'doc', 'txt']
            file_ext = file.name.split('.')[-1].lower()
            if file_ext not in allowed_extensions:
                raise forms.ValidationError("Only PDF, DOCX, DOC, and TXT files are allowed.")
            if file.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError("File size should not exceed 5MB.")
        return file

class ProctoringSessionForm(forms.ModelForm):
    class Meta:
        model = ProctoringSession
        fields = ['role_type']
        widgets = {
            'role_type': forms.TextInput(attrs={
                'placeholder': 'e.g., Software Engineer, Data Scientist',
                'class': 'form-control'
            })
        }

class ProctoringResponseForm(forms.ModelForm):
    class Meta:
        model = ProctoringResponse
        fields = ['response_text', 'response_audio', 'duration_seconds']
        widgets = {
            'response_text': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Type your response here...',
                'class': 'form-control'
            }),
            'response_audio': forms.FileInput(attrs={
                'accept': 'audio/*',
                'class': 'form-control'
            }),
            'duration_seconds': forms.NumberInput(attrs={
                'min': '0',
                'class': 'form-control'
            })
        }

