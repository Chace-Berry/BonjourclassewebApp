import os
from django.conf import settings
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.utils.timezone import now
from datetime import datetime, timedelta
from django.contrib import admin
from django.contrib.auth.models import User, Group

from userauths.models import User, Profile
from shortuuid.django_fields import ShortUUIDField
from moviepy.video.io.VideoFileClip import VideoFileClip
import math
from adminsortable2.admin import SortableAdminMixin
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.exceptions import ValidationError

LANGUAGE = (
    ("English", "English"),
    ("French", "French"),
)

LEVEL = (
    ("Beginner", "Beginner"),
    ("Intermediate", "Intermediate"),
    ("Advanced", "Advanced"),
)


TEACHER_STATUS = (
    ("Draft", "Draft"),
    ("Disabled", "Disabled"),
    ("Published", "Published"),
)

PAYMENT_STATUS = (
    ("Paid", "Paid"),
    ("Processing", "Processing"),
    ("Failed", "Failed"),
)


PLATFORM_STATUS = (
    ("Review", "Review"),
    ("Disabled", "Disabled"),
    ("Rejected", "Rejected"),
    ("Draft", "Draft"),
    ("Published", "Published"),
)

RATING = (
    (1, "1 Star"),
    (2, "2 Star"),
    (3, "3 Star"),
    (4, "4 Star"),
    (5, "5 Star"),
)

NOTI_TYPE = (
    ("New Order", "New Order"),
    ("New Review", "New Review"),
    ("New Course Question", "New Course Question"),
    ("Draft", "Draft"),
    ("Course Published", "Course Published"),
    ("Course Enrollment Completed", "Course Enrollment Completed"),
    ("New Assignment", "New Assignment"),  # Added
    ("Assignment Graded", "Assignment Graded"),  # Added
    ("New Event", "New Event"),  # Added
    ("New Message", "New Message"),  # Added
    ("Quiz Available", "Quiz Available"),  # Added
)

class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.FileField(upload_to="course-file", blank=True, null=True, default="default.jpg")
    full_name = models.CharField(max_length=100)
    bio = models.CharField(max_length=100, null=True, blank=True)
    facebook = models.URLField(null=True, blank=True)
    twitter = models.URLField(null=True, blank=True)
    linkedin = models.URLField(null=True, blank=True)
    about = models.TextField(null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.full_name
    
    def students(self):
        return CartOrderItem.objects.filter(teacher=self)
    
    def courses(self):
        return Course.objects.filter(teacher=self)
    
    def review(self):
        return Course.objects.filter(teacher=self).count()
    
class Category(models.Model):
    title = models.CharField(max_length=100)
    image = models.FileField(upload_to="course-file", default="category.jpg", null=True, blank=True)
    active = models.BooleanField(default=True)
    slug = models.SlugField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Category"
        ordering = ['title']

    def __str__(self):
        return self.title
    
    def course_count(self):
        return Course.objects.filter(category=self).count()
    
    def save(self, *args, **kwargs):
        if self.slug == "" or self.slug == None:
            self.slug = slugify(self.title) 
        super(Category, self).save(*args, **kwargs)
            
class Course(models.Model):
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    file = models.FileField(upload_to="course-file", blank=True, null=True)
    image = models.FileField(upload_to="course-file", blank=True, null=True)
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    language = models.CharField(choices=LANGUAGE, default="English", max_length=100)
    level = models.CharField(choices=LEVEL, default="Beginner", max_length=100)
    platform_status = models.CharField(choices=PLATFORM_STATUS, default="Published", max_length=100)
    teacher_course_status = models.CharField(choices=TEACHER_STATUS, default="Published", max_length=100)
    featured = models.BooleanField(default=False)
    course_id = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    slug = models.SlugField(unique=True, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)


    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.slug == "" or self.slug == None:
            self.slug = slugify(self.title) + str(self.pk)
        super(Course, self).save(*args, **kwargs)

    def students(self):
        return EnrolledCourse.objects.filter(course=self)
    
    def curriculum(self):
        return Variant.objects.filter(course=self)
    
    def lectures(self):
        return VariantItem.objects.filter(variant__course=self)
    
    def average_rating(self):
        average_rating = Review.objects.filter(course=self, active=True).aggregate(avg_rating=models.Avg('rating'))
        return average_rating['avg_rating']
    
    def rating_count(self):
        return Review.objects.filter(course=self, active=True).count()
    
    def reviews(self):
        return Review.objects.filter(course=self, active=True)
    
class Variant(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=1000)
    variant_id = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title
    
    def variant_items(self):
        return VariantItem.objects.filter(variant=self)
    
    def items(self):
        return VariantItem.objects.filter(variant=self)
    
    
class VariantItem(models.Model):
    variant = models.ForeignKey(Variant, on_delete=models.CASCADE, related_name="variant_items")
    title = models.CharField(max_length=1000)
    description = models.TextField(null=True, blank=True)
    file = models.FileField(upload_to="course-file", null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    content_duration = models.CharField(max_length=1000, null=True, blank=True)
    preview = models.BooleanField(default=False)
    variant_item_id = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.variant.title} - {self.title}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if self.file:
            clip = VideoFileClip(self.file.path)
            duration_seconds = clip.duration

            minutes, remainder = divmod(duration_seconds, 60)  

            minutes = math.floor(minutes)
            seconds = math.floor(remainder)

            duration_text = f"{minutes}m {seconds}s"
            self.content_duration = duration_text
            super().save(update_fields=['content_duration'])

class Question_Answer(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=1000, null=True, blank=True)
    qa_id = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"
    
    class Meta:
        ordering = ['-date']

    def messages(self):
        return Question_Answer_Message.objects.filter(question=self)
    
    def profile(self):
        return Profile.objects.get(user=self.user)
    
class Question_Answer_Message(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    question = models.ForeignKey(Question_Answer, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    qam_id = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    qa_id = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"
    
    class Meta:
        ordering = ['date']

    def profile(self):
        return Profile.objects.get(user=self.user)
    
class Cart(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    tax_fee = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    total = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    country = models.CharField(max_length=100, null=True, blank=True)
    cart_id = ShortUUIDField(length=6, max_length=20, alphabet="1234567890")
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.course.title
    
class CartOrder(models.Model):
    student = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    teachers = models.ManyToManyField(Teacher, blank=True)
    sub_total = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    tax_fee = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    total = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    initial_total = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    saved = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    payment_status = models.CharField(choices=PAYMENT_STATUS, default="Processing", max_length=100)
    full_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    coupons = models.ManyToManyField("api.Coupon", blank=True)
    yoco_payment_id = models.CharField(max_length=1000, null=True, blank=True)  
    oid = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    date = models.DateTimeField(default=timezone.now)


    class Meta:
        ordering = ['-date']
    
    def order_items(self):
        return CartOrderItem.objects.filter(order=self)
    
    def __str__(self):
        return self.oid
    
class CartOrderItem(models.Model):
    order = models.ForeignKey(CartOrder, on_delete=models.CASCADE, related_name="orderitem")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="order_item")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    tax_fee = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    total = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    initial_total = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    saved = models.DecimalField(max_digits=12, default=0.00, decimal_places=2)
    coupons = models.ManyToManyField("api.Coupon", blank=True)
    applied_coupon = models.BooleanField(default=False)
    oid = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-date']
    
    def order_id(self):
        return f"Order ID #{self.order.oid}"
    
    def payment_status(self):
        return f"{self.order.payment_status}"
    
    def __str__(self):
        return self.oid
class Certificate(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    certificate_id = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")  # Ensure this field exists
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.course.title
    
class CompletedLesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    variant_item = models.ForeignKey(VariantItem, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.course.title
    
class EnrolledCourse(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)  # Keeping this as-is
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    order_item = models.ForeignKey(CartOrderItem, on_delete=models.CASCADE)
    enrollment_id = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    # Add this new field with default=False
    added_via_subscription = models.BooleanField(default=False)
    # New field to reference the subscription
    subscription = models.ForeignKey("Subscription", on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.course.title
    
    def lectures(self):
        return VariantItem.objects.filter(variant__course=self.course)
    
    def completed_lesson(self):
        return CompletedLesson.objects.filter(course=self.course, user=self.user)
    
    def curriculum(self):
        return Variant.objects.filter(course=self.course)
    
    def note(self):
        return Note.objects.filter(course=self.course, user=self.user)
    
    def question_answer(self):
        return Question_Answer.objects.filter(course=self.course)
    
    def review(self):
        return Review.objects.filter(course=self.course, user=self.user).first()
    
class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=1000, null=True, blank=True)
    note = models.TextField()
    note_id = ShortUUIDField(unique=True, length=6, max_length=20, alphabet="1234567890")
    date = models.DateTimeField(default=timezone.now)   

    def __str__(self):
        return self.title
    
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    review = models.TextField()
    rating = models.IntegerField(choices=RATING, default=None)
    reply = models.CharField(null=True, blank=True, max_length=1000)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(default=timezone.now)   

    def __str__(self):
        return self.course.title
    
    def profile(self):
        return Profile.objects.get(user=self.user)
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey(CartOrder, on_delete=models.SET_NULL, null=True, blank=True)
    order_item = models.ForeignKey(CartOrderItem, on_delete=models.SET_NULL, null=True, blank=True)
    review = models.ForeignKey(Review, on_delete=models.SET_NULL, null=True, blank=True)
    assignment = models.ForeignKey('Assignment', on_delete=models.SET_NULL, null=True, blank=True)
    event = models.ForeignKey('Event', on_delete=models.SET_NULL, null=True, blank=True)
    quiz = models.ForeignKey('Quiz', on_delete=models.SET_NULL, null=True, blank=True)
    message = models.ForeignKey('Message', on_delete=models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=100, choices=NOTI_TYPE)
    title = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(blank=True, null=True)
    url = models.CharField(max_length=255, blank=True, null=True)  # URL to redirect to when clicking notification
    seen = models.BooleanField(default=False)
    date = models.DateTimeField(default=timezone.now)  

    def __str__(self):
        return f"{self.type} for {self.user.username if self.user else 'Unknown'}"
    
    class Meta:
        ordering = ['-date']

class Coupon(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    used_by = models.ManyToManyField(User, blank=True)
    code = models.CharField(max_length=50)
    discount = models.IntegerField(default=1)
    active = models.BooleanField(default=False)
    date = models.DateTimeField(default=timezone.now)   

    def __str__(self):
        return self.code
    
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    
    def __str__(self):
        return str(self.course.title)
    
class Country(models.Model):
    name = models.CharField(max_length=100)
    tax_rate = models.IntegerField(default=5)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Lecture(models.Model):
    course = models.ForeignKey(Course, related_name="lectures", on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    video = models.FileField(upload_to="lectures/", blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    # Admin configuration for Lecture
    class Admin(SortableAdminMixin):
        list_display = ("title", "course", "order")  # Display title, course, and order
        list_filter = ("course",)  # Filter by course
        search_fields = ("title", "course__title")  # Search by title or course title
        ordering = ("order",)  # Default ordering by the `order` field
        fields = ("title", "course", "video", "order")  # Fields to display in the form

class EmailSettings(models.Model):
    email_host = models.CharField(max_length=255, default="smtp.gmail.com")
    email_port = models.PositiveIntegerField(default=587)
    email_use_tls = models.BooleanField(default=True)
    email_host_user = models.EmailField()
    email_host_password = models.CharField(max_length=255)
    default_from_email = models.EmailField()

    def __str__(self):
        return f"Email Settings ({self.email_host_user})"

class OTP(models.Model):
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        # OTP is valid for 10 minutes
        return now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.email}: {self.otp}"

class Event(models.Model):
    PLATFORM_CHOICES = [
        ('zoom', 'Zoom'),
        ('ms_teams', 'Microsoft Teams'),
        ('webex', 'WebEx'),
        ('google_meet', 'Google Meet'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=255)  # Event name
    date = models.DateTimeField()  # Event date and time
    description = models.TextField(blank=True, null=True)  # Add this field
    platform = models.CharField(max_length=50, choices=PLATFORM_CHOICES, default='other') 
    invite_link = models.URLField(blank=True, null=True)  # Optional invite link
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_events')  # Event creator
    groups = models.ManyToManyField(Group, blank=True)  # Groups to share the event with
    users = models.ManyToManyField(User, blank=True, related_name='events')  # Specific users to share the event with
    send_to_all = models.BooleanField(default=False)  # Checkbox to send to all users

    def __str__(self):
        return self.name

def validate_file_size(value):
    max_size = 10 * 1024 * 1024  # 10 MB
    if value.size > max_size:
        raise ValidationError("File size exceeds 10 MB.")

from api.models import Course, Category

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="subscription")
    package = models.ForeignKey('SubscriptionPackage', on_delete=models.SET_NULL, null=True, blank=True)  # Reference to the subscription package
    active_courses = models.ManyToManyField(Course, blank=True)  # Specific courses included in the subscription
    include_all_courses = models.BooleanField(default=False)  # Checkbox to include all courses
    categories = models.ManyToManyField(Category, blank=True)  # Categories included in the subscription
    difficulties = models.JSONField(default=list, blank=True)  # Difficulty levels included (e.g., ["Beginner", "Intermediate"])
    features = models.JSONField(default=list, blank=True, null=True)  # <-- Change from TextField to JSONField
    is_active = models.BooleanField(default=True)  # Whether the subscription is active
    valid_until = models.DateTimeField(null=True, blank=True)  # Expiration date of the subscription
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Only set fields from package if package is present
        if self.package:
            self.include_all_courses = self.package.include_all_courses
            self.features = self.package.features
            self.difficulties = self.package.included_difficulties

        # Only call super().save() ONCE
        super().save(*args, **kwargs)

        # Now set M2M fields (after the instance is saved)
        if self.package:
            self.active_courses.set(self.package.active_courses.all())
            self.categories.set(self.package.included_categories.all())

    def __str__(self):
        return f"{self.user.username}'s Subscription"

from django.db import models
from api.models import Category, Course

class SubscriptionPackage(models.Model):
    name = models.CharField(max_length=255)  # Name of the subscription package
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price of the package
    active_courses = models.ManyToManyField(Course, blank=True)  # Specific courses included in the package
    include_all_courses = models.BooleanField(default=False)  # Checkbox to include all courses
    included_categories = models.ManyToManyField(Category, blank=True)  # Categories included in the package
    included_difficulties = models.JSONField(default=list, blank=True)  # Difficulty levels included (e.g., ["Beginner", "Intermediate"])
    features = models.JSONField(default=list, blank=True, null=True)  # <-- Change from TextField to JSONField
    description = models.TextField(blank=True, null=True)  # Description of the package
    duration = models.PositiveIntegerField(default=30)  # Duration of the package in days
    is_active = models.BooleanField(default=True)  # Whether the package is active

    def __str__(self):
        return self.name

class UserLibrary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    Course = models.ForeignKey(Course, on_delete=models.CASCADE)
    added_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

class CourseResource(models.Model):
    """
    Model for course resources/materials that can be downloaded by students
    """
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='resources')
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='resources', null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    file = models.FileField(upload_to='course_resources/')
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.CharField(max_length=50, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    downloa_d_url = models.URLField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Automatically determine file type and size if not provided
        if not self.file_type and self.file:
            file_name = self.file.name
            extension = file_name.split('.')[-1].lower() if '.' in file_name else ''
            self.file_type = extension
            
        if self.file and hasattr(self.file, 'size'):
            size_bytes = self.file.size
            # Always show size in MB for consistency
            self.file_size = f"{size_bytes/(1024*1024):.2f} MB"
                
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} - {self.course.title}"

# Add this after the CourseResource model, before the Assignment model
class VideoProgress(models.Model):
    """Track student progress through lecture videos"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, related_name='progress_records')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    current_time = models.FloatField(default=0)  # Current position in seconds
    duration = models.FloatField(default=0)      # Total duration in seconds
    percentage_complete = models.IntegerField(default=0)  # 0-100
    completed = models.BooleanField(default=False)
    last_watched = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'lecture']
        
    def __str__(self):
        return f"{self.user.username} - {self.lecture.title} - {self.percentage_complete}%"
    
    def save(self, *args, **kwargs):
        # Auto-calculate percentage if duration is available
        if self.duration > 0:
            self.percentage_complete = min(100, int((self.current_time / self.duration) * 100))
            # Mark as completed if watched at least 90%
            self.completed = self.percentage_complete >= 90
        super().save(*args, **kwargs)

class Assignment(models.Model):
    """Model for course assignments"""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)  # Make it optional
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='assignments')
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    points = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    has_test_mode = models.BooleanField(default=False, help_text="If enabled, this assignment requires secure test mode")
    time_limit_minutes = models.PositiveIntegerField(null=True, blank=True, help_text="Time limit in minutes for test mode")
    test_content = models.TextField(null=True, blank=True, help_text="Test questions or content")

    def __str__(self):
        return f"{self.title} - {self.course.title}"

class AssignmentFile(models.Model):
    """Files associated with assignments"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='assignment_files/')
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.CharField(max_length=50, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.assignment.title}"

    def save(self, *args, **kwargs):
        # Auto-populate file_type and file_size from the uploaded file
        if self.file and not self.name:
            self.name = os.path.basename(self.file.name)
        
        if self.file and not self.file_type:
            extension = os.path.splitext(self.file.name)[1].lower().replace('.', '')
            self.file_type = extension

        if self.file and not self.file_size and hasattr(self.file, 'size'):
            # Convert to readable format
            size_bytes = self.file.size
            if size_bytes < 1024:
                self.file_size = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                self.file_size = f"{size_bytes/1024:.2f} KB"
            else:
                self.file_size = f"{size_bytes/(1024*1024):.2f} MB"

        super().save(*args, **kwargs)

class AssignmentSubmission(models.Model):
    """Student submissions for assignments"""
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('graded', 'Graded'),
    )
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    submission_text = models.TextField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    grade = models.CharField(max_length=10, null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    secure_mode_used = models.BooleanField(default=False)
    fullscreen_warnings = models.IntegerField(default=0)
    tab_switch_warnings = models.IntegerField(default=0)
    answers = models.JSONField(default=dict, blank=True)  # <-- Added field for per-question answers
    
    def __str__(self):
        return f"{self.student.username} - {self.assignment.title}"
        
    class Meta:
        unique_together = ['assignment', 'student']  # One submission per student per assignment

class AssignmentSubmissionFile(models.Model):
    """Files attached to student submissions"""
    submission = models.ForeignKey(AssignmentSubmission, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='assignment_submissions/')
    name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.CharField(max_length=50, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.submission.student.username}"

    def save(self, *args, **kwargs):
        # Auto-populate file properties
        if self.file and not self.name:
            self.name = os.path.basename(self.file.name)
        
        if self.file and not self.file_type:
            extension = os.path.splitext(self.file.name)[1].lower().replace('.', '')
            self.file_type = extension

        if self.file and not self.file_size and hasattr(self.file, 'size'):
            size_bytes = self.file.size
            if size_bytes < 1024:
                self.file_size = f"{size_bytes} bytes"
            elif size_bytes < 1024 * 1024:
                self.file_size = f"{size_bytes/1024:.2f} KB"
            else:
                self.file_size = f"{size_bytes/(1024*1024):.2f} MB"

        super().save(*args, **kwargs)

class AssignmentTestLog(models.Model):
    """Logs for secure test mode activities"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='test_logs')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=50)  # start_test, end_test, fullscreen_exit, tab_switch, time_up
    details = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.student.username} - {self.action} - {self.timestamp}"

class Conversation(models.Model):
    """
    Represents a conversation between two or more users.
    """
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        participant_names = ', '.join([user.username for user in self.participants.all()])
        return f"Conversation: {participant_names}"
    
    def last_message(self):
        """Return the most recent message in this conversation"""
        return self.messages.order_by('-created_at').first()
    
    def unread_count(self, user):
        """Return the count of unread messages for a specific user"""
        return self.messages.exclude(read_by=user).count()
    
    class Meta:
        ordering = ['-updated_at']

class Message(models.Model):
    """
    Individual messages within a conversation
    """
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)
    attachment = models.FileField(upload_to='message_attachments/', null=True, blank=True)
    
    def __str__(self):
        return f"Message from {self.sender.username} at {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    def mark_as_read(self, user):
        """Mark this message as read by a specific user"""
        if user not in self.read_by.all():
            self.read_by.add(user)
            
    class Meta:
        ordering = ['created_at']
        
class Quiz(models.Model):
    """Model for course quizzes"""
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE,
        related_name='quizzes',
        null=True,
        blank=True,
        help_text="The course this quiz belongs to. Leave blank if assigning to a lecture."
    )
    lecture = models.ForeignKey(
        'Lecture',
        on_delete=models.CASCADE,
        related_name='quizzes',
        null=True,
        blank=True,
        help_text="The lecture this quiz belongs to. Leave blank if assigning to a course."
    )
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    points = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    def __str__(self):
        if self.course:
            return f"{self.title} - {self.course.title}"
        elif self.lecture:
            return f"{self.title} - {self.lecture.title}"
        return self.title

class QuizQuestion(models.Model):
    """Model for questions in quizzes"""
    QUESTION_TYPES = (
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('checkbox', 'Checkbox'),
        ('sentence_building', 'Sentence Building'),  
    )

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=50, choices=QUESTION_TYPES, default='multiple_choice')
    required = models.BooleanField(default=True)
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    options = models.JSONField(null=True, blank=True, help_text="Options for multiple choice questions")
    correct_feedback = models.TextField(null=True, blank=True)
    incorrect_feedback = models.TextField(null=True, blank=True)
    sample_answer = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.title} - {self.quiz.title}"

class UserActivity(models.Model):
    """Model for tracking user activity for analytics"""
    USER = 'user'
    TEACHER = 'teacher'
    ADMIN = 'admin'
    
    USER_TYPES = [
        (USER, 'Student'),
        (TEACHER, 'Teacher'),
        (ADMIN, 'Admin'),
    ]
    
    LOGIN = 'login'
    CONTENT_VIEW = 'content_view'
    SUBMISSION = 'submission'
    QUIZ_ATTEMPT = 'quiz_attempt'
    COMMENT = 'comment'
    DOWNLOAD = 'download'
    
    ACTIVITY_TYPES = [
        (LOGIN, 'Login'),
        (CONTENT_VIEW, 'Content View'),
        (SUBMISSION, 'Submission'),
        (QUIZ_ATTEMPT, 'Quiz Attempt'),
        (COMMENT, 'Comment'),
        (DOWNLOAD, 'Download'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    user_type = models.CharField(max_length=10, choices=USER_TYPES)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    course = models.ForeignKey('Course', on_delete=models.SET_NULL, null=True, blank=True)
    teacher = models.ForeignKey('Teacher', on_delete=models.SET_NULL, null=True, blank=True)
    content_id = models.CharField(max_length=50, blank=True, null=True)  # ID of related content
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)  # Additional details as needed
    
    class Meta:
        verbose_name_plural = "User Activities"
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

class StudentProgress(models.Model):
    """Track overall student progress through a course"""
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='student_progress')
    completed_lectures = models.JSONField(default=list, blank=True)  # List of lecture IDs completed
    completed_percentage = models.IntegerField(default=0)  # Overall course progress percentage
    last_activity = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)  # Whether the entire course is completed
    
    class Meta:
        unique_together = ['student', 'course']
        
    def __str__(self):
        return f"{self.student.username} - {self.course.title} - {self.completed_percentage}%"
    
    def update_progress(self):
        """Update the completion percentage based on completed lectures"""
        # Get total number of lectures in the course
        total_lectures = Lecture.objects.filter(course=self.course).count()
        
        if total_lectures:
            completed_count = len(self.completed_lectures)
            self.completed_percentage = int((completed_count / total_lectures) * 100)
            # Mark as fully completed if 100%
            self.completed = self.completed_percentage == 100
        else:
            self.completed_percentage = 0
            self.completed = False
            
        self.save(update_fields=['completed_percentage', 'completed'])

from django.db import models
from django.conf import settings

class UserAppearanceSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='appearance_settings')
    dark_mode = models.BooleanField(default=False)
    font_size = models.IntegerField(default=16)
    high_contrast = models.BooleanField(default=False)
    color_theme = models.CharField(max_length=20, default="default")
    density = models.CharField(max_length=20, default="comfortable")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Appearance Setting"
        verbose_name_plural = "User Appearance Settings"

    def __str__(self):
        return f"{self.user.username}'s appearance settings"

class AssignmentQuestion(models.Model):
    """Model for questions in assignments"""
    QUESTION_TYPES = (
        ('multiple_choice', 'Multiple Choice'),
        ('text', 'Text Answer'),
        ('file_upload', 'File Upload'),
    )
    
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='questions')
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    required = models.BooleanField(default=True)
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    options = models.JSONField(null=True, blank=True, help_text="Options for multiple choice questions")
    correct_feedback = models.TextField(null=True, blank=True)
    incorrect_feedback = models.TextField(null=True, blank=True)
    sample_answer = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.title} - {self.assignment.title}"

class QuestionOption(models.Model):
    """Options for multiple choice questions"""
    question = models.ForeignKey('AssignmentQuestion', on_delete=models.CASCADE, related_name='option_objects')
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        
    def __str__(self):
        return f"{self.text} - {self.question.title[:20]}"

class QuizSubmission(models.Model):
    """Model to track quiz submissions by students"""
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('graded', 'Graded'),
    )
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    answers = models.JSONField(default=dict, blank=True)  # Student's answers
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    score = models.PositiveIntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    correct_answers = models.PositiveIntegerField(default=0)  # Number of correct answers
    total_questions = models.PositiveIntegerField(default=0)  # Total number of questions
    auto_graded = models.BooleanField(default=False)  # Whether the quiz was automatically graded
    teacher_graded = models.BooleanField(default=False)  # Whether a teacher manually graded
    graded_at = models.DateTimeField(null=True, blank=True)
    notification_sent = models.BooleanField(default=False)  # Track if notification was sent
    
    class Meta:
        unique_together = ['quiz', 'student']  # One submission per student per quiz
        
    def __str__(self):
        return f"{self.student.username} - {self.quiz.title}"
        
    def get_score_percentage(self):
        """Return score as a percentage"""
        if self.score is None:
            return None
        return f"{self.score}%"

class CertificateFile(models.Model):
    certificate = models.OneToOneField(Certificate, on_delete=models.CASCADE, related_name='file')
    file = models.FileField(upload_to='certs/')
    image = models.ImageField(upload_to='certs/', null=True, blank=True)  # Add this line
    expires_at = models.DateTimeField()
    date_issued = models.DateTimeField(default=timezone.now)

    def is_expired(self):
        return timezone.now() > self.expires_at

class CertificateTemplate(models.Model):
    course = models.OneToOneField('Course', on_delete=models.CASCADE, related_name='certificate_template')
    template_json = models.JSONField()  # For Fabric.js/Konva.js schema
    background_image = models.ImageField(upload_to='certificate_templates/', null=True, blank=True)
    created_by = models.ForeignKey('Teacher', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class PendingSubscription(models.Model):
    """
    Tracks pending subscription checkouts waiting for payment confirmation
    """
    checkout_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    package = models.ForeignKey('SubscriptionPackage', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.package.name} - {self.checkout_id}"
    
    class Meta:
        verbose_name = "Pending Subscription"
        verbose_name_plural = "Pending Subscriptions"
        ordering = ['-created_at']



