from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(User)
admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(Assessment)
admin.site.register(Submission)
admin.site.register(StudentProgress)
admin.site.register(Notification)
admin.site.register(Sponsor)