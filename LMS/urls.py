"""
URL configuration for LMS project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from base.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/',RegisterUserView.as_view(),name = 'register'),
    path('login/',login, name = 'login'),
    path('course/',CourseView.as_view(),name = 'courseview'),
    path('coursedetail/<int:pk>/',CoursedetailView.as_view(),name = 'course'),
    path('enrollment/',EnrollmentView.as_view(),name='Enrollment'),
    path('assessment/', AssessmentListCreateView.as_view(), name='assessment-list-create'),
    path('submission/',SubmissionView.as_view(),name = 'Submission'),
    path('sponsor/',SponsorView.as_view(),name='Sponsor'),
    path('student-progress/',StudentProgressView.as_view(),name='studentprogress'),
    path('admin-dashboard/',admin_dashboard_api,name='admin_dashboard_api'),
    path('sponsor-dashboard/',sponsor_dashboard_api,name='sponsor_dashboard_api'),
    path('progress-report/',ProgressReportView.as_view(),name='progress_report')
]
