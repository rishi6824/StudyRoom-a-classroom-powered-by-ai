from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Profile, Assignment, Submission
from django.urls import reverse

class AdvancedFeaturesTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create Teacher
        self.teacher_user = User.objects.create_user(username='teacher', password='password123')
        self.teacher_profile = Profile.objects.get(user=self.teacher_user)
        self.teacher_profile.role = 'TEACHER'
        self.teacher_profile.save()
        
        # Create Student
        self.student_user = User.objects.create_user(username='student', password='password123')
        self.student_profile = Profile.objects.get(user=self.student_user)
        self.student_profile.role = 'STUDENT'
        self.student_profile.save()

    def test_teacher_dashboard_access(self):
        self.client.login(username='teacher', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/teacher_dashboard.html')

    def test_student_dashboard_access(self):
        self.client.login(username='student', password='password123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/student_dashboard.html')

    def test_create_assignment(self):
        self.client.login(username='teacher', password='password123')
        response = self.client.post(reverse('create_assignment'), {
            'title': 'Test Assignment',
            'description': 'Test Description',
        })
        self.assertEqual(response.status_code, 302) # Redirect to dashboard
        self.assertEqual(Assignment.objects.count(), 1)

    def test_interview_access(self):
        self.client.login(username='student', password='password123')
        response = self.client.get(reverse('start_interview'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('interview_room'))
        self.assertEqual(response.status_code, 200)
        
        response = self.client.get(reverse('interview_results'))
        self.assertEqual(response.status_code, 200)
    def test_profile_access(self):
        self.client.login(username='student', password='password123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/profile.html')
