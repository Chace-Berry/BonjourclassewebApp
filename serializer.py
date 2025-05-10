import os
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from api import models as api_models
from api.models import (
    EmailSettings, Category, Course, VideoProgress, Event, CourseResource, AssignmentFile,
    AssignmentSubmissionFile, Assignment, AssignmentQuestion, AssignmentSubmission, AssignmentTestLog,
    Conversation, EnrolledCourse, Quiz, Subscription, SubscriptionPackage, Message
)
from userauths.models import Profile, User

# JWT Token Serializer
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['full_name'] = user.full_name
        token['email'] = user.email
        token['username'] = user.username
        token['user_id'] = user.id
        try:
            token['teacher_id'] = user.teacher.id
        except:
            token['teacher_id'] = 0
        return token

# User and Profile
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    class Meta:
        model = User
        fields = ['full_name', 'email', 'password', 'password2']
    def validate(self, attr):
        if attr['password'] != attr['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attr
    def create(self, validated_data):
        user = User.objects.create(
            full_name=validated_data['full_name'],
            email=validated_data['email'],
        )
        email_username, _ = user.email.split("@")
        user.username = email_username
        user.set_password(validated_data['password'])
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = "__all__"

# Category & Course
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Category
        fields = ['id', 'title', 'image', 'slug', 'course_count']

class CourseMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title']

class CategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'title']

class CourseSerializer(serializers.ModelSerializer):
    teacher = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = api_models.Course
        fields = ["id", "category", "teacher", "file", "image", "title", "description", "price", "language", "level", "platform_status", "teacher_course_status", "featured", "course_id", "slug", "date"]

# Subscription & Packages
class SubscriptionPackageSerializer(serializers.ModelSerializer):
    active_courses = CourseMiniSerializer(many=True, read_only=True)
    included_categories = CategoryMiniSerializer(many=True, read_only=True)
    class Meta:
        model = SubscriptionPackage
        fields = '__all__'

class SubscriptionSerializer(serializers.ModelSerializer):
    package = SubscriptionPackageSerializer(read_only=True)
    class Meta:
        model = Subscription
        fields = '__all__'
        read_only_fields = ["created_at", "updated_at"]

# Course Resource
class CourseResourceSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    class Meta:
        model = CourseResource
        fields = ['id', 'title', 'file', 'file_url', 'file_type', 'file_size', 'course', 'lecture']
    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None
    def get_file_size(self, obj):
        if obj.file and hasattr(obj.file, 'path') and os.path.exists(obj.file.path):
            return os.path.getsize(obj.file.path)
        return 0

# Assignment & Related
class AssignmentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentQuestion
        fields = ['id', 'title', 'description', 'type', 'required', 'points', 'options', 'correct_feedback', 'incorrect_feedback', 'sample_answer']

class AssignmentSerializer(serializers.ModelSerializer):
    questions = AssignmentQuestionSerializer(many=True, read_only=True)
    course_name = serializers.SerializerMethodField()
    class Meta:
        model = Assignment
        fields = ['id', 'title', 'description', 'course', 'course_name', 'teacher', 'created_at', 'updated_at', 'due_date', 'points', 'status', 'has_test_mode', 'time_limit_minutes', 'test_content', 'questions']
    def get_course_name(self, obj):
        return obj.course.title if obj.course else None

class AssignmentListSerializer(serializers.ModelSerializer):
    course_name = serializers.SerializerMethodField()
    submissions_count = serializers.IntegerField(read_only=True)
    enrolled_students = serializers.IntegerField(read_only=True)
    class Meta:
        model = Assignment
        fields = ['id', 'title', 'description', 'course', 'course_name', 'created_at', 'updated_at', 'due_date', 'points', 'status', 'has_test_mode', 'submissions_count', 'enrolled_students']
        read_only_fields = ['created_at', 'updated_at', 'submissions_count', 'enrolled_students']
    def get_course_name(self, obj):
        return obj.course.title if obj.course else None

class AssignmentFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = AssignmentFile
        fields = ['id', 'name', 'file_type', 'file_size', 'file', 'url', 'uploaded_at']
        read_only_fields = ['file_type', 'file_size', 'uploaded_at']
    def get_url(self, obj):
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None

class AssignmentSubmissionFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    class Meta:
        model = AssignmentSubmissionFile
        fields = ['id', 'name', 'file_type', 'file_size', 'file', 'url', 'uploaded_at']
        read_only_fields = ['file_type', 'file_size', 'uploaded_at']
    def get_url(self, obj):
        request = self.context.get('request')
        if request and obj.file:
            return request.build_absolute_uri(obj.file.url)
        return None

class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    files = AssignmentSubmissionFileSerializer(many=True, read_only=True)
    student_name = serializers.SerializerMethodField()
    student_email = serializers.SerializerMethodField()
    class Meta:
        model = AssignmentSubmission
        fields = ['id', 'assignment', 'student', 'student_name', 'student_email', 'submission_text', 'submitted_at', 'status', 'grade', 'feedback', 'files', 'secure_mode_used', 'fullscreen_warnings', 'tab_switch_warnings', 'answers']
        read_only_fields = ['submitted_at', 'status', 'grade', 'feedback']
    def get_student_name(self, obj):
        return obj.student.profile.full_name if hasattr(obj.student, 'profile') else obj.student.username
    def get_student_email(self, obj):
        return obj.student.email

class AssignmentTestLogSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    class Meta:
        model = AssignmentTestLog
        fields = ['id', 'assignment', 'student', 'student_name', 'timestamp', 'action', 'details']
        read_only_fields = ['timestamp']
    def get_student_name(self, obj):
        return obj.student.profile.full_name if hasattr(obj.student, 'profile') else obj.student.username

# Quiz & Related
class QuizQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.QuizQuestion
        fields = ['id', 'title', 'description', 'type', 'required', 'points', 'options', 'correct_feedback', 'incorrect_feedback', 'sample_answer', 'order']

class QuizSerializer(serializers.ModelSerializer):
    questions = QuizQuestionSerializer(many=True, read_only=True)
    course_title = serializers.SerializerMethodField()
    lecture_title = serializers.SerializerMethodField()
    class Meta:
        model = api_models.Quiz
        fields = ['id', 'title', 'description', 'course', 'course_title', 'lecture', 'lecture_title', 'teacher', 'created_at', 'updated_at', 'points', 'status', 'questions']
    def get_course_title(self, obj):
        return obj.course.title if obj.course else None
    def get_lecture_title(self, obj):
        return obj.lecture.title if obj.lecture else None

class QuizSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.QuizSubmission
        fields = ['id', 'quiz', 'student', 'submitted_at', 'answers', 'status', 'score', 'feedback', 'correct_answers', 'total_questions', 'auto_graded', 'teacher_graded', 'graded_at', 'notification_sent']
        read_only_fields = ['submitted_at', 'graded_at']

# Messaging & Conversations
class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    is_sender = serializers.SerializerMethodField()
    class Meta:
        model = Message
        fields = ['id', 'sender', 'sender_name', 'content', 'created_at', 'is_sender', 'attachment']
    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username
    def get_is_sender(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.sender == request.user
        return False

class ConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    class Meta:
        model = Conversation
        fields = ['id', 'last_message', 'other_participant', 'unread_count', 'updated_at']
    def get_last_message(self, obj):
        last_msg = obj.last_message()
        if last_msg:
            return {
                'content': last_msg.content[:50] + '...' if len(last_msg.content) > 50 else last_msg.content,
                'created_at': last_msg.created_at,
                'is_read': self.context['request'].user in last_msg.read_by.all() if last_msg else True
            }
        return None
    def get_other_participant(self, obj):
        current_user = self.context['request'].user
        other_users = obj.participants.exclude(id=current_user.id)
        if other_users.count() == 1:
            user = other_users.first()
            return {
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'image': user.profile.image.url if hasattr(user, 'profile') and user.profile.image else None,
                'is_teacher': hasattr(user, 'teacher'),
            }
        elif other_users.count() > 1:
            return {
                'id': None,
                'name': f"Group ({other_users.count()} participants)",
                'image': None,
                'is_group': True
            }
        return None
    def get_unread_count(self, obj):
        current_user = self.context['request'].user
        return obj.messages.exclude(read_by=current_user).count()

# Certificate, Notes, Reviews, Notifications, Wishlist, Country, etc.
class CertificateSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    course_title = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    class Meta:
        model = api_models.Certificate
        fields = ['id', 'certificate_id', 'student', 'student_name', 'course', 'course_title', 'date', 'download_url']
    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username
    def get_course_title(self, obj):
        return obj.course.title
    def get_download_url(self, obj):
        return f"/api/v1/certificates/{obj.id}/download/"

class CompletedLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.CompletedLesson
        fields = '__all__'

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Note
        fields = '__all__'

class ReviewSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(many=False)
    class Meta:
        model = api_models.Review
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Notification
        fields = '__all__'

class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Coupon
        fields = '__all__'

class WishlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Wishlist
        fields = '__all__'

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Country
        fields = '__all__'

# Video Progress
class VideoProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoProgress
        fields = ['id', 'lecture', 'course', 'current_time', 'duration', 'percentage_complete', 'completed', 'last_watched']
        read_only_fields = ['percentage_complete', 'completed']

# User Appearance Settings
class UserAppearanceSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.UserAppearanceSettings
        fields = ['id', 'user', 'dark_mode', 'font_size', 'high_contrast', 'color_theme', 'density', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

# Email/OTP/Password
class EmailSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSettings
        fields = '__all__'

class OTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=False, max_length=6)
    password = serializers.CharField(required=False, write_only=True)

class PasswordUpdateSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

# Event
class EventSerializer(serializers.ModelSerializer):
    event_date = serializers.SerializerMethodField()
    event_time = serializers.SerializerMethodField()
    class Meta:
        model = Event
        fields = ['id', 'name', 'date', 'event_date', 'event_time', 'description', 'platform', 'invite_link', 'created_by', 'groups', 'users', 'send_to_all']
        read_only_fields = ['created_by']
    def get_event_date(self, obj):
        if obj.date:
            return obj.date.date()
        return None
    def get_event_time(self, obj):
        if obj.date:
            return obj.date.time()
        return None
    def create(self, validated_data):
        request = self.context.get('request')
        if 'date' not in validated_data and 'event_datetime' in validated_data:
            validated_data['date'] = validated_data.pop('event_datetime')
        if isinstance(validated_data.get('date'), str):
            from datetime import datetime
            date_str = validated_data['date']
            validated_data['date'] = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        elif 'user_id' in validated_data:
            from userauths.models import User
            try:
                user_id = validated_data.pop('user_id')
                validated_data['created_by'] = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
        return super().create(validated_data)

class LectureSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Lecture
        fields = '__all__'

class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Cart
        fields = '__all__'

class CartOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.CartOrder
        fields = '__all__'

class CartOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.CartOrderItem
        fields = '__all__'

class Question_AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Question_Answer
        fields = '__all__'

class Question_Answer_MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Question_Answer_Message
        fields = '__all__'

class EnrolledCourseSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)  # <-- NEST THE FULL COURSE OBJECT

    class Meta:
        model = api_models.EnrolledCourse
        fields = '__all__'

class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.Variant
        fields = '__all__'

class VariantItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_models.VariantItem
        fields = '__all__'

# For summary endpoints, if you return dicts, you may not need a serializer.
# But if you want to use one:
class StudentSummarySerializer(serializers.Serializer):
    total_courses = serializers.IntegerField()
    incomplete_lectures = serializers.IntegerField()
    pending_assignments = serializers.IntegerField()
    available_quizzes = serializers.IntegerField()
    daily_quiz_count = serializers.IntegerField()
    daily_assignment_count = serializers.IntegerField()
    daily_lecture_count = serializers.IntegerField()
    daily_other_count = serializers.IntegerField()
    monthly_quiz_activity = serializers.ListField(child=serializers.IntegerField())
    monthly_assignment_activity = serializers.ListField(child=serializers.IntegerField())
    monthly_lecture_activity = serializers.ListField(child=serializers.IntegerField())
    course_progress = serializers.ListField()
    months = serializers.ListField()

class TeacherSummarySerializer(serializers.Serializer):
    total_courses = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    monthly_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_students = serializers.IntegerField()