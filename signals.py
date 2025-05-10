from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.utils import timezone

from userauths.models import User
from .models import Assignment, EnrolledCourse, Event, Message, Quiz, Notification, UserActivity

@receiver(post_save, sender=Assignment)
def create_assignment_notification(sender, instance, created, **kwargs):
    """Create notifications when a new assignment is created"""
    if created and instance.status == 'published':
        # Get all students enrolled in the course
        enrolled_students = EnrolledCourse.objects.filter(course=instance.course).values_list('user', flat=True)
        
        # Create a notification for each enrolled student
        for student_id in enrolled_students:
            student = User.objects.get(id=student_id)
            Notification.objects.create(
                user=student,
                sender=instance.teacher.user,
                assignment=instance,
                type="New Assignment",
                title=f"New Assignment: {instance.title}",
                content=f"A new assignment has been posted for {instance.course.title}.",
                url=f"/assignments/{instance.id}"
            )

@receiver(post_save, sender=Event)
def create_event_notification(sender, instance, created, **kwargs):
    """Create notifications for new events"""
    if created:
        # Determine recipients based on event settings
        recipients = []
        
        # Add users from specified groups
        if instance.groups.exists():
            for group in instance.groups.all():
                recipients.extend(list(User.objects.filter(groups=group)))
        
        # Add specifically selected users
        if instance.users.exists():
            recipients.extend(list(instance.users.all()))
        
        # If send_to_all is True, get all users
        if instance.send_to_all:
            recipients = User.objects.all()
            
        # Remove duplicates
        recipients = list(set(recipients))
        
        # Create notification for each recipient
        for recipient in recipients:
            Notification.objects.create(
                user=recipient,
                sender=instance.created_by,
                event=instance,
                type="New Event",
                title=f"New Event: {instance.name}",
                content=f"You've been invited to {instance.name} on {instance.date.strftime('%Y-%m-%d %H:%M')}.",
                url=f"/events/{instance.id}"
            )

@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """Create notifications for new messages"""
    if created:
        # Get all participants in the conversation except the sender
        recipients = instance.conversation.participants.exclude(id=instance.sender.id)
        
        # Create a notification for each recipient
        for recipient in recipients:
            Notification.objects.create(
                user=recipient,
                sender=instance.sender,
                message=instance,
                type="New Message",
                title=f"New Message from {instance.sender.get_full_name() or instance.sender.username}",
                content=f"{instance.content[:50]}..." if len(instance.content) > 50 else instance.content,
                url=f"/messages/{instance.conversation.id}"
            )

@receiver(post_save, sender=Quiz)
def create_quiz_notification(sender, instance, created, **kwargs):
    """Create notifications when a new quiz is published"""
    if created and instance.status == 'published':
        # Get all students enrolled in the course
        enrolled_students = EnrolledCourse.objects.filter(course=instance.course).values_list('user', flat=True)
        
        # Create a notification for each enrolled student
        for student_id in enrolled_students:
            student = User.objects.get(id=student_id)
            Notification.objects.create(
                user=student,
                sender=instance.teacher.user,
                quiz=instance,
                type="Quiz Available",
                title=f"New Quiz: {instance.title}",
                content=f"A new quiz is available for {instance.course.title}.",
                url=f"/quizzes/{instance.id}"
            )

@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """Track when a user logs in and save to UserActivity"""
    try:
        # Get the IP address if available
        ip = None
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
                
        # Create activity record for login
        UserActivity.objects.create(
            user=user,
            activity_type='login',
            user_type='user',
            details={
                "ip_address": ip,
                "user_agent": request.META.get('HTTP_USER_AGENT', 'Unknown') if request else 'Unknown',
                "timestamp": timezone.now().isoformat()
            }
        )
        
        print(f"Login tracked for user {user.id}")
    except Exception as e:
        # Log the error but don't prevent login
        print(f"Error tracking login: {str(e)}")