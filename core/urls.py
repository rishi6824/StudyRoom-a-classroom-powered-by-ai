from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('assignment/create/', views.create_assignment, name='create_assignment'),
    path('assignment/<int:pk>/', views.view_assignment, name='view_assignment'),
    path('assignment/<int:pk>/submit/', views.submit_assignment, name='submit_assignment'),
    path('interview/start/', views.start_interview, name='start_interview'),
    path('interview/room/', views.interview_room, name='interview_room'),
    path('interview/results/', views.interview_results, name='interview_results'),
    path('profile/', views.profile_view, name='profile'),
]
