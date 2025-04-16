from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('instructor', 'Instructor'),
        ('student', 'Student'),
        ('sponsor', 'Sponsor')
    ]
    
    email = models.EmailField(unique=True)
    image = models.FileField(upload_to='profile_images/', null=True, blank=True)
    contacts = models.CharField(max_length=300, null=True, blank=True)
    role = models.CharField(max_length=100, choices=ROLE_CHOICES, default='student')

    USERNAME_FIELD = 'email'  # blackbox ai suggestion , finds out this helps us create email as primary login field 
    REQUIRED_FIELDS = ['username'] #username still needed but it is not primary login field

    def __str__(self):
        return f"{self.username}({self.role})" # being neat

class Course(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy','Easy'),
        ('intermediate','Intermediate'),
        ('hard','Hard')
    ]
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=300)
    difficulty = models.CharField(max_length=30,choices=DIFFICULTY_CHOICES) #no default as it makes the input field not required
    instructor = models.ForeignKey(User,on_delete=models.CASCADE,related_name='course')
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('enrolled','Enrolled'),
        ('not_enrolled','Not Enrolled')
    ]
    course = models.ForeignKey(Course,on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE,related_name="student")
    instructor = models.ForeignKey(User,on_delete=models.CASCADE, related_name="instructor")
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='not_enrolled')
    enrolled_at = models.DateField(auto_now_add=True)
    progress = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.student}'s enrollment for {self.course}"
    
class Assessment(models.Model):
    DIFFICULTY_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]

    file = models.FileField()
    course = models.ForeignKey('Course',on_delete=models.CASCADE,related_name='assessments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    due_date = models.DateField()
    max_score = models.PositiveIntegerField()
    difficulty_level = models.CharField(max_length=20,choices=DIFFICULTY_CHOICES,default='Beginner')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.title} - {self.course.title}"
    
class Submission(models.Model):
    assessment = models.ForeignKey(Assessment,on_delete=models.CASCADE)
    add_file = models.FileField()
    submitted_by = models.ForeignKey(User,on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.assessment}'s submission"


class Sponsor(models.Model):
    sponsor = models.ForeignKey(User,on_delete=models.CASCADE,limit_choices_to={'role':'sponsor'},related_name='sponsor_sponsor')
    student = models.ForeignKey(User,on_delete=models.CASCADE,limit_choices_to={'role':'student'},related_name='student_student')
    amount = models.BigIntegerField()
    sponsorship_date = models.DateField(auto_now_add=True)
    transaction_id = models.CharField(max_length=200)
    #progress report related fields
    report_file = models.FileField(null=True, blank=True)

    def __str__(self):
        return f"{self.student} sponsored by {self.sponsor}"
    


class StudentProgress(models.Model):
    student = models.ForeignKey(User,on_delete=models.CASCADE,related_name='progress')
    assessment = models.ForeignKey(Assessment,on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    marks_obtained = models.IntegerField(default=0)
    instructor = models.ForeignKey(User,on_delete=models.CASCADE,related_name='instructor_name')

    def __str__(self):
        return f"{self.student}'s {self.assessment} progress"
    

class Notification(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    message = models.CharField(max_length=300)
    time = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    link = models.URLField(blank=True)

    def __str__(self):
        return f"{self.user}: {self.message[:50]}" #slicing first 50 letters for clean look jammai aayo vane wild dekhinxa