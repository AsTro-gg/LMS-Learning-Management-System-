from rest_framework.generics import CreateAPIView,ListAPIView,GenericAPIView,ListCreateAPIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializers import *
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework import filters
from django.http import JsonResponse
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, Sum, Q,Avg
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.core.mail import EmailMessage


class RegisterUserView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            group, _ = Group.objects.get_or_create(name=user.role.capitalize())  
            user.groups.add(group)
            
            return Response(
                {"message": "User registered successfully!", "user": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


@api_view(['POST'])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(username=email, password=password) # as we set email as our primary field in place of username we can now do this easily without extra steps
    if user is None:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    token, _ = Token.objects.get_or_create(user=user) # we need 2 fields as get or create returns boolean also
    return Response({'token': token.key, 'role': user.role}, status=status.HTTP_200_OK) #again being neat with it

class CourseView(GenericAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseViewSerialiser
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'difficulty', 'instructor__username']

    def get(self, request):
        queryset = self.get_queryset()
        queryset = self.filter_queryset(queryset)
        paginated_data = self.paginate_queryset(queryset)

        # Check user role and filter courses accordingly
        if request.user.role == 'instructor':
            course = queryset.filter(instructor=request.user)
        else:
            course = queryset  # Others can view all courses

        # Serialize and paginate the course data
        serializer = self.get_serializer(paginated_data, many=True)
        response = self.get_paginated_response(serializer.data) 
        return Response(response.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Only instructors can add courses
        if request.user.role == 'instructor':
            serializer.save(instructor=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # Unauthorized access response
        return Response(
            {"detail": "Only instructors can add a course."},  # Improved error message
            status=status.HTTP_401_UNAUTHORIZED
        )

    
class CoursedetailView(GenericAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseViewSerialiser
    permission_classes = [IsAuthenticated]

    def get(self,request,pk):
            try:
                data =self.get_object()
            except Course.DoesNotExist:
                return Response({'Doesnot Exist'},status=status.HTTP_404_NOT_FOUND)

            
            if request.user.role == 'instructor' and data.instructor != request.user:
                return Response({'Forbidden':'This course is not yours'},status=status.HTTP_403_FORBIDDEN)
            else:
                serialiser = self.get_serializer(data)
                return Response(serialiser.data,status=status.HTTP_200_OK)

class EnrollmentView(GenericAPIView): # only student can enroll, if already enrolled no duplication
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerialiser
    permission_classes = [IsAuthenticated]

    def get(self,request):
        if request.user.role == 'student':
            enrolled_in = Enrollment.objects.filter(student_id = request.user)
            serialiser = self.get_serializer(enrolled_in,many = True)
            return Response(serialiser.data,status=status.HTTP_200_OK)
        elif request.user.role == 'instructor':
            course_enrollment= Enrollment.objects.filter(instructor_id = request.user)
            serialiser = self.get_serializer(course_enrollment,many = True)
            return Response(serialiser.data,status=status.HTTP_200_OK)
        else:
            return Response({'Forbidden':'You dont have access'},status=status.HTTP_403_FORBIDDEN)

    def post(self,request):
        if request.user.role == 'student':
            user = request.user
            course_id = request.data['course']
            if Enrollment.objects.filter(student=user ,course=course_id).exists():
                return Response({'enrolled':'You are already enrolled'},status=status.HTTP_400_BAD_REQUEST)
            serialiser = EnrollmentSerialiser(data = request.data,context = {'request':request})
            if serialiser.is_valid():
                serialiser.save()
                return Response(serialiser.data,status=status.HTTP_201_CREATED)
            return Response(serialiser.errors,status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'Forbidden':'You are not allowed to enroll in courses'},status=status.HTTP_403_FORBIDDEN)

class AssessmentListCreateView(GenericAPIView):
    queryset = Assessment.objects.all()
    serializer_class = AssessmentSerializer
    permission_classes = [IsAuthenticated]

    def get(self,request):
        user = self.request.user
        
        if user.role == 'student':
            student_enrollment = Enrollment.objects.filter(student = request.user).values_list('course_id', flat=True) #sending whole list from the database
            assessment_objs = Assessment.objects.filter(course_id__in= student_enrollment) #__in field helps us look one by one in a field it is called as a look up field 
            serialiser = self.get_serializer(assessment_objs,many = True)
            return Response(serialiser.data,status=status.HTTP_200_OK)

        elif user.role == 'instructor':
            instructor_course = Course.objects.filter(instructor = request.user).values_list('id',flat=True)
            created_courses = Assessment.objects.filter(course_id__in = instructor_course)
            serialiser = self.get_serializer(created_courses,many = True)
            return Response(serialiser.data,status=status.HTTP_200_OK)

        else:
            return Response({'Forbidden':'Only for students and instructors'},status=status.HTTP_403_FORBIDDEN)
    
    def post(self, request):
        course_id = request.data.get('course')
        if not course_id:
            return Response({'detail': 'Course ID is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try: 
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            return Response({'detail': 'The course you entered does not exist.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.role == 'instructor' and course.instructor == request.user:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "You are not authorized to create an assessment for this course."},status=status.HTTP_403_FORBIDDEN)

class SubmissionView(GenericAPIView):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerialiser
    permission_classes = [IsAuthenticated]
    
    
    def get(self, request):
        user = request.user

        if user.role == 'instructor':
            submissions = Submission.objects.filter(assessment__created_by=user) # using django orm lookup field to search for assessment created by user
            serializer = self.get_serializer(submissions, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({'Forbidden': 'Only instructors can view the submissions'},status=status.HTTP_403_FORBIDDEN)

    def post(self,request):
        user = request.user
        assessment_id = request.data.get('assessment')
        submission_obj = self.get_queryset()
        submitted_by = request.data.get('submitted_by')

# i wanted to check if the assessment is of the correct course and the course is enrolled by the student but it took way to many steps than i previously thought
        if user.role == 'student':
            try:
                assessment = Assessment.objects.get(id=assessment_id)
            except Assessment.DoesNotExist:
                return Response({'error': 'Assessment not found'}, status=status.HTTP_404_NOT_FOUND)
            
            is_enrolled = Enrollment.objects.filter(course=assessment.course, student=user).exists()
            if not is_enrolled:
                return Response({'Invalid':'You are not a part of this course'},status=status.HTTP_403_FORBIDDEN)
            serialisers = self.get_serializer(data = request.data)
            if serialisers.is_valid():
                serialisers.save()
                return Response(serialisers.data,status=status.HTTP_201_CREATED)
            return Response(serialisers.errors,status=status.HTTP_400_BAD_REQUEST)
           
        return Response({'Forbidden':'Only students can submit courses'},status=status.HTTP_403_FORBIDDEN)

class SponsorView(GenericAPIView):
    queryset = Sponsor.objects.all()
    serializer_class = SponsorSerialiser
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'sponsor':
            return Response({'Error': 'Only sponsors can access this page'}, status=403)

        # Filter sponsor data for current sponsor
        sponsor_filter = self.get_queryset().filter(sponsor=user)

        # Apply pagination
        paginated_queryset = self.paginate_queryset(sponsor_filter)
        serializer = self.get_serializer(paginated_queryset, many=True)

        # Return paginated response
        return self.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role != 'sponsor':
            return Response({'Forbidden': 'You are not a sponsor'}, status=403)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)

    
class StudentProgressView(GenericAPIView):
    queryset = StudentProgress.objects.all()
    serializer_class = StudentProgressSerialiser
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != 'instructor':
            return Response({'Forbidden': 'Only instructors can access this'}, status=403)

        # Filter progress related to the instructor
        queryset = self.get_queryset().filter(instructor=user)

        # Apply pagination
        paginated_queryset = self.paginate_queryset(queryset)
        serializer = self.get_serializer(paginated_queryset, many=True)

        # Return paginated response
        return self.get_paginated_response(serializer.data)

    def post(self, request):
        assessment = request.data.get('assessment')
        student = request.data.get('student')
        user = request.user

        if user.role != 'instructor':
            return Response({'Forbidden': 'Only instructors can access this'}, status=403)

        # Check if the assessment is created by the instructor
        validity_check = Assessment.objects.filter(created_by=user, id=assessment).exists()
        if not validity_check:
            return Response({'Forbidden': 'This is not your course'}, status=403)

        # Prevent duplicate progress entry
        if StudentProgress.objects.filter(assessment=assessment, student=student).exists():
            return Response({'Already recorded': 'This student has their progress already recorded'}, status=400)

        # Validate and save
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)


    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_dashboard_api(request):
    if request.user.role != 'admin':
        return Response({'Error':'You are not an admin user'},status=403)
    
    total_user = User.objects.count()
    active_course = Course.objects.filter(is_active=True).count()
    total_enrollment = Enrollment.objects.count()

    data = {
        "total_users":total_user,
        "active_courses":active_course,
        "total_enrollment":total_enrollment
    }
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sponsor_dashboard_api(request):
    if request.user.role != 'sponsor':
        return Response({"error": "Permission denied"}, status=403)

    # Get query params
    filter_progress = request.GET.get('progress_percentage')
    filter_courses = request.GET.get('courses_enrolled')

    sponsorships = Sponsor.objects.filter(sponsor=request.user).select_related('student')
    student_progress = []

    for sponsorship in sponsorships:
        student = sponsorship.student
        courses = Course.objects.filter(enrollment__student=student).distinct()

        total_assessments = Assessment.objects.filter(course__in=courses).count()
        completed_assessments = StudentProgress.objects.filter(
            student=student,
            is_completed=True
        ).count()

        progress_percentage = 0
        if total_assessments > 0:
            progress_percentage = round((completed_assessments / total_assessments) * 100, 2)

        courses_enrolled = courses.count()

        #using loop to filter because sponsor will have ease in using dashboard.
        if filter_progress and progress_percentage != float(filter_progress):
            continue
        if filter_courses and courses_enrolled != int(filter_courses):
            continue

        student_progress.append({
            "student_id": student.id,
            "student_name": student.username,
            "total_assessments": total_assessments,
            "completed_assessments": completed_assessments,
            "progress_percentage": progress_percentage,
            "total_funds": float(sponsorship.amount),
            "course_enrolled": courses_enrolled,
        })

    return Response({
        "sponsored_students": student_progress
    })

class NotificationView(GenericAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerialiser

    def get(self):
        #only notifications for currently logged in user
        return Notification.objects.filter(User=self.request.user)

class ProgressReportView(GenericAPIView):
    serializer_class = ProgressReportSerialiser

    def post(self, request):
        user = request.user
        if user.role != 'instructor':
            return Response({'Forbidden': 'You are not allowed'}, status=403)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            student = serializer.validated_data['student'] 
            report_file = serializer.validated_data['report_file']

            # Get sponsor instance
            sponsor_instance = Sponsor.objects.filter(student=student).first()
            sponsor = sponsor_instance.sponsor if sponsor_instance else None

            if not sponsor:
                return Response({"error": "No sponsor found for this student."}, status=400)

            # Save the report file
            sponsor_instance.report_file = report_file
            sponsor_instance.save()

            # Send email to sponsor
            subject = f"Progress Report Uploaded for {student.username}"
            email_sponsor = EmailMessage(
                subject,
                f"A new progress report for {student.username} has been uploaded.",
                settings.DEFAULT_FROM_EMAIL,
                [sponsor.email]
            )
            email_sponsor.attach(report_file.name, report_file.read(), report_file.content_type)
            email_sponsor.send()

            return Response({'message': 'Report uploaded. Email sent to sponsor.'}, status=201)

        return Response(serializer.errors, status=400)

class NotificationView(GenericAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerialiser
    permission_classes = [IsAuthenticated]

    def get(self,request):
        model = self.get_queryset()
        serializers = self.get_serializer(model,many = True)
        return Response(serializers.data,status=200)