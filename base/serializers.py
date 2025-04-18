from .models import *
from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings

class UserRegistrationSerializer(serializers.ModelSerializer):
    #customising serialiser so that we dont manually do anything in views because it is very error sensitive(T-T)
    #write only = True ensures password isnt visible
    password = serializers.CharField(write_only=True, min_length=6) 

    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'password', 'role']

    def create(self, validated_data): # we create a function which creates data when validated data is sent as .save()
        #if we write logic in view we have to manually hash password but after we use .create_user this function automatically stores according to the fields

        user = User.objects.create_user(
            # we pull individual data and store them as predefined DRF function stores.
            email=validated_data['email'],
            username=validated_data['username'],
            password=validated_data['password'],
            role =validated_data.get('role', 'student')
            # we write role as student because it is default and if no role is passed in request it automatically defaults to student. if user is other role it will change.
        )

        

        return user



class CourseViewSerialiser(serializers.ModelSerializer):
    instructor = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'difficulty', 'instructor', 'start_date', 'end_date']

    def create(self, validated_data):
        course = Course.objects.create(**validated_data)

        # Get all students
        students = User.objects.filter(role='student')
        student_emails = [student.email for student in students]

        print("Student Emails:", student_emails)  #debugging

        if student_emails:
            send_mail(
                subject=f"New Course: {course.title}",
                message=f"Check out this course by {course.instructor} starting on {course.start_date}. Enhance your skills with '{course.title}'!",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=student_emails,
                fail_silently=False
            )

        return course

class EnrollmentSerialiser(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    course_name = serializers.SerializerMethodField() # this method is useful for getting indirect values from foreign key models
    instructor_name = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields =['status','enrolled_at','course','student','student_name','course_name','instructor_name','instructor']
        read_only_fields = ['enrolled_at','student','instructor']

    def get_student_name(self,obj):
        return obj.student.username # the obj gets the user model and serialises the username field so we can get the username also
    def get_course_name(self,obj):
        return obj.course.title
    def get_instructor_name(self,obj):
        return obj.course.instructor.username
    
    def create(self,validated_data):
        user = self.context['request'].user #the ['request'] is the request we'd get in views 
        validated_data['student'] =  user

        course = validated_data.get('course')
        if course:
            validated_data['instructor'] = course.instructor

        enrollment = Enrollment.objects.create(**validated_data)

        if User.objects.filter(username = user).exists:
            Notification.objects.create(user = user,message = f"New Enrollment by {enrollment.student} for course {enrollment.course}")
        
        return enrollment


class AssessmentSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    class Meta:
        model = Assessment
        fields = ['course','title','description','due_date','max_score','difficulty_level','created_at','created_by']
        read_only_fields = ['created_at','created_by']
    
    def get_created_by(self,obj):
        return obj.created_by.username
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        # saving the validated data instantly because we need it for notification
        assessment = Assessment.objects.create(**validated_data)
        # creating notification in the serialiser itself because its easier
        students = User.objects.filter(role = 'student')
        for student in students:
            Notification.objects.create(user = student,message = f"New assessment added {assessment.title} deadiline till-{assessment.due_date}")
        
        return assessment

    def validate_course(self, value):
        # Check if course belongs to requesting instructor
        if self.context['request'].user.role == 'instructor':
            if self.context['request'].user != value.instructor:
                raise serializers.ValidationError("You are not allowed")
        return value
    
class SubmissionSerialiser(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class Meta:
        model = Submission
        fields = ['assessment','add_file','submitted_by','submitted_at','name']
        read_only_fields = ['submitted_by','submitted_at']

    def get_name(self,obj):
        return obj.submitted_by.username

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['submitted_by'] = user
        
        submission = Submission.objects.create(**validated_data)

        if User.objects.filter(username = user).exists():        
            Notification.objects.create(user =user,message = f"New submission by {submission.submitted_by.username}")
        
        return submission
    
class SponsorSerialiser(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    sponsor_name = serializers.SerializerMethodField()
    class Meta:
        model = Sponsor
        fields = ['sponsor','student','amount','sponsorship_date','transaction_id','student_name','sponsor_name']
        read_only_fields = ['sponsor','sponsorship_date','student_name','sponsor_name']

    def get_student_name(self,obj):
        return obj.student.username
    def get_sponsor_name(self,obj):
        return obj.sponsor.username

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['sponsor']= user
        return super().create(validated_data)

class StudentProgressSerialiser(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentProgress
        fields = ['student', 'assessment', 'is_completed', 'marks_obtained', 'student_name']
        read_only_fields = ['student_name']

    def get_student_name(self, obj):
        return obj.student.username

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['instructor'] = user

        assessment_result = StudentProgress.objects.create(**validated_data)

        student = assessment_result.student

        send_mail(
            subject=f"Assessment Report: {assessment_result.assessment}",
            message=(
                f"Hi {student.username},\n\n"
                f"You've completed the assessment: {assessment_result.assessment}.\n"
                f"Marks Obtained: {assessment_result.marks_obtained}\n\n"
                f"Great job!"
            ),
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[student.email]
        )
        return assessment_result

class NotificationSerialiser(serializers.ModelSerializer):
    class Meta:
        # have written the logic to create notification whilst the action happens in other serialiser so nothing here
        model = Notification
        fields = '__all__'

class ProgressReportSerialiser(serializers.ModelSerializer):
    class Meta:
        model = Sponsor
        fields =['student','report_file']

