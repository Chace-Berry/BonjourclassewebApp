import logging
import ssl
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.timezone import now
from django.shortcuts import get_object_or_404
from weasyprint import HTML, CSS, default_url_fetcher
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from pdf2image import convert_from_path,convert_from_bytes
from django.templatetags.static import static
import os
from io import BytesIO
from html2image import Html2Image
from django.template import loader as django_loader
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import timedelta
from xhtml2pdf import pisa

class UploadCertificateBackground(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        file = request.FILES['file']
        file_name = default_storage.save(f"certificates/backgrounds/{file.name}", file)
        file_url = default_storage.url(file_name)

        # Get positioning data from the request
        name_position = request.data.get('name_position', {'x': 100, 'y': 500})
        date_position = request.data.get('date_position', {'x': 100, 'y': 450})
        logo_position = request.data.get('logo_position', {'x': 50, 'y': 700})

        # Generate a sample PDF with the provided positions
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)

        # Draw elements on the PDF
        pdf.drawString(name_position['x'], name_position['y'], "Sample Name")
        pdf.drawString(date_position['x'], date_position['y'], "Sample Date")
        pdf.drawImage(file_url, logo_position['x'], logo_position['y'], width=100, height=50)

        pdf.save()
        buffer.seek(0)

        # Save the generated PDF
        pdf_name = f"certificates/generated/{file.name.split('.')[0]}_sample.pdf"
        pdf_path = default_storage.save(pdf_name, ContentFile(buffer.read()))
        pdf_url = default_storage.url(pdf_path)

        return Response({"file_url": file_url, "sample_pdf_url": pdf_url}, status=201)
from itertools import count
import os
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.db import models
from django.db.models.functions import ExtractMonth
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in
from django.template.loader import render_to_string
from rest_framework import viewsets
from api.models import Lecture, OTP, EnrolledCourse, CourseResource
from api.serializer import LectureSerializer

from api import serializer as api_serializer
from api import models as api_models
from userauths.models import User, Profile
from api.models import EmailSettings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .models import Certificate, CertificateFile, CertificateTemplate, Course
from django.shortcuts import get_object_or_404
from django.core.files.base import ContentFile
from datetime import timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics, status, viewsets
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, PermissionDenied

import random
from decimal import Decimal
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.utils.timezone import now
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
import mimetypes
from wsgiref.util import FileWrapper
from django.contrib.auth.models import Group

def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError(f"Invalid truth value {val}")

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = api_serializer.MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # Only log if login is successful
        if response.status_code == 200:
            try:
                # Add your code here
                pass
            except Exception as e:
                # Handle the exception
                #print(f"An error occurred: {e}")
                # Get user by email or username
                email = request.data.get('email')
                username = request.data.get('username')
                user = None
                if email:
                    user = User.objects.filter(email=email).first()
                elif username:
                    user = User.objects.filter(username=username).first()
                if user:
                    from api.models import UserActivity
                    UserActivity.objects.create(
                        user=user,
                        user_type='user',
                        activity_type='login',
                        details={
                            'ip_address': get_client_ip(request),
                            'user_agent': request.META.get('HTTP_USER_AGENT', '')
                        }
                            )
            except Exception as e:
                    #print(f"Error tracking login in MyTokenObtainPairView: {str(e)}")
                pass
        
        return response

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = api_serializer.RegisterSerializer

def generate_random_otp(length=7):
    otp = ''.join([str(random.randint(0, 9)) for _ in range(length)])
    return otp

from rest_framework import serializers  # Ensure serializers is imported

# Define the PasswordUpdateSerializer if it is not already defined
class PasswordUpdateSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, min_length=8)

class PasswordChangeAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = PasswordUpdateSerializer

    def create(self, request, email, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_password = serializer.validated_data['new_password']

        try:
            # Query the user using the email from the URL
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            return Response({"message": "Password updated successfully"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist"}, status=status.HTTP_404_NOT_FOUND)

class ProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = api_serializer.ProfileSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        user_id = self.kwargs['user_id']
        user = User.objects.get(id=user_id)
        return Profile.objects.get(user=user)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Check if the image is being updated
        if 'image' in request.data:
            new_image = request.data['image']
            # Check if the new_image is a file object before accessing its name
            if hasattr(new_image, 'name') and instance.image and instance.image.name == new_image.name:
                # If the image is the same, skip updating it
                request.data.pop('image')

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)

class CategoryListAPIView(generics.ListAPIView):
    queryset = api_models.Category.objects.filter(active=True)  
    serializer_class = api_serializer.CategorySerializer
    permission_classes = [AllowAny]
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CourseListAPIView(generics.ListAPIView):
    queryset = api_models.Course.objects.filter(platform_status="Published", teacher_course_status="Published")
    serializer_class = api_serializer.CourseSerializer
    permission_classes = [AllowAny]

class CourseDetailAPIView(generics.RetrieveAPIView):
    serializer_class = api_serializer.CourseSerializer
    permission_classes = [AllowAny]
    queryset = api_models.Course.objects.filter(platform_status="Published", teacher_course_status="Published")

    def get_object(self):
        slug = self.kwargs['slug']
        course = api_models.Course.objects.get(slug=slug, platform_status="Published", teacher_course_status="Published")
        return course
    
class CartAPIView(generics.CreateAPIView):
    queryset = api_models.Cart.objects.all()
    serializer_class = api_serializer.CartSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        try:
            course_id = request.data['course_id']  
            user_id = request.data['user_id']
            price = request.data['price']
            country_name = request.data['country_name']
            
            # We'll use a consistent cart ID format for persistence
            cart_id = request.data.get('cart_id', '')

            # Validate course exists
            course = api_models.Course.objects.filter(id=course_id).first()
            if not course:
                return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Set user if provided, otherwise None
            user = None
            if user_id and user_id != "undefined" and user_id != "null":
                try:
                    user = User.objects.get(id=user_id)
                    # Always use the persistent format: user_{user_id}
                    cart_id = f"user_{user.id}"
                except User.DoesNotExist:
                    return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            

            # Get country and tax info
            try:
                country_object = api_models.Country.objects.filter(name=country_name).first()
                country = country_object.name if country_object else "South Africa"
                tax_rate = country_object.tax_rate / 100 if country_object else 0
            except:
                country = "South Africa"
                tax_rate = 0

            # Check if this course is already in the user's cart
            if user:
                cart = api_models.Cart.objects.filter(user=user, course=course).first()
            else:
                cart = api_models.Cart.objects.filter(cart_id=cart_id, course=course).first()

            # Update or create cart item
            if (cart):
                cart.price = price
                cart.tax_fee = Decimal(price) * Decimal(tax_rate)
                cart.country = country
                cart.cart_id = cart_id  # Ensure consistent cart_id
                cart.total = Decimal(cart.price) + Decimal(cart.tax_fee)
                cart.save()

                return Response({
                    "message": "Cart Updated Successfully",
                    "cart_id": cart_id
                }, status=status.HTTP_200_OK)
            else:

                cart = api_models.Cart.objects.create(
                    course=course,
                    user=user,
                    price=price,
                    tax_fee=Decimal(price) * Decimal(tax_rate),
                    country=country,
                    cart_id=cart_id,
                    total=Decimal(price) + (Decimal(price) * Decimal(tax_rate))
                )

                return Response({
                    "message": "Cart Created Successfully",
                    "cart_id": cart_id
                }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CartListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.CartSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        cart_id = self.kwargs['cart_id']
        
        # If cart_id follows the user_{id} pattern
        if cart_id.startswith('user_'):
            try:
                user_id = int(cart_id.split('_')[1])
                user = User.objects.get(id=user_id)

                
                # Return ALL cart items for this user
                return api_models.Cart.objects.filter(user=user)
            except (ValueError, User.DoesNotExist) as e:
                return api_models.Cart.objects.none()
        
        # For legacy cart IDs, just filter by cart_id
        return api_models.Cart.objects.filter(cart_id=cart_id)

class CartItemDeleteAPIView(generics.DestroyAPIView):
    serializer_class = api_serializer.CartSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        cart_id = self.kwargs['cart_id']
        item_id = self.kwargs['item_id']
        
        # print(f"DEBUG: Attempting to delete cart item - cart_id={cart_id}, course_id={item_id}")
        
        # Extract user_id from cart_id if it exists
        user_id = None
        if '_' in cart_id and cart_id.startswith('c'):
            try:
                user_id = int(cart_id.split('_')[1])
                user = User.objects.filter(id=user_id).first()
                
                if user:
                    # print(f"DEBUG: Found user with id={user_id}")
                    # First try finding the item by user and course
                    cart_item = api_models.Cart.objects.filter(user=user, course__id=item_id).first()
                    if cart_item:
                        # print(f"DEBUG: Found cart item by user={user_id} and course_id={item_id}")
                        return cart_item
            except Exception as e:
                # print(f"DEBUG: Error extracting user_id from cart_id {cart_id}: {str(e)}")
        
        # Default: try to find the cart item directly by cart_id and course
            
                cart_item = api_models.Cart.objects.get(cart_id=cart_id, course__id=item_id)
            # print(f"DEBUG: Found cart item with cart_id={cart_id}, course_id={item_id}")
                return cart_item
            except api_models.Cart.DoesNotExist:
            # print(f"DEBUG: No cart item found with cart_id={cart_id}, course_id={item_id}")
            
            # If we couldn't find the item by the exact cart_id, try other variations
                if user_id:
                # Try to find cart items for this user and course, regardless of cart_id
                    cart_items = api_models.Cart.objects.filter(
                    models.Q(user__id=user_id, course__id=item_id) |
                    models.Q(cart_id__endswith=f"_{user_id}", course__id=item_id)
                )
                
                if cart_items.exists():
                    cart_item = cart_items.first()
                    # print(f"DEBUG: Found cart item with user_id={user_id}, course_id={item_id}, cart_id={cart_item.cart_id}")
                    return cart_item
        
        # print(f"DEBUG: No cart item found matching any criteria")
        return None

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response({"detail": "Cart item not found."}, status=404)
        
        # Store course ID before deleting
        course_id = instance.course.id if instance.course else None
        
        # Delete the cart item
        instance.delete()
        
        return Response({"detail": "Item removed successfully", "course_id": course_id}, status=200)

class CartStatsAPIView(generics.RetrieveAPIView):
    serializer_class = api_serializer.CartSerializer
    permission_classes = [AllowAny]
    lookup_field = 'cart_id'

    def get_queryset(self):
        cart_id = self.kwargs['cart_id']
        queryset = api_models.Cart.objects.filter(cart_id=cart_id)
        return queryset
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        total_price = 0.00
        total_tax = 0.00
        total_total = 0.00

        for cart_item in queryset:
            total_price += float(self.calculate_price(cart_item))
            total_tax += float(self.calculate_tax(cart_item))
            total_total += round(float(self.calculate_total(cart_item)), 2)

        data = {
            "price": total_price,
            "tax": total_tax,
            "total": total_total,
        }

        return Response(data)

    def calculate_price(self, cart_item):
        return cart_item.price
    
    def calculate_tax(self, cart_item):
        return cart_item.tax_fee

    def calculate_total(self, cart_item):
        return cart_item.total
    



class CreateOrderAPIView(generics.CreateAPIView):
    serializer_class = api_serializer.CartOrderSerializer
    permission_classes = [AllowAny]
    queryset = api_models.CartOrder.objects.all()

    def create(self, request, *args, **kwargs):
        try:
            # Extract data from the request
            full_name = request.data.get('full_name')
            email = request.data.get('email')
            country = request.data.get('country')
            cart_id = request.data.get('cart_id')
            user_id = request.data.get('user_id')

            # Validate user_id
            user = None
            if user_id and user_id != 0:
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            # Validate cart items
            cart_items = api_models.Cart.objects.filter(cart_id=cart_id)
            if not cart_items.exists():
                return Response({"error": "Cart is empty or invalid cart_id"}, status=status.HTTP_400_BAD_REQUEST)

            # Initialize totals
            total_price = Decimal(0.00)
            total_tax = Decimal(0.00)
            total_initial_total = Decimal(0.00)
            total_total = Decimal(0.00)

            # Create the order
            order = api_models.CartOrder.objects.create(
                full_name=full_name,
                email=email,
                country=country,
                student=user
            )

            # Process cart items and calculate totals
            for c in cart_items:
                api_models.CartOrderItem.objects.create(
                    order=order,
                    course=c.course,
                    price=c.price,
                    tax_fee=c.tax_fee,
                    total=c.total,
                    initial_total=c.total,
                    teacher=c.course.teacher
                )

                total_price += Decimal(c.price)
                total_tax += Decimal(c.tax_fee)
                total_initial_total += Decimal(c.total)
                total_total += Decimal(c.total)

                order.teachers.add(c.course.teacher)

            # Update order totals
            order.sub_total = total_price
            order.tax_fee = total_tax
            order.initial_total = total_initial_total
            order.total = total_total
            order.save()

            return Response({"message": "Order Created Successfully", "order_oid": order.oid}, status=status.HTTP_201_CREATED)

        except KeyError as e:
            return Response({"error": f"Missing field: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class CheckoutAPIView(generics.RetrieveAPIView):
    serializer_class = api_serializer.CartOrderSerializer
    permission_classes = [AllowAny]
    queryset = api_models.CartOrder.objects.all()
    lookup_field = 'oid'


class CouponApplyAPIView(generics.CreateAPIView):
    serializer_class = api_serializer.CouponSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        order_oid = request.data['order_oid']
        coupon_code = request.data['coupon_code']

        order = api_models.CartOrder.objects.get(oid=order_oid)
        coupon = api_models.Coupon.objects.get(code=coupon_code)

        if coupon:
            order_items = api_models.CartOrderItem.objects.filter(order=order, teacher=coupon.teacher)
            for i in order_items:
                if not coupon in i.coupons.all():
                    discount = i.total * coupon.discount / 100

                    i.total -= discount
                    i.price -= discount
                    i.saved += discount
                    i.applied_coupon = True
                    i.coupons.add(coupon)

                    order.coupons.add(coupon)
                    order.total -= discount
                    order.sub_total -= discount
                    order.saved += discount

                    i.save()
                    order.save()
                    coupon.used_by.add(order.student)
                    return Response({"message": "Coupon Found and Activated", "icon": "success"}, status=status.HTTP_201_CREATED)
                else:
                    return Response({"message": "Coupon Already Applied", "icon": "warning"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Coupon Not Found", "icon": "error"}, status=status.HTTP_404_NOT_FOUND)

# Import necessary modules for Yoco
from django.conf import settings
from django.http import JsonResponse
import requests

class SearchCourseAPIView(generics.ListAPIView):
    serializer_class = api_serializer.CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        query = self.request.GET.get('query')
        # learn lms
        return api_models.Course.objects.filter(title__icontains=query, platform_status="Published", teacher_course_status="Published")
    
class StudentSummaryAPIView(generics.ListAPIView):
    serializer_class = api_serializer.StudentSummarySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = User.objects.get(id=user_id)

        # Enrolled courses
        enrolled_courses = api_models.EnrolledCourse.objects.filter(user=user)
        enrolled_course_ids = enrolled_courses.values_list('course', flat=True)
        total_courses = enrolled_courses.count()
        # print(f"[StudentSummaryAPIView] Enrolled courses: {list(enrolled_course_ids)} (Total: {total_courses})")

        # Incomplete lectures
        incomplete_lectures = Lecture.objects.filter(
            course__in=enrolled_course_ids
        ).exclude(
            id__in=VideoProgress.objects.filter(
                user=user, completed=True
            ).values_list('lecture_id', flat=True)
        ).count()
        # print(f"[StudentSummaryAPIView] Incomplete lectures: {incomplete_lectures}")

        # Pending assignments
        pending_assignments = Assignment.objects.filter(
            course__in=enrolled_course_ids,
            status='published'
        ).exclude(
            id__in=AssignmentSubmission.objects.filter(
                student=user
            ).values_list('assignment_id', flat=True)
        ).count()
        # print(f"[StudentSummaryAPIView] Pending assignments: {pending_assignments}")

        # Available quizzes (published, not completed) - exclude before union
        completed_quiz_ids = QuizSubmission.objects.filter(
            student=user, status='completed'
        ).values_list('quiz_id', flat=True)

        course_quizzes = Quiz.objects.filter(
            course__in=enrolled_course_ids,
            status='published'
        ).exclude(id__in=completed_quiz_ids)

        lecture_quizzes = Quiz.objects.filter(
            lecture__course__in=enrolled_course_ids,
            status='published'
        ).exclude(id__in=completed_quiz_ids)

        all_quizzes = course_quizzes.union(lecture_quizzes)
        available_quizzes = all_quizzes.count()
        # print(f"[StudentSummaryAPIView] Available quizzes: {available_quizzes}")

        # Activity tracking (last 3 months, like teacher dashboard)
        today = timezone.now().date()
        three_months_ago = today - timedelta(days=90)
        activities = UserActivity.objects.filter(
            user=user,
            course__in=enrolled_course_ids,
            timestamp__gte=three_months_ago
        )
        # print(f"[StudentSummaryAPIView] Activities in last 3 months: {activities.count()}")

        # Monthly activity for last 3 months (timezone-aware and logging)
        months = [(today.month - i) % 12 or 12 for i in range(3)][::-1]
        monthly_quiz_activity = [0, 0, 0]
        monthly_assignment_activity = [0, 0, 0]
        monthly_lecture_activity = [0, 0, 0]

        for i, month in enumerate(months):
            # Calculate year correctly for current and previous months
            year = today.year
            if month > today.month:
                year = year - 1  # Previous year for later months
                
            # Calculate the next month and year for range ending
            next_month = month % 12 + 1
            next_year = year
            if month == 12:
                next_year = year + 1
                next_month = 1

            # Make timezone-aware datetimes
            start_date = timezone.make_aware(datetime(year, month, 1))
            end_date = timezone.make_aware(datetime(next_year, next_month, 1))

            # Log the date range for debugging
            # print(f"[StudentSummaryAPIView] Month index {i}: {start_date} to {end_date}")

            # Count quiz activities
            monthly_quiz_activity[i] = activities.filter(
                activity_type='quiz_attempt',
                timestamp__gte=start_date,
                timestamp__lt=end_date
            ).count()
            
            # Count assignment activities - FIXED to correctly track assignment submissions
            # We need to count both UserActivity records and actual AssignmentSubmission records
            assignment_activities = activities.filter(
                activity_type='assignment_submission',
                timestamp__gte=start_date,
                timestamp__lt=end_date
            ).count()
            
            # Also check actual AssignmentSubmission records
            assignment_submissions = AssignmentSubmission.objects.filter(
                student=user,
                submitted_at__gte=start_date,
                submitted_at__lt=end_date
            ).count()
            
            # Use the higher count to ensure we don't miss any submissions
            monthly_assignment_activity[i] = max(assignment_activities, assignment_submissions)
            
            # Count lecture activities
            monthly_lecture_activity[i] = activities.filter(
                activity_type='content_view',
                timestamp__gte=start_date,
                timestamp__lt=end_date
            ).count()
            
            # print(f"[StudentSummaryAPIView] Month {i} ({start_date.strftime('%b %Y')}): "
            #       f"Quizzes={monthly_quiz_activity[i]}, Assignments={monthly_assignment_activity[i]}, Lectures={monthly_lecture_activity[i]}")

        # Daily activity (today)
        daily_quiz_count = activities.filter(
            activity_type='quiz_attempt',
            timestamp__date=today
        ).count()
        
        # Fix for daily assignment count - check both activity records and actual submissions
        daily_activity_assignment_count = activities.filter(
            activity_type='assignment_submission',
            timestamp__date=today
        ).count()
        
        daily_submission_assignment_count = AssignmentSubmission.objects.filter(
            student=user,
            submitted_at__date=today
        ).count()
        
        # Use the higher count
        daily_assignment_count = max(daily_activity_assignment_count, daily_submission_assignment_count)
        
        daily_lecture_count = activities.filter(
            activity_type='content_view',
            timestamp__date=today
        ).count()
        
        daily_other_count = activities.filter(
            timestamp__date=today
        ).exclude(
            activity_type__in=['quiz_attempt', 'assignment_submission', 'content_view']
        ).count()
        
        # print(f"[StudentSummaryAPIView] Daily activity: Quizzes={daily_quiz_count}, Assignments={daily_assignment_count}, Lectures={daily_lecture_count}, Other={daily_other_count}")

        # Course progress
        course_progress = []
        for enrollment in enrolled_courses:
            course = enrollment.course
            lectures = Lecture.objects.filter(course=course)
            total_lectures = lectures.count()
            progress_records = VideoProgress.objects.filter(user=user, course=course)
            completed_lectures = progress_records.filter(completed=True).count()
            progress_percentage = (completed_lectures / total_lectures) * 100 if total_lectures > 0 else 0
            course_progress.append({
                "course_id": course.id,
                "title": course.title,
                "progress": progress_percentage,
                "completed": completed_lectures,
                "total": total_lectures
            })
            # print(f"[StudentSummaryAPIView] Course '{course.title}': {completed_lectures}/{total_lectures} lectures completed ({progress_percentage:.2f}%)")

        # print(f"[StudentSummaryAPIView] Returning summary for user {user_id}")
        return [{
            "total_courses": total_courses,
            "incomplete_lectures": incomplete_lectures,
            "pending_assignments": pending_assignments,
            "available_quizzes": available_quizzes,
            "daily_quiz_count": daily_quiz_count,
            "daily_assignment_count": daily_assignment_count,
            "daily_lecture_count": daily_lecture_count,
            "daily_other_count": daily_other_count,
            "monthly_quiz_activity": monthly_quiz_activity,
            "monthly_assignment_activity": monthly_assignment_activity,
            "monthly_lecture_activity": monthly_lecture_activity,
            "course_progress": course_progress,
            "months": months
        }]
    
    def post(self, request, user_id):
        """Track quiz attempts at the first auto-marked question"""
        try:
            # Verify the user has permission to track attempts for this user_id
            if str(request.user.id) != str(user_id):
                return Response(
                    {"error": "You don't have permission to track attempts for this user"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            quiz_id = request.data.get('quiz_id')
            question_id = request.data.get('question_id')
            course_id = request.data.get('course_id')
            
            if not quiz_id or not question_id:
                return Response(
                    {"error": "Quiz ID and Question ID are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify the quiz and question exist
            quiz = get_object_or_404(Quiz, id=quiz_id)
            question = get_object_or_404(QuizQuestion, id=question_id, quiz=quiz)
            
            # Get the course
            course = None
            if course_id:
                course = get_object_or_404(Course, id=course_id)
            elif quiz.course:
                course = quiz.course
            elif quiz.lecture and quiz.lecture.course:
                course = quiz.lecture.course
            
            # Always create an activity record for better tracking
            # (we'll check duplicates by our own logic)
            activity = UserActivity(
                user=request.user,
                user_type='user',  # Use string literals instead of constants
                activity_type='quiz_attempt',  # Use string literals instead of constants
                content_id=str(quiz_id),
                timestamp=timezone.now()
            )
            
            # Associate with course if available
            if course:
                activity.course = course
                
            # Add details to the activity
            activity.details = {
                "quiz_title": quiz.title,
                "first_question_id": str(question_id),
                "timestamp": timezone.now().isoformat()
            }
            
            # Save the activity
            activity.save()
            
            # Check if this is a duplicate attempt for logging purposes only
            existing_attempt = UserActivity.objects.filter(
                user=request.user,
                activity_type='quiz_attempt',
                content_id=str(quiz_id)
            ).exclude(id=activity.id).exists()
            
            return Response({
                "message": "Quiz attempt recorded successfully",
                "is_first_attempt": not existing_attempt
            }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            # print(f"Error tracking quiz attempt: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class StudentCourseListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.EnrolledCourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user =  User.objects.get(id=user_id)
        return api_models.EnrolledCourse.objects.filter(user=user)
    

class StudentCourseDetailAPIView(generics.RetrieveAPIView):
    serializer_class = api_serializer.EnrolledCourseSerializer
    permission_classes = [AllowAny]
    lookup_field = 'enrollment_id'

    def get_object(self):
        user_id = self.kwargs['user_id']
        enrollment_id = self.kwargs['enrollment_id']

        user = User.objects.get(id=user_id)
        return api_models.EnrolledCourse.objects.get(user=user, enrollment_id=enrollment_id)
         
        
class StudentCourseCompletedCreateAPIView(generics.CreateAPIView):
    serializer_class = api_serializer.CompletedLessonSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        user_id = request.data['user_id']
        course_id = request.data['course_id']
        variant_item_id = request.data['variant_item_id']

        user = User.objects.get(id=user_id)
        course = api_models.Course.objects.get(id=course_id)
        variant_item = api_models.VariantItem.objects.get(variant_item_id=variant_item_id)

        completed_lessons = api_models.CompletedLesson.objects.filter(user=user, course=course, variant_item=variant_item).first()

        if completed_lessons:
            completed_lessons.delete()
            return Response({"message": "Course marked as not completed"})

        else:
            api_models.CompletedLesson.objects.create(user=user, course=course, variant_item=variant_item)
            return Response({"message": "Course marked as completed"})
        

class StudentNoteCreateAPIView(generics.ListCreateAPIView):
    serializer_class = api_serializer.NoteSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        enrollment_id = self.kwargs['enrollment_id']

        user = User.objects.get(id=user_id)
        enrolled = api_models.EnrolledCourse.objects.get(enrollment_id=enrollment_id)
        
        return api_models.Note.objects.filter(user=user, course=enrolled.course)

    def create(self, request, *args, **kwargs):
        user_id = request.data['user_id']
        enrollment_id = request.data['enrollment_id']
        title = request.data['title']
        note = request.data['note']

        user = User.objects.get(id=user_id)
        enrolled = api_models.EnrolledCourse.objects.get(enrollment_id=enrollment_id)
        
        api_models.Note.objects.create(user=user, course=enrolled.course, note=note, title=title)

        return Response({"message": "Note created successfullly"}, status=status.HTTP_201_CREATED)
    

class StudentNoteDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = api_serializer.NoteSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        user_id = self.kwargs['user_id']
        enrollment_id = self.kwargs['enrollment_id']
        note_id = self.kwargs['note_id']

        user = User.objects.get(id=user_id)
        enrolled = api_models.EnrolledCourse.objects.get(enrollment_id=enrollment_id)
        note = api_models.Note.objects.get(user=user, course=enrolled.course, id=note_id)
        return note


class StudentRateCourseCreateAPIView(generics.CreateAPIView):
    serializer_class = api_serializer.ReviewSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        user_id = request.data['user_id']
        course_id = request.data['course_id']
        rating = request.data['rating']
        review = request.data['review']

        user = User.objects.get(id=user_id)
        course = api_models.Course.objects.get(id=course_id)

        api_models.Review.objects.create(
            user=user,
            course=course,
            review=review,
            rating=rating,
            active=True,
        )

        return Response({"message": "Review created successfullly"}, status=status.HTTP_201_CREATED)


class StudentRateCourseUpdateAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = api_serializer.ReviewSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        user_id = self.kwargs['user_id']
        review_id = self.kwargs['review_id']

        user = User.objects.get(id=user_id)
        return api_models.Review.objects.get(id=review_id, user=user)
    

class StudentWishListListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = api_serializer.WishlistSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        user_id = self.kwargs['user_id']
        user = User.objects.get(id=user_id)
        return api_models.Wishlist.objects.filter(user=user)
    
    def create(self, request, *args, **kwargs):
        user_id = request.data['user_id']
        course_id = request.data['course_id']

        user = User.objects.get(id=user_id)
        course = api_models.Course.objects.get(id=course_id)

        wishlist = api_models.Wishlist.objects.filter(user=user, course=course).first()
        if (wishlist):
            wishlist.delete()
            return Response({"message": "Wishlist Deleted"}, status=status.HTTP_200_OK)
        else:
            api_models.Wishlist.objects.create(
                user=user, course=course
            )
            return Response({"message": "Wishlist Created"}, status=status.HTTP_201_CREATED)



class QuestionAnswerListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = api_serializer.Question_AnswerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        course = api_models.Course.objects.get(id=course_id)
        return api_models.Question_Answer.objects.filter(course=course)
    
    def create(self, request, *args, **kwargs):
        course_id = request.data['course_id']
        user_id = request.data['user_id']
        title = request.data['title']
        message = request.data['message']

        user = User.objects.get(id=user_id)
        course = api_models.Course.objects.get(id=course_id)
        
        question = api_models.Question_Answer.objects.create(
            course=course,
            user=user,
            title=title
        )

        api_models.Question_Answer_Message.objects.create(
            course=course,
            user=user,
            message=message,
            question=question
        )
        
        return Response({"message": "Group conversation Started"}, status=status.HTTP_201_CREATED)


class QuestionAnswerMessageSendAPIView(generics.CreateAPIView):
    serializer_class = api_serializer.Question_Answer_MessageSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        course_id = request.data['course_id']
        qa_id = request.data['qa_id']
        user_id = request.data['user_id']
        message = request.data['message']

        user = User.objects.get(id=user_id)
        course = api_models.Course.objects.get(id=course_id)
        question = api_models.Question_Answer.objects.get(qa_id=qa_id)
        api_models.Question_Answer_Message.objects.create(
            course=course,
            user=user,
            message=message,
            question=question
        )

        question_serializer = api_serializer.Question_AnswerSerializer(question)
        return Response({"messgae": "Message Sent", "question": question_serializer.data})




class TeacherSummaryAPIView(generics.ListAPIView):
    serializer_class = api_serializer.TeacherSummarySerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        teacher = api_models.Teacher.objects.get(id=teacher_id)

        one_month_ago = datetime.today() - timedelta(days=28)

        total_courses = api_models.Course.objects.filter(teacher=teacher).count()
        total_revenue = api_models.CartOrderItem.objects.filter(teacher=teacher, order__payment_status="Paid").aggregate(total_revenue=models.Sum("price"))['total_revenue'] or 0
        monthly_revenue = api_models.CartOrderItem.objects.filter(teacher=teacher, order__payment_status="Paid", date__gte=one_month_ago).aggregate(total_revenue=models.Sum("price"))['total_revenue'] or 0

        enrolled_courses = api_models.EnrolledCourse.objects.filter(teacher=teacher)
        unique_student_ids = set()
        students = []

        for course in enrolled_courses:
            if course.user_id not in unique_student_ids:
                user = User.objects.get(id=course.user_id)
                student = {
                    "full_name": user.profile.full_name,
                    "image": user.profile.image.url,
                    "country": user.profile.country,
                    "date": course.date
                }

                students.append(student)
                unique_student_ids.add(course.user_id)

        return [{
            "total_courses": total_courses,
            "total_revenue": total_revenue,
            "monthly_revenue": monthly_revenue,
            "total_students": len(students),
        }]
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    

class TeacherCourseListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        teacher = api_models.Teacher.objects.get(id=teacher_id)
        return api_models.Course.objects.filter(teacher=teacher)
    

class TeacherReviewListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        teacher = api_models.Teacher.objects.get(id=teacher_id)
        return api_models.Review.objects.filter(course__teacher=teacher)
    

class TeacherReviewDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = api_serializer.ReviewSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        teacher_id = self.kwargs['teacher_id']
        review_id = self.kwargs['review_id']
        teacher = api_models.Teacher.objects.get(id=teacher_id)
        return api_models.Review.objects.get(course__teacher=teacher, id=review_id)
    

class TeacherStudentsListAPIVIew(viewsets.ViewSet):
    
    def list(self, request, teacher_id=None):
        teacher = api_models.Teacher.objects.get(id=teacher_id)

        enrolled_courses = api_models.EnrolledCourse.objects.filter(teacher=teacher)
        unique_student_ids = set()
        students = []

        for course in enrolled_courses:
            if course.user_id not in unique_student_ids:
                user = User.objects.get(id=course.user_id)
                student = {
                    "full_name": user.profile.full_name,
                    "image": user.profile.image.url,
                    "country": user.profile.country,
                    "date": course.date
                }

                students.append(student)
                unique_student_ids.add(course.user_id)

        return Response(students)
    

@api_view(("GET", ))
def TeacherAllMonthEarningAPIView(request, teacher_id):
    teacher = api_models.Teacher.objects.get(id=teacher_id)
    monthly_earning_tracker = (
        api_models.CartOrderItem.objects
        .filter(teacher=teacher, order__payment_status="Paid")
        .annotate(
            month=ExtractMonth("date")
        )
        .values("month")
        .annotate(
            total_earning=models.Sum("price")
        )
        .order_by("month")
    )

    return Response(monthly_earning_tracker)

class TeacherBestSellingCourseAPIView(viewsets.ViewSet):

    def list(self, request, teacher_id=None):
        teacher = api_models.Teacher.objects.get(id=teacher_id)
        courses_with_total_price = []
        courses = api_models.Course.objects.filter(teacher=teacher)

        for course in courses:
            revenue = course.enrolledcourse_set.aggregate(total_price=models.Sum('order_item__price'))['total_price'] or 0
            sales = course.enrolledcourse_set.count()

            courses_with_total_price.append({
                'course_image': course.image.url,
                'course_title': course.title,
                'revenue': revenue,
                'sales': sales,
            })

        return Response(courses_with_total_price)
    
class TeacherCourseOrdersListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.CartOrderItemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        teacher = api_models.Teacher.objects.get(id=teacher_id)

        return api_models.CartOrderItem.objects.filter(teacher=teacher)

class TeacherQuestionAnswerListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.Question_AnswerSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        teacher = api_models.Teacher.objects.get(id=teacher_id)
        return api_models.Question_Answer.objects.filter(course__teacher=teacher)
    
class TeacherCouponListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = api_serializer.CouponSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        teacher = api_models.Teacher.objects.get(id=teacher_id)
        return api_models.Coupon.objects.filter(teacher=teacher)
    
class TeacherCouponDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = api_serializer.CouponSerializer
    permission_classes = [AllowAny]
    
    def get_object(self):
        teacher_id = self.kwargs['teacher_id']
        coupon_id = self.kwargs['coupon_id']
        teacher = api_models.Teacher.objects.get(id=teacher_id)
        return api_models.Coupon.objects.get(teacher=teacher, id=coupon_id)
    
class TeacherNotificationListAPIView(generics.ListAPIView):
    serializer_class = api_serializer.NotificationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        teacher_id = self.kwargs['teacher_id']
        teacher = api_models.Teacher.objects.get(id=teacher_id)
        return api_models.Notification.objects.filter(teacher=teacher, seen=False)
    
class TeacherNotificationDetailAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = api_serializer.NotificationSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        teacher_id = self.kwargs['teacher_id']
        noti_id = self.kwargs['noti_id']
        teacher = api_models.Teacher.objects.get(id=teacher_id)
        return api_models.Notification.objects.get(teacher=teacher, id=noti_id)
    
class CourseCreateAPIView(generics.CreateAPIView):
    queryset = api_models.Course.objects.all()
    serializer_class = api_serializer.CourseSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        teacher = get_object_or_404(api_models.Teacher, user=self.request.user)
        serializer.save(teacher=teacher)


class CourseUpdateAPIView(generics.RetrieveUpdateAPIView):
    queryset = api_models.Course.objects.all()
    serializer_class = api_serializer.CourseSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Get the teacher from the logged-in user
        teacher = get_object_or_404(api_models.Teacher, user=self.request.user)
        course_id = self.kwargs.get('course_id')
        # Only allow updating courses owned by this teacher
        course = get_object_or_404(api_models.Course, id=course_id, teacher=teacher)
        return course

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        course = self.get_object()
        data = request.data.copy()

        # Handle image update/removal
        if "image" in data:
            image = data.get('image')
            if isinstance(image, InMemoryUploadedFile):
                course.image = image
            elif str(image) == "No File":
                course.image = None

        # Handle file update
        if "file" in data:
            file = data.get('file')
            if file and not str(file).startswith("https://"):
                course.file = file

        # Handle category update
        category_id = data.get('category')
        if category_id and category_id not in ['NaN', "undefined", None, ""]:
            try:
                category = api_models.Category.objects.get(id=category_id)
                course.category = category
            except api_models.Category.DoesNotExist:
                pass

        serializer = self.get_serializer(course, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Handle variants if needed (call your update_variant method if you use it)
        if hasattr(self, 'update_variant'):
            self.update_variant(course, data)

        return Response(serializer.data, status=status.HTTP_200_OK)


class CourseDetailAPIView(generics.RetrieveDestroyAPIView):
    serializer_class = api_serializer.CourseSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        course_id = self.kwargs['course_id']
        return api_models.Course.objects.get(course_id=course_id)


class CourseVariantDeleteAPIView(generics.DestroyAPIView):
    serializer_class = api_serializer.VariantSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        variant_id = self.kwargs['variant_id']
        teacher_id = self.kwargs['teacher_id']
        course_id = self.kwargs['course_id']

        #print("variant_id ========", variant_id)

        teacher = api_models.Teacher.objects.get(id=teacher_id)
        course = api_models.Course.objects.get(teacher=teacher, course_id=course_id)
        return api_models.Variant.objects.get(id=variant_id)
    
class CourseVariantItemDeleteAPIVIew(generics.DestroyAPIView):
    serializer_class = api_serializer.VariantItemSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        variant_id = self.kwargs['variant_id']
        variant_item_id = self.kwargs['variant_item_id']
        teacher_id = self.kwargs['teacher_id']
        course_id = self.kwargs['course_id']


        teacher = api_models.Teacher.objects.get(id=teacher_id)
        course = api_models.Course.objects.get(teacher=teacher, course_id=course_id)
        variant = api_models.Variant.objects.get(variant_id=variant_id, course=course)
        return api_models.VariantItem.objects.get(variant=variant, variant_item_id=variant_item_id)



class LectureViewSet(viewsets.ModelViewSet):

    queryset = Lecture.objects.all()
    serializer_class = LectureSerializer

    def get_queryset(self):

        course_id = self.request.query_params.get('course_id')
        if (course_id):
            return self.queryset.filter(course_id=course_id)
        return self.queryset

from api.models import EmailSettings
from api.serializer import EmailSettingsSerializer
from rest_framework import serializers

class OTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(required=False, max_length=6)
    password = serializers.CharField(required=False, write_only=True)

class EmailSettingsViewSet(viewsets.ModelViewSet):
    queryset = EmailSettings.objects.all()
    serializer_class = EmailSettingsSerializer
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def perform_create(self, serializer):
        # Save the email settings
        email_settings = serializer.save()

        # Send a confirmation email
        self.send_confirmation_email(email_settings)

    def perform_update(self, serializer):
        # Update the email settings
        email_settings = serializer.save()

        # Send a confirmation email
        self.send_confirmation_email(email_settings)

    def send_confirmation_email(self, email_settings):
        """
        Sends a confirmation email to the configured email address.
        """
        try:
            # Configure the email connection dynamically
            connection = get_connection(
                host=email_settings.email_host,
                port=email_settings.email_port,
                username=email_settings.email_host_user,
                password=email_settings.email_host_password,
                use_tls=email_settings.email_use_tls
            )

            # Prepare the email
            subject = "SMTP Configuration for Bonjour Classe"
            message = (
                f"Hello,\n\n"
                f"This email confirms that the email address {email_settings.email_host_user} "
                f"has been configured for SMTP in Bonjour Classe.\n\n"
                f"Thank you!"
            )
            msg = EmailMultiAlternatives(
                subject=subject,
                from_email=email_settings.default_from_email,
                to=[email_settings.email_host_user],
                body=message,
                connection=connection
            )

            # Send the email
            msg.send()
            print(f"Confirmation email sent to {email_settings.email_host_user}.")
        except Exception as e:
            print(f"Failed to send confirmation email: {e}")
            
# Add this function near other email related functions

def send_subscription_email(user, subject, message, template_name):
    """
    Send subscription related emails
    """
    try:
        # Get the default email settings
        email_settings = EmailSettings.objects.first()
        
        if not email_settings:
           # print("No email settings found")
            return False
            
        # Configure email connection
        connection = get_connection(
            host=email_settings.email_host,
            port=email_settings.email_port,
            username=email_settings.email_host_user,
            password=email_settings.email_host_password,
            use_tls=email_settings.email_use_tls
        )
        
        # Prepare the context for the email template
        context = {
            'username': user.get_full_name() or user.username,
            'message': message,
            'site_name': 'Bonjour Classe',
            'subscription_details': None
        }
        
        # Add subscription details if user has one
        subscription = Subscription.objects.filter(user=user).first()
        if subscription and subscription.package:
            context['subscription_details'] = {
                'name': subscription.package.name,
                'price': subscription.package.price,
                'valid_until': subscription.valid_until.strftime('%B %d, %Y') if subscription.valid_until else 'N/A',
                'auto_renew': subscription.auto_renew
            }
        
        # Render email templates
        html_email = render_to_string(f'email/{template_name}.html', context)
        text_email = render_to_string(f'email/{template_name}.txt', context)
        
        # Create and send the email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_email,
            from_email=email_settings.default_from_email,
            to=[user.email],
            connection=connection
        )
        email.attach_alternative(html_email, "text/html")
        email.send()
        
        return True
        
    except Exception as e:
        #print(f"Error sending subscription email: {str(e)}")
        return False

# Generate and store OTP
class RequestOTPAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')

        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Add your code here
            pass
            # Check if the user exists
            profile = Profile.objects.get(user__email=email)

            # Delete all old OTPs for the user
            OTP.objects.filter(email=email).delete()

            # Generate a random 6-digit OTP
            otp = str(random.randint(100000, 999999))

            # Save the new OTP in the OTP model
            otp_entry = OTP.objects.create(
                email=email,
                otp=otp,
                created_at=now()
            )

            # Debugging: Log the OTP and save status
            #print(f"OTP entry created: {otp_entry}")

            # Send the OTP via email
            self.send_otp_email(email, otp, profile.user.username)

            return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'An error occurred: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            print(f"An error occurred: {e}")
            # Check if the user exists
            profile = Profile.objects.get(user__email=email)

            # Delete all old OTPs for the user
            OTP.objects.filter(email=email).delete()

            # Generate a random 6-digit OTP
            otp = str(random.randint(100000, 999999))

            # Save the new OTP in the OTP model
            otp_entry = OTP.objects.create(
                email=email,
                otp=otp,
                created_at=now()
            )

            # Debugging: Log the OTP and save status
            #print(f"OTP entry created: {otp_entry}")

            # Send the OTP via email
            self.send_otp_email(email, otp, profile.user.username)

            return Response({'message': 'OTP sent successfully'}, status=status.HTTP_200_OK)

        except Profile.DoesNotExist:
                    return Response({'error': 'Profile does not exist for the given email'}, status=status.HTTP_404_NOT_FOUND)
        
    def send_otp_email(self, email, otp, username):
        from django.core.mail import send_mail, get_connection, EmailMultiAlternatives
        from django.template.loader import render_to_string
        import os
        
        try:
            # Get the email settings from database
            email_settings = EmailSettings.objects.first()
              # Use the production URL for the logo
            production_domain = "https://api.bonjourclasse.online"
            
            # Check if a logo exists in any of the expected locations
            logo_paths = [
                os.path.join(settings.STATIC_ROOT, 'logo', 'logo.png'),
                os.path.join(settings.BASE_DIR, 'static', 'logo', 'logo.png'),
                os.path.join(settings.BASE_DIR, 'static', 'logo', 'admin-logo.png')
            ]
            
            # Set logo_url to the production URL regardless of environment
            logo_url = production_domain + '/static/logo/logo.png'
            
            # Fallback to empty string if needed (shouldn't happen often)
            logo_exists = any(os.path.exists(path) for path in logo_paths)
            if not logo_exists:
                logo_url = ''
            
            if not email_settings:
                # Fallback to default settings if no email settings found
                subject = "Password Reset Request"
                context = {
                    'username': username,
                    'otp': otp,
                    'otp_expiry': 5,  # OTP expiry time in minutes
                    'logo_url': logo_url,
                }
                message = render_to_string('email/password_reset.html', context)
                send_mail(subject, '', settings.DEFAULT_FROM_EMAIL, [email], html_message=message)
                return
                
            # Configure the email connection using settings from database
            connection = get_connection(
                host=email_settings.email_host,
                port=email_settings.email_port,
                username=email_settings.email_host_user,
                password=email_settings.email_host_password,
                use_tls=email_settings.email_use_tls
            )
            
            # Prepare the email content
            subject = "Password Reset Request"
            context = {
                'username': username,
                'otp': otp,
                'otp_expiry': 5,  # OTP expiry time in minutes
                'logo_url': logo_url,
            }
            
            # Render HTML message
            html_message = render_to_string('email/password_reset.html', context)
            text_message = f"Your OTP code for password reset is: {otp}. This code will expire in 5 minutes."
            
            # Create and send the email
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=email_settings.default_from_email,
                to=[email],
                connection=connection
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send()
        except Exception as e:
            # Fallback to default method if there's an error
            # print(f"Error sending OTP email: {str(e)}, falling back to default method")
            
            # Always use the production URL in error case as well
            try:
                production_domain = "https://api.bonjourclasse.online"
                logo_url = production_domain + '/static/logo/logo.png'
            except:
                logo_url = ''
                
            subject = "Password Reset Request"
            context = {
                'username': username,
                'otp': otp,
                'otp_expiry': 5,
                'logo_url': logo_url,
            }
            message = render_to_string('email/password_reset.html', context)
            send_mail(subject, '', settings.DEFAULT_FROM_EMAIL, [email], html_message=message)

# Password Reset with OTP
class PasswordResetAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = OTPSerializer

    def create(self, request, *args, **kwargs):
        email = request.data.get('email')
        otp = request.data.get('otp', '').strip()  # Strip leading/trailing spaces
        password = request.data.get('password')

        if not email or not otp or not password:
            return Response({'error': 'Email, OTP, and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Use UserSerializer to fetch and validate user data
            user = User.objects.get(email=email)
            user_data = api_serializer.UserSerializer(user).data

            profile = Profile.objects.get(user=user)

            # Validate OTP
            if profile.otp != otp:
                return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

            # Validate password (e.g., minimum length of 8 characters)
            if len(password) < 8:
                return Response({'error': 'Password must be at least 8 characters long'}, status=status.HTTP_400_BAD_REQUEST)

            # Update password and clear OTP
            user.set_password(password)
            profile.otp = ''  # Clear OTP after use
            profile.save()
            user.save()

            return Response({'message': 'Password changed successfully', 'user': user_data}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'error': 'User does not exist'}, status=status.HTTP_404_NOT_FOUND)
        except Profile.DoesNotExist:
            return Response({'error': 'Profile does not exist'}, status=status.HTTP_404_NOT_FOUND)

class VerifyOtpAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, email, *args, **kwargs):
        """
        Handle GET requests to check if an OTP exists for the given email.
        """
        try:
            #print(f"Looking for OTP for email: {email}")  # Debugging log
            otp_entry = OTP.objects.filter(email=email).first()

            if not otp_entry:
                #print(f"No OTP found for email: {email}")  # Debugging log
                return Response({'error': 'OTP not found for the given email.'}, status=404)

            #print(f"Found OTP for email {email}: {otp_entry.otp}")  # Debugging log
            return Response({'email': email, 'otp': otp_entry.otp, 'created_at': otp_entry.created_at}, status=200)
        except Exception as e:
            #print(f"An error occurred while retrieving OTP: {str(e)}")  # Debugging log
            return Response({'error': f'An error occurred: {str(e)}'}, status=500)

    def post(self, request, email, *args, **kwargs):
        """
        Handle POST requests to verify the OTP.
        """
        otp = request.data.get('otp', '').strip()

        if not otp:
            return Response({'error': 'OTP is required.'}, status=400)

        try:
            otp_entry = OTP.objects.filter(email=email).first()

            if not otp_entry:
                return Response({'error': 'OTP not found.'}, status=404)

            if otp_entry.otp != otp:
                return Response({'error': 'Invalid OTP.'}, status=400)

            # Generate uuidb64 for the user
            user = User.objects.get(email=email)
            uuidb64 = urlsafe_base64_encode(force_bytes(user.id))

            otp_entry.delete()  # Delete OTP after successful verification
            return Response({'message': 'OTP verified successfully.', 'uuidb64': uuidb64}, status=200)

        except Exception as e:
            return Response({'error': f'An error occurred: {str(e)}'}, status=500)

from rest_framework import viewsets, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.db.models import Q
from api.models import Event
from api.serializer import EventSerializer

class EventViewSet(viewsets.ModelViewSet):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only return events the user is allowed to see
        user = self.request.user
        return Event.objects.filter(
            Q(send_to_all=True) |  # Events sent to all users
            Q(users=user) |  # Events explicitly shared with the user
            Q(groups__in=user.groups.all()) |  # Events shared with the user's groups
            Q(created_by=user)  # Events created by the user
        ).distinct()

    def perform_create(self, serializer):
        # Automatically set the creator of the event to the logged-in user
        serializer.save(created_by=self.request.user)

class CourseLecturesAPIView(generics.ListAPIView):
    serializer_class = LectureSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        return Lecture.objects.filter(course_id=course_id).order_by('order')


class LectureDetailAPIView(generics.RetrieveAPIView):
    serializer_class = LectureSerializer
    permission_classes = [IsAuthenticated]
    queryset = Lecture.objects.all()
    lookup_field = 'id'

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Assignment, AssignmentFile, AssignmentQuestion, AssignmentSubmission, AssignmentSubmissionFile, AssignmentTestLog, Certificate, Course, Question_Answer_Message, QuestionOption, Quiz, QuizQuestion, UserActivity, VideoProgress, StudentProgress, QuizSubmission
from .serializer import AssignmentListSerializer, AssignmentSerializer, AssignmentSubmissionSerializer, AssignmentTestLogSerializer, CourseSerializer, QuizQuestionSerializer, QuizSerializer, VideoProgressSerializer, QuizSubmissionSerializer
import requests

class UnboughtCoursesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user_id = kwargs.get("user_id")
        #print(f"DEBUG: Fetching unbought courses for user_id: {user_id}")

        # Fetch all available courses
        try:
            all_courses = Course.objects.all()
            #print(f"DEBUG: Total courses available: {all_courses.count()}")
        except Exception as e:
            #print(f"ERROR: Failed to fetch all courses: {str(e)}")
            return Response({"error": "Failed to fetch all courses"}, status=500)

        # Fetch the student's courses directly from the database instead of making an API call
        try:
            # Get user
            user = get_object_or_404(User, id=user_id)
            
            # Get the enrolled courses directly from the database
            enrolled_courses = EnrolledCourse.objects.filter(user=user)
            # Fix: remove the float(True) which is causing the type error
            enrolled_course_ids = enrolled_courses.values_list('course__id', flat=True)
            
            print(f"DEBUG: Enrolled course IDs: {list(enrolled_course_ids)}")
        except Exception as e:
            print(f"ERROR: Failed to fetch student's courses: {str(e)}")
            return Response({"error": "Failed to fetch student's courses"}, status=500)

        # Filter out courses the student already has
        try:
            unbought_courses = all_courses.exclude(id__in=enrolled_course_ids)
            print(f"DEBUG: Unbought courses count: {unbought_courses.count()}")
        except Exception as e:
            print(f"ERROR: Failed to filter unbought courses: {str(e)}")
            return Response({"error": "Failed to filter unbought courses"}, status=500)

        # Serialize the unbought courses
        try:
            serializer = CourseSerializer(unbought_courses, many=True)
            print(f"DEBUG: Serialized unbought courses: {serializer.data}")
            return Response(serializer.data)
        except Exception as e:
            print(f"ERROR: Failed to serialize unbought courses: {str(e)}")
            return Response({"error": "Failed to serialize unbought courses"}, status=500)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Subscription, SubscriptionPackage
from api.serializer import SubscriptionSerializer, SubscriptionPackageSerializer

class SubscriptionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription = Subscription.objects.filter(user=request.user).first()
        if not subscription:
            return Response({"error": "No subscription found."}, status=404)
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)
    def post(self, request):
        data = request.data
        subscription, created = Subscription.objects.get_or_create(user=request.user)

        subscription.is_active = data.get("is_active", subscription.is_active)

        package_id = data.get("package")
        if package_id:
            subscription.package = SubscriptionPackage.objects.get(id=package_id)

        subscription.save()
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data, status=201)
        
    def delete(self, request):
        """Cancel a subscription"""
        try:
            subscription = Subscription.objects.filter(user=request.user).first()
            
            if not subscription:
                return Response({"error": "No active subscription found"}, status=404)
                
            # Set auto_renew to False instead of deleting
            subscription.auto_renew = False
            subscription.save()
            
            # Send cancellation confirmation email
            send_subscription_email(
                request.user,
                'Subscription Cancellation Confirmation',
                'Your subscription has been canceled and will not renew',
                'subscription_canceled'
            )
            
            return Response({
                "message": "Subscription canceled successfully. Your access will remain until the current period ends."
            }, status=200)
            
        except Exception as e:
            return Response({"error": f"Error canceling subscription: {str(e)}"}, status=500)

class SubscriptionPackageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        packages = SubscriptionPackage.objects.filter(is_active=True)
        serializer = SubscriptionPackageSerializer(packages, many=True)
        return Response(serializer.data)

class LandingPageSubscriptionPackageAPIView(APIView):
    """API view to get subscription packages for the landing page without authentication"""
    permission_classes = [AllowAny]

    def get(self, request):
        """Get all active subscription packages for public display"""
        try:
            packages = SubscriptionPackage.objects.filter(is_active=True)
            serializer = SubscriptionPackageSerializer(packages, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error fetching subscription packages for landing page: {str(e)}")
            return Response({"error": "Unable to fetch subscription packages"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from api.models import Subscription, UserLibrary, Course
from api.serializer import CourseSerializer

class AddSubscriptionCoursesToLibraryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            course_id = request.data.get('course_id')
            
            print(f"DEBUG - Adding course to library - User: {user.id}, Course ID: {course_id}")
            
            # First check if the user has an active subscription
            subscription = Subscription.objects.filter(user=user, is_active=True).first()
            
            if not subscription:
                print(f"DEBUG - No active subscription found for user {user.id}")
                return Response({"error": "No active subscription found."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Find the specific course
            try:
                course = Course.objects.get(id=course_id)
                print(f"DEBUG - Found course: {course.id} - {course.title}")
            except Course.DoesNotExist:
                print(f"DEBUG - Course not found with ID: {course_id}")
                return Response({"error": f"Course with ID {course_id} not found."}, status=status.HTTP_404_NOT_FOUND)
            
            # Check if the course is included in the subscription
            if subscription.include_all_courses:
                print("DEBUG - Subscription includes all courses")
                course_included = True
            else:
                course_included = subscription.active_courses.filter(id=course_id).exists()
                print(f"DEBUG - Course included in subscription: {course_included}")
            
            if not course_included:
                return Response({"error": "This course is not included in your subscription."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if the course is already in the user's library (using EnrolledCourse model)
            already_enrolled = EnrolledCourse.objects.filter(user=user, course=course).exists()
            
            if already_enrolled:
                print(f"DEBUG - User {user.id} already enrolled in course {course_id}")
                return Response({"message": "You are already enrolled in this course."}, status=status.HTTP_200_OK)
            
            # Create a fake order item for the enrollment
            teacher = course.teacher
            
            # Create a placeholder order item (required by your EnrolledCourse model)
            placeholder_order = CartOrder.objects.create(
                student=user,
                payment_status="Paid",
                full_name=user.profile.full_name if hasattr(user, 'profile') else user.username
            )
            
            placeholder_order_item = CartOrderItem.objects.create(
                order=placeholder_order,
                course=course,
                teacher=teacher,
                price=0.00,  # Free through subscription
                total=0.00,
                initial_total=0.00
            )
            
            # Now create the enrollment
            enrolled_course = EnrolledCourse.objects.create(
                user=user,
                course=course,
                teacher=teacher,
                order_item=placeholder_order_item
            )
            
            print(f"DEBUG - Successfully enrolled user {user.id} in course {course_id}")
            
            # Return the course data in the expected format
            course_data = api_serializer.CourseSerializer(course).data
            
            return Response({
                "message": "Course successfully added to your library!",
                "courses": [course_data]  # Return as array to match existing code expecting courses[0]
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"ERROR in addToLibrary: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.conf import settings

import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from api.models import CartOrder, CartOrderItem, Course, Teacher

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_yoco_checkout(request):
    """
    Create a Yoco checkout session for course or subscription purchases.
    For subscriptions, include 'is_subscription': true and 'subscription_pkg_id' in the POST data.
    """
    try:
        data = request.data
        amount = data.get("amount")
        currency = data.get("currency", "ZAR")
        user = request.user

        # Detect if this is a subscription checkout
        is_subscription = data.get("is_subscription", False)
        subscription_pkg_id = data.get("subscription_pkg_id")
        metadata = data.get("metadata", {})
        metadata.update({
            "user_id": str(user.id),
            "email": user.email,
            "application": "BonjourClasse"
        })
        if is_subscription and subscription_pkg_id:
            metadata["subscription_pkg_id"] = str(subscription_pkg_id)
            metadata["productType"] = "subscription"

        frontend_url = settings.FRONTEND_SITE_URL.rstrip('/')
        order_oid = data.get("order_oid")
        success_url = data.get("successUrl") or f"{frontend_url}/student/courses?payment=success&order={order_oid}"
        cancel_url = data.get("cancelUrl") or f"{frontend_url}/payment-cancelled?order={order_oid}"
        failure_url = data.get("failureUrl") or f"{frontend_url}/payment-failed?order={order_oid}"

        webhook_url = getattr(settings, "YOCO_WEBHOOK_URL", None)
        if not webhook_url:
            webhook_url = f"{frontend_url}/api/v1/payment/yoco-webhook/"

        payload = {
            "amount": amount,
            "currency": currency,
            "successUrl": success_url,
            "cancelUrl": cancel_url,
            "failureUrl": failure_url,
            "metadata": metadata,
            "lineItems": data.get("lineItems", []),
            "webhookUrl": webhook_url,
        }

        print("Payload being sent to Yoco API:", payload)

        headers = {
            "Authorization": f"Bearer {settings.YOCO_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            "https://payments.yoco.com/api/checkouts",
            json=payload,
            headers=headers,
            verify=True
        )

        print("Response from Yoco API:", response.status_code)
        print("Response content:", response.text)

        if response.status_code == 200:
            yoco_response = response.json()
            # If this is a subscription, create a PendingSubscription record
            if is_subscription and subscription_pkg_id:
                api_models.PendingSubscription.objects.create(
                    checkout_id=yoco_response.get("id"),
                    user=user,
                    package=SubscriptionPackage.objects.get(id=subscription_pkg_id),
                    amount=amount
                )
            return Response(yoco_response, status=200)
        else:
            error_message = response.json() if response.content else "No content"
            return Response(
                {"error": f"Payment gateway error: {response.status_code}", "details": error_message},
                status=500
            )

    except Exception as e:
        print(f"ERROR in create_yoco_checkout: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({"error": "Failed to create checkout session", "details": str(e)}, status=500)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    try:
        data = request.data
        course_id = data.get("course_id")
        user = request.user

        # Fetch the course
        course = Course.objects.get(id=course_id)

        # Create or update the CartOrder
        cart_order, created = CartOrder.objects.get_or_create(
            student=user,
            payment_status="Processing",
            defaults={
                "sub_total": 0.00,
                "total": 0.00,
                "initial_total": 0.00,
            },
        )

        # Check if the item already exists in the CartOrder
        if CartOrderItem.objects.filter(order=cart_order, course=course).exists():
            return Response({"message": "Item already in cart"}, status=400)

        # Add the item to the CartOrder
        CartOrderItem.objects.create(
            order=cart_order,
            course=course,
            teacher=course.teacher,
            price=course.price,
            total=course.price,
            initial_total=course.price,
        )

        # Update the CartOrder totals
        cart_order.sub_total += course.price
        cart_order.total += course.price
        cart_order.initial_total += course.price
        cart_order.save()

        return Response({"message": "Item added to cart", "oid": cart_order.oid}, status=200)

    except Course.DoesNotExist:
        return Response({"error": "Course not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.conf import settings
import json
import hmac
import hashlib
import traceback
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from api.models import CartOrder, EnrolledCourse, Cart, Notification
from django.db import transaction

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def yoco_webhook_handler(request):
    """
    Handles webhook events from Yoco payment gateway.
    """
    print("===== WEBHOOK RECEIVED =====")
    print(f"Headers: {dict(request.headers)}")
    try:
        raw_payload = request.body.decode('utf-8')
        print(f"Payload sample: {raw_payload[:500]}{'...' if len(raw_payload) > 500 else ''}")

        event_data = json.loads(raw_payload)
        payment_data = event_data.get('payload', event_data)
        metadata = payment_data.get('metadata', {})

        # Detect if this is a subscription payment
        subscription_pkg_id = metadata.get("subscription_pkg_id")
        product_type = metadata.get("productType")

        if subscription_pkg_id and product_type == "subscription":
            print("Processing subscription payment webhook")
            return process_subscription_payment(payment_data, metadata)
        else:
            print("Not a subscription payment, skipping subscription logic.")
            return Response({"status": "Not a subscription payment"}, status=200)

    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({"error": str(e)}, status=500)
def process_course_purchase(payment_data, metadata):
    """
    Process a course purchase payment from the webhook
    """
    try:
        payment_id = payment_data.get('id')
        order_oid = metadata.get('order_oid')
        
        print(f"Processing course purchase - Payment ID: {payment_id}, Order OID: {order_oid}")
        
        # If the order_oid is missing, try extracting checkout ID
        if not order_oid:
            checkout_id = metadata.get('checkoutId')
            print(f"No direct order_oid, using checkout_id: {checkout_id}")
            
            # Try to find the order based on checkout ID
            if checkout_id:
                order = CartOrder.objects.filter(yoco_payment_id=checkout_id).first()
                if order:
                    order_oid = order.oid
                    print(f"Found order with checkout ID: {checkout_id}, order_oid: {order_oid}")
        
        if not order_oid:
            print("No order_oid found in payment metadata")
            return HttpResponse("Missing order_oid in metadata", status=200)
        
        # Find the order
        try:
            order = CartOrder.objects.get(oid=order_oid)
        except CartOrder.DoesNotExist:
            print(f"Order with oid {order_oid} not found")
            return HttpResponse(f"Order with oid {order_oid} not found", status=200)
        
        # Update the order with payment details
        order.payment_status = "Paid"
        order.yoco_payment_id = payment_id
        order.save()
        
        print(f"Updated order status to Paid for {order_oid}")
        
        # Process all order items - create enrollments for each course
        order_items = CartOrderItem.objects.filter(order=order)
        for item in order_items:
            course = item.course
            teacher = item.teacher
            
            try:
                # Create enrollment for this course
                enrollment = EnrolledCourse.objects.create(
                    course=course,
                    user=order.student,
                    teacher=teacher,
                    order_item=item,
                    added_via_subscription=False
                )
                
                print(f"Created enrollment for user {order.student.id} in course {course.id}")
                
                # Create notification for student
                Notification.objects.create(
                    user=order.student,
                    order=order,
                    type="Course Purchase",
                    title="Course Purchase Successful",
                    content=f"You've been enrolled in {course.title}.",
                    url=f"/student/courses"
                )
                
                # Create notification for teacher
                if teacher:
                    Notification.objects.create(
                        user=teacher.user,
                        order=order,
                        type="Course Purchase",
                        title="New Enrollment",
                        content=f"A student has enrolled in your course {course.title}.",
                        url="/teacher/students"
                    )
                
            except Exception as e:
                print(f"Error creating enrollment for course {course.id}: {str(e)}")
        
        # Clean up cart items if any
        Cart.objects.filter(user=order.student).delete()
        
        print(f"Successfully processed payment for order {order_oid}")
        return HttpResponse("Payment processed successfully", status=200)
        
    except Exception as e:
        print(f"Error processing course purchase: {str(e)}")
        traceback.print_exc()
        return HttpResponse(f"Error: {str(e)}", status=500)
def verify_yoco_signature(payload, signature, timestamp):
    """
    Verify that the webhook was sent by Yoco by checking the signature.
    """
    if not signature:
        print("No signature provided in webhook request")
        return False
        
    try:
        # Get the webhook secret from settings, fallback to secret key if not available        webhook_secret = getattr(settings, 'YOCO_WEBHOOK_SECRET', None) or settings.YOCO_SECRET_KEY
        
        # print(f"Using webhook secret: {webhook_secret[:5]}...") # Print first few characters for debugging
        
        # Compute HMAC with SHA-256
        computed_signature = hmac.new(
              (getattr(settings, 'YOCO_WEBHOOK_SECRET', None) or settings.YOCO_SECRET_KEY).encode('utf-8'),
          payload,
            hashlib.sha256
        ).hexdigest()
        
        print(f"Received signature: {signature}")
        print(f"Computed signature: {computed_signature}")
        
        # Compare signatures using constant time comparison
        return hmac.compare_digest(computed_signature, signature)
    except Exception as e:
        print(f"Signature verification error: {str(e)}")
        traceback.print_exc()
        return False

import base64

def verify_yoco_signature(payload, signature, timestamp=None, request=None):
    """
    Verify that the webhook was sent by Yoco by checking the signature.
    Handles v1 signature format.
    """
    if not signature:
        print("No signature provided in webhook request")
        return False
        
    try:
        # Get the webhook secret from settings        webhook_secret = getattr(settings, 'YOCO_WEBHOOK_SECRET', None) or settings.YOCO_SECRET_KEY
        # print(f"Using webhook secret: {webhook_secret[:5]}...")  # Print first few characters for debugging
        
        # Check if this is a v1 signature format (v1,<signature>)
        if ',' in signature:
            parts = signature.split(',')
            if len(parts) != 2:
                print(f"Invalid signature format: {signature}")
                return False
            
            version, sig_value = parts
            print(f"Signature version: {version}, sig_value: {sig_value}")
            
            # Decode the signature value from base64
            sig_value = base64.b64decode(sig_value)
            
            # Compute HMAC with SHA-256
            computed_signature = hmac.new(
                  (getattr(settings, 'YOCO_WEBHOOK_SECRET', None) or settings.YOCO_SECRET_KEY).encode('utf-8'),
              payload,
                hashlib.sha256
            ).digest()
            
            # Compare signatures using constant time comparison
            return hmac.compare_digest(computed_signature, sig_value)
        
        # Fallback to default signature verification
        return verify_yoco_signature(payload, signature, request=request)
    except Exception as e:
        print(f"Signature verification error: {str(e)}")
        traceback.print.exc()
        return False

import base64
import hmac
import hashlib

def verify_yoco_signature(payload, signature, timestamp=None, request=None):
    """
    Verify that the webhook was sent by Yoco by checking the signature.
    Handles v1 signature format with proper concatenation.
    """
    if not signature:
        print("No signature provided in webhook request")
        return False
        
    try:        # Get the webhook secret from settings
        webhook_secret = getattr(settings, 'YOCO_WEBHOOK_SECRET', None) or settings.YOCO_SECRET_KEY
        
        # Remove 'whsec_' prefix if present
        if webhook_secret.startswith('whsec_'):
            webhook_secret = webhook_secret[6:]
        
        # print(f"Using webhook secret: {webhook_secret[:5]}...")  # Print first few characters for debugging
          # Check if this is a v1 signature format (v1,<signature>)
        if ',' in signature:
            parts = signature.split(',')
            if len(parts) != 2:
                # print(f"Invalid signature format: {signature}")
                return False
            
            version, received_signature = parts
            webhook_id = request.headers.get('Webhook-Id') if request else None
            
            # print(f"Webhook ID: {webhook_id}")
            # print(f"Timestamp: {timestamp}")
            
            # For v1 signatures, concatenate webhook-id, timestamp, and payload
            if version == 'v1' and timestamp and webhook_id:
                # The signed content is webhook_id + "." + timestamp + "." + payload
                signed_content = f"{webhook_id}.{timestamp}.{payload.decode('utf-8')}"
                
                # Compute HMAC with SHA-256
                computed_signature_raw = hmac.new(
                    webhook_secret.encode('utf-8'),
                    signed_content.encode('utf-8'),
                    hashlib.sha256
                ).digest()
                
                # Base64 encode the binary digest
                computed_signature = base64.b64encode(computed_signature_raw).decode('utf-8')
                
                print(f"Received signature: {received_signature}")
                print(f"Computed signature: {computed_signature}")
                
                # Compare signatures using constant time comparison
                return hmac.compare_digest(computed_signature, received_signature)
            
        # Fallback to original method if not v1 format
        computed_signature = hmac.new(
            webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        print(f"Fallback: using hex format")
        print(f"Received signature: {signature}")
        print(f"Computed signature: {computed_signature}")
        
        return hmac.compare_digest(computed_signature, signature)
        
    except Exception as e:
        print(f"Signature verification error: {str(e)}")
        traceback.print.exc()
        return False

# Add this code to the process_successful_payment function in the yoco_webhook_handler

def process_successful_payment(event_data):
    """
    Process a successful payment event from Yoco.
    This function enrolls the user in courses or activates subscriptions.
    """
    try:
        # Extract payment details from the webhook payload
        print("Processing successful payment...")
        payment_id = event_data.get('id')
        print(f"Payment ID: {payment_id}")
        
        # Extract metadata
        metadata = event_data.get('metadata', {})
        if not metadata and 'data' in event_data:
            metadata = event_data.get('data', {}).get('metadata', {})
        
        print(f"Metadata: {metadata}")
        
        # Check if this is a subscription payment
        subscription_pkg_id = metadata.get('subscription_pkg_id')
        if subscription_pkg_id:
            print(f"Processing subscription payment for package ID: {subscription_pkg_id}")
            return process_subscription_payment(event_data, metadata)
        
        # Continue with regular course enrollment logic
        order_oid = metadata.get('order_oid')
        
        # If the order_oid is missing, try extracting checkout ID
        if not order_oid:
            checkout_id = metadata.get('checkoutId')
            print(f"No direct order_oid, using checkout_id: {checkout_id}")
            
            # Try to find the order based on checkout ID
            if checkout_id:
                order = CartOrder.objects.filter(yoco_payment_id=checkout_id).first()
                if order:
                    order_oid = order.oid
                    print(f"Found order with checkout ID: {checkout_id}, order_oid: {order_oid}")
        
        # Rest of your existing function for course purchases
        # ...
        
    except Exception as e:
        print(f"Error processing payment: {str(e)}")
        traceback.print_exc()
        return HttpResponse(f"Error: {str(e)}", status=500)

def process_subscription_payment(event_data, metadata):
    """
    Process a subscription payment and activate/renew the subscription for the user.
    If the subscription is expired for more than 7 days, delete it and create a new one.
    Otherwise, extend the valid_until by the package duration (from the expiry date, not now).
    """
    from datetime import timedelta
    from django.utils import timezone
    from api.models import Subscription, SubscriptionPackage, User, Notification

    try:
        payment_id = event_data.get('id')
        user_id = metadata.get('user_id')
        subscription_pkg_id = metadata.get('subscription_pkg_id')

        if not user_id or not subscription_pkg_id:
            print("Missing user_id or subscription_pkg_id in metadata")
            return HttpResponse("Missing required metadata", status=200)

        user = User.objects.get(id=user_id)
        package = SubscriptionPackage.objects.get(id=subscription_pkg_id)

        subscription = Subscription.objects.filter(user=user).first()
        now_time = timezone.now()
        duration_days = getattr(package, "duration", 30)

        # If subscription exists and is expired for more than 7 days, delete it
        if subscription and subscription.valid_until and subscription.valid_until < now_time - timedelta(days=7):
            print(f"Subscription for user {user_id} expired more than 7 days ago. Deleting...")
            subscription.delete()
            subscription = None

        # --- FIX: Use calendar date for expiry check ---
        valid_until_date = subscription.valid_until.date() if subscription and subscription.valid_until else None
        now_date = now_time.date()

        # Calculate new valid_until
        if subscription and subscription.valid_until and valid_until_date >= now_date:
            # Extend from current valid_until (even if expires today)
            new_valid_until = subscription.valid_until + timedelta(days=duration_days)
        else:
            # New or expired before today, start from now
            new_valid_until = now_time + timedelta(days=duration_days)
        print(f"[SUBSCRIPTION RENEWAL] Renewal granted on: {now_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[SUBSCRIPTION RENEWAL] New expiry date (after adding {duration_days} days): {new_valid_until.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[SUBSCRIPTION RENEWAL] Day after expiry: {(new_valid_until + timedelta(days=1)).strftime('%Y-%m-%d')}")
        # Create or update subscription
        subscription, created = Subscription.objects.update_or_create(
            user=user,
            defaults={
                'package': package,
                'is_active': True,
                'valid_until': new_valid_until,
                'auto_renew': True,
                'include_all_courses': package.include_all_courses
            }
        )

        print(f"Subscription {'created' if created else 'updated'} for user {user_id}")

        # Send confirmation email (optional)
        try:
            send_subscription_email(
                user,
                'Subscription Confirmation',
                f'Your {package.name} subscription is now active',
                'subscription_activated'
            )
        except Exception as e:
            print(f"Failed to send subscription email: {e}")

        # Create notification for the user
        Notification.objects.create(
            user=user,
            type="Subscription Activated",
            title="Subscription Activated",
            content=f"Your {package.name} subscription is now active until {new_valid_until.strftime('%B %d, %Y')}.",
            url="/student/profile?tab=subscriptions"
        )

        print(f"Successfully processed subscription payment for user {user_id}")
        return HttpResponse("Subscription payment processed successfully", status=200)

    except User.DoesNotExist:
        print(f"User with ID {user_id} not found")
        return HttpResponse("User not found", status=200)
    except SubscriptionPackage.DoesNotExist:
        print(f"Subscription package with ID {subscription_pkg_id} not found")
        return HttpResponse("Subscription package not found", status=200)
    except Exception as e:
        print(f"Error processing subscription payment: {str(e)}")
        import traceback
        traceback.print_exc()
        return HttpResponse(f"Error: {str(e)}", status=500)

def process_failed_payment(event_data):
    """
    Process a failed payment event from Yoco.
    """
    try:
        # Extract payment details
        payment_id = event_data.get('id')
        metadata = event_data.get('metadata', {})
        order_oid = metadata.get('order_oid')
        
        if not order_oid:
            print("No order_oid found in payment metadata")
            return HttpResponse("Missing order_oid in metadata", status=200)
        
        print(f"Processing failed payment for order: {order_oid}")
        
        # Find the order
        try:
            order = CartOrder.objects.get(oid=order_oid)
        except CartOrder.DoesNotExist:
            print(f"Order with oid {order_oid} not found")
            return HttpResponse("Order not found", status=200)
            
        # Update the order with payment details
        order.payment_status = "Failed"
        order.yoco_payment_id = payment_id
        order.save()
        
        print(f"Updated order status to Failed for {order_oid}")
        
        # Create notification for student
        if order.student:
            Notification.objects.create(
                user=order.student, 
                order=order, 
                type="Payment Failed"
            )
            print(f"Created payment failed notification for student {order.student.id}")
        
        print(f"Successfully processed failed payment for order {order_oid}")
        return HttpResponse("Failed payment processed", status=200)
        
    except Exception as e:
        print(f"Error processing failed payment: {str(e)}")
        traceback.print_exc()
        return HttpResponse(f"Error: {str(e)}", status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def test_webhook_setup(request):
    """
    Test that the webhook configuration is working by checking:
    1. The webhook URL is accessible
    2. The signature verification works
    """
    # Generate a test payload
    test_payload = json.dumps({"test": True}).encode('utf-8')
    
    # Get the webhook secret from settings, fallback to secret key if not available
    webhook_secret = getattr(settings, 'YOCO_WEBHOOK_SECRET', None) or settings.YOCO_SECRET_KEY
    
    # Generate a test signature using your webhook secret
    test_signature = hmac.new(
        webhook_secret.encode('utf-8'),
        test_payload,
        hashlib.sha256
    ).hexdigest()
    
    # Verify the signature works
    is_valid = verify_yoco_signature(test_payload, test_signature)
    
    # Build the webhook URL
    protocol = "https" if request.is_secure() else "http"
    webhook_url = f"{protocol}://{request.get_host()}/api/v1/payment/yoco-webhook/"
    
    return Response({
        "webhook_url": webhook_url,
        "signature_verification_works": is_valid,
        "configuration_valid": is_valid,
        "webhook_secret_exists": bool(getattr(settings, 'YOCO_WEBHOOK_SECRET', None)),
        "test_signature": test_signature[:10] + "..." # Show part of signature for debugging
    })

@api_view(['POST'])
@permission_classes([AllowAny])
@csrf_exempt
def test_webhook_setup(request):
    """
    Test endpoint for Yoco webhook validation
    """
    try:
        print("===== TEST WEBHOOK RECEIVED =====")
        print(f"Headers: {dict(request.headers)}")
        
        # Get the webhook payload
        payload = request.body
        raw_payload = request.body.decode('utf-8')
        
        # Extract headers needed for verification
        signature = request.headers.get('Webhook-Signature')
        timestamp = request.headers.get('Webhook-Timestamp')
        webhook_id = request.headers.get('Webhook-Id')
        
        # Log everything for debugging
        print(f"Raw payload: {raw_payload}")
        print(f"Signature: {signature}")
        print(f"Timestamp: {timestamp}")
        print(f"Webhook ID: {webhook_id}")
        
        # Always return success for testing
        return HttpResponse("Webhook test received successfully", status=200)
    except Exception as e:
        print(f"Error in test webhook: {str(e)}")
        traceback.print_exc()
        return HttpResponse(f"Error: {str(e)}", status=500)
@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """Track when a user logs in successfully"""
    try:
        UserActivity.objects.create(
            user=user,
            user_type='user',  # Make sure this matches your model's choices
            activity_type='login',
            details={
                'ip_address': get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            }
        )
    except Exception as e:
        print(f"Error tracking login: {str(e)}")
        
def get_client_ip(request):
    """Get the client's IP address from the request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
import requests
from django.conf import settings

def register_webhook_with_yoco(ngrok_url):
    """
    Register a webhook with Yoco API using your ngrok URL
    """
    webhook_url = f"https://{ngrok_url}/api/v1/payment/yoco-webhook/"
    
    headers = {
        "Authorization": f"Bearer {settings.YOCO_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "url": webhook_url,
        "events": ["payment.succeeded"],
        "description": "Bonjour Classe payment webhook (development)"
    }
    
    response = requests.post(
        "https://payments.yoco.com/api/webhooks",
        headers=headers,
        json=payload
    )
    
    if response.status_code in [200, 201]:
        print(f"Webhook registered successfully: {webhook_url}")
        print(f"Response: {response.json()}")
        return response.json()
    else:
        print(f"Failed to register webhook: {response.status_code}")
        print(f"Response: {response.text}")
        return None

class CourseResourceListCreateAPIView(APIView):
    """
    API view for listing and creating course resources
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]
    
    def get(self, request, course_id):
        """
        Get all resources for a specific course
        """
        try:
            course = Course.objects.get(id=course_id)
            
            # For teachers - allow access to own course resources
            if request.user.user_type == 'teacher' and course.teacher != request.user:
                return Response({"error": "You don't have permission to access these resources"}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            # For students - check if enrolled
            if request.user.user_type == 'student':
                if not EnrolledCourse.objects.filter(user=request.user, course=course).exists():
                    return Response({"error": "You must be enrolled in this course to access resources"}, 
                                   status=status.HTTP_403_FORBIDDEN)
            
            resources = CourseResource.objects.filter(course=course)
            serializer = api_serializer.CourseResourceSerializer(resources, many=True, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, course_id):
        """
        Create a new course resource (teachers only)
        """
        try:
            course = Course.objects.get(id=course_id)
            
            # Only the teacher who owns the course can add resources
            if request.user.user_type != 'teacher' or course.teacher != request.user:
                return Response({"error": "You don't have permission to add resources to this course"}, 
                               status=status.HTTP_403_FORBIDDEN)
            
            # Create serializer with course ID
            data = request.data.copy()
            data['course'] = course.id
            
            # Handle lecture ID if provided
            lecture_id = data.get('lecture')
            if (lecture_id):
                try:
                    lecture = Lecture.objects.get(id=lecture_id, course=course)
                    data['lecture'] = lecture.id
                except Lecture.DoesNotExist:
                    return Response({"error": "Lecture not found in this course"}, 
                                   status=status.HTTP_404_NOT_FOUND)
            
            serializer = api_serializer.CourseResourceSerializer(data=data, context={"request": request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CourseResourceDetailAPIView(APIView):
    """
    API view for retrieving, updating and deleting course resources.
    Only teachers who own the course can edit/delete.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def get_resource(self, resource_id, user):
        try:
            resource = CourseResource.objects.get(id=resource_id)
            user_type = getattr(user, 'user_type', None)
            # Only allow teachers who own the course
            if user_type == 'teacher':
                if not hasattr(user, 'teacher') or resource.course.teacher != user.teacher:
                     raise PermissionDenied("You don't have permission to access this resource")
            # Students can only view if enrolled
            elif user_type == 'student':
                if not EnrolledCourse.objects.filter(user=user, course=resource.course).exists():
                    raise PermissionDenied("You must be enrolled in this course to access resources")
            return resource
        except CourseResource.DoesNotExist:
            raise Http404("Resource not found")

    def get(self, request, resource_id):
        try:
            resource = self.get_resource(resource_id, request.user)
            serializer = api_serializer.CourseResourceSerializer(resource, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request, resource_id):
        try:
            resource = self.get_resource(resource_id, request.user)
            # Only allow teachers who own the course
            if request.user.user_type != 'teacher' or not hasattr(request.user, 'teacher') or resource.course.teacher != request.user.teacher:
                return Response({"error": "You don't have permission to update this resource"}, status=status.HTTP_403_FORBIDDEN)
            serializer = api_serializer.CourseResourceSerializer(resource, data=request.data, partial=True, context={"request": request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, resource_id):
        try:
            resource = self.get_resource(resource_id, request.user)
            # Only allow teachers who own the course
            if request.user.user_type != 'teacher' or not hasattr(request.user, 'teacher') or resource.course.teacher != request.user.teacher:
                return Response({"error": "You don't have permission to delete this resource"}, status=status.HTTP_403_FORBIDDEN)
            resource.delete()
            return Response({"message": "Resource deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except PermissionDenied as e:
            return Response({"error": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Http404 as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LectureResourceListAPIView(APIView):
    """
    API view for listing resources for a specific lecture
    """
    permission_classes = [AllowAny]
    
    def get(self, request, course_id, lecture_id):
        """
        Get all resources for a specific lecture
        """
        try:
            # Import Q here to ensure it's available
            from django.db.models import Q
            
            course = Course.objects.get(id=course_id)
            lecture = Lecture.objects.get(id=lecture_id, course=course)
            
            # Check if the user is authenticated
            if request.user.is_authenticated:
                # For teachers - check if they own the course
                # Use a safer approach to check if user is a teacher
                teacher = getattr(request.user, 'teacher', None)
                if teacher and teacher == course.teacher:
                    # Teacher has access to their own course resources
                    pass
                # For students - check if enrolled
                elif not EnrolledCourse.objects.filter(user=request.user, course=course).exists():
                    return Response({"error": "You must be enrolled in this course to access resources"}, 
                                  status=status.HTTP_403_FORBIDDEN)
            else:
                # For unauthenticated users, deny access
                return Response({"error": "Authentication required to access course resources"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Get resources specific to this lecture or course-wide resources
            resources = CourseResource.objects.filter(
                Q(lecture=lecture) | 
                Q(course=course, lecture__isnull=True)
            ).order_by('title')
            
            serializer = api_serializer.CourseResourceSerializer(resources, many=True, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        except Lecture.DoesNotExist:
            return Response({"error": "Lecture not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            import traceback
            print(f"Error in LectureResourceListAPIView: {str(e)}")
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_resource(request, resource_id):
    """
    Download a resource file
    """
    try:
        # Get the resource
        resource = CourseResource.objects.get(id=resource_id)
        course = resource.course
        
        # Check permissions
        if request.user.user_type == 'teacher':
            if course.teacher != request.user.teacher:
                return Response({"error": "You don't have permission to download this resource"}, 
                               status=status.HTTP_403_FORBIDDEN)
        elif request.user.user_type == 'student':
            if not EnrolledCourse.objects.filter(user=request.user, course=course).exists():
                return Response({"error": "You must be enrolled in this course to download resources"}, 
                               status=status.HTTP_403_FORBIDDEN)
        
        # Prepare file for download
        file_path = resource.file.path
        filename = os.path.basename(file_path)
        
        # Set content disposition header to force download
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except CourseResource.DoesNotExist:
        return Response({"error": "Resource not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Add these API views to your existing views.py file

class StudentAssignmentsView(APIView):
    """List all assignments for a student"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        # Verify user has access
        if str(request.user.id) != str(user_id):
            print(f"User ID mismatch: {request.user.id} vs {user_id}")
            return Response(
                {"error": "You do not have permission to access these assignments"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Debug logging
        print(f"Finding assignments for user ID: {user_id}")
            
        # Find all courses the student is enrolled in
        enrolled_courses = EnrolledCourse.objects.filter(user=request.user).values_list('course', flat=True)
        print(f"Enrolled courses: {list(enrolled_courses)}")
        
        # Find all published assignments for those courses
        assignments = Assignment.objects.filter(
            course__in=enrolled_courses,
            status='published'
        ).select_related('course').order_by('due_date')
        
        print(f"Found {assignments.count()} assignments")
        # List each assignment
        # Check if assignment has any non-multiple choice questions
        # (This depends on how your assignment questions are structured)
        if hasattr(assignments, 'questions'):
            for question in assignments.questions.all():
                if question.type != 'multiple_choice':
                    has_non_mc_questions = True
                    break
        for assign in assignments:
            print(f"Assignment ID: {assign.id}, Title: {assign.title}, Course: {assign.course.title}")
        
        serializer = AssignmentSerializer(assignments, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
from rest_framework.decorators import api_view, permission_classes, renderer_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Teacher, Assignment
  
class TeacherAssignmentView(APIView):
    """View for teachers to create and manage assignments"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, assignment_id=None):
        # Get a specific assignment or list all assignments
        try:
            teacher = Teacher.objects.get(user=request.user)
            
            if assignment_id:
                # Get a specific assignment
                assignment = get_object_or_404(Assignment, id=assignment_id, teacher=teacher)
                serializer = api_serializer.AssignmentDetailSerializer(assignment, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # Get all assignments for this teacher
                assignments = Assignment.objects.filter(teacher=teacher).order_by('-created_at')
                serializer = api_serializer.AssignmentListSerializer(assignments, many=True, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
                
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher profile not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request, assignment_id=None):
        try:
            # Extract data from request
            title = request.data.get('title')
            description = request.data.get('description', '')  # Optional with default empty string
            course_id = request.data.get('course_id')
            due_date = request.data.get('due_date')
            has_test_mode = request.data.get('has_test_mode', False)
            time_limit_minutes = request.data.get('time_limit_minutes')
            test_content = request.data.get('test_content', '')
            status = request.data.get('status', 'draft')
            
            # Get questions data
            questions_data = request.data.get('questions', [])
            
            # DEBUG: Print questions data to troubleshoot
            print(f"Received questions data: {questions_data}")
            
            # Automatically calculate total points from questions
            total_points = 0
            for question in questions_data:
                try:
                    # Get point value from each question, default to 1 if not provided
                    question_points = int(question.get('points', 1))
                    total_points += question_points
                except (ValueError, TypeError):
                    # If points can't be converted to int, default to 1 point
                    total_points += 1
            
            # Ensure minimum value is 1
            if total_points < 1:
                total_points = 1
                
            # DEBUG: Print calculated points
            print(f"Calculated total points: {total_points}")
            
            # Validate required fields
            if not title:
                return Response({"error": "Title is required"}, status=status.HTTP_400_BAD_REQUEST)
                
            if not course_id:
                return Response({"error": "Course is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get teacher instance
            try:
                teacher = Teacher.objects.get(user=request.user)
            except Teacher.DoesNotExist:
                return Response({"error": "Teacher profile not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Get course instance
            try:
                course = Course.objects.get(id=course_id)
                
                # Check if teacher is authorized for this course
                if course.teacher.id != teacher.id:
                    return Response(
                        {"error": "You are not authorized to create assignments for this course"}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Course.DoesNotExist:
                return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Create or update assignment
            if assignment_id:
                # Update existing assignment
                try:
                    assignment = Assignment.objects.get(id=assignment_id, teacher=teacher)
                except Assignment.DoesNotExist:
                    return Response({"error": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
                
                assignment.title = title
                assignment.description = description
                assignment.due_date = due_date
                assignment.status = status
                assignment.has_test_mode = has_test_mode
                assignment.time_limit_minutes = time_limit_minutes
                assignment.test_content = test_content
                assignment.points = total_points  # Set the calculated total points
                assignment.save()
            else:
                # Create new assignment
                assignment = Assignment.objects.create(
                    title=title,
                    description=description,
                    course=course,
                    teacher=teacher,
                    due_date=due_date,
                    status=status,
                    has_test_mode=has_test_mode,
                    time_limit_minutes=time_limit_minutes,
                    test_content=test_content,
                    points=total_points  # Set the calculated total points
                )
            
            # Handle questions
            # First, delete existing questions if updating
            if assignment_id:
                AssignmentQuestion.objects.filter(assignment=assignment).delete()
            
            # Create new questions
            for idx, q_data in enumerate(questions_data):
                question = AssignmentQuestion.objects.create(
                    assignment=assignment,
                    title=q_data.get('title', ''),
                    description=q_data.get('description', ''),
                    type=q_data.get('type', 'text'),
                    required=q_data.get('required', True),
                    points=q_data.get('points', 1),  # Default to 1 point
                    order=idx
                )
                
                # Handle options for multiple choice questions
                if q_data.get('type') == 'multiple_choice' and 'options' in q_data:
                    options = q_data.get('options', [])
                    for opt_idx, opt_data in enumerate(options):
                        QuestionOption.objects.create(
                            question=question,
                            text=opt_data.get('text', ''),
                            is_correct=opt_data.get('is_correct', False),
                            order=opt_idx
                        )
            
            # Verify the points were saved correctly
            assignment.refresh_from_db()
            
            return Response({
                "success": True, 
                "assignment_id": assignment.id,
                "points": assignment.points,
                "message": "Assignment saved successfully with " + str(assignment.points) + " points"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Log the error for debugging
            print(f"Error creating/updating assignment: {str(e)}")
            return Response(
                {"error": f"Error saving assignment: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, assignment_id):
        try:
            teacher = Teacher.objects.get(user=request.user)
            assignment = get_object_or_404(Assignment, id=assignment_id, teacher=teacher)
            assignment.delete()
            return Response({"success": True, "message": "Assignment deleted successfully"}, status=status.HTTP_200_OK)
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher profile not found"}, status=status.HTTP_404_NOT_FOUND)
        except Assignment.DoesNotExist:
            return Response({"error": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AssignmentSubmissionView(APIView):
    """Handle student submissions for assignments"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, assignment_id=None):
        """Return the current user's submission for a specific assignment"""
        if not assignment_id:
            return Response({"error": "Assignment ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        assignment = get_object_or_404(Assignment, id=assignment_id)
        submission = AssignmentSubmission.objects.filter(assignment=assignment, student=request.user).first()
        if not submission:
            return Response({}, status=status.HTTP_200_OK)
        serializer = AssignmentSubmissionSerializer(submission, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        try:
            print("\n===== ASSIGNMENT SUBMISSION =====")
            print(f"User: {request.user.username} (ID: {request.user.id})")

            assignment_id = request.data.get('assignment_id')
            print(f"Assignment ID: {assignment_id}")

            if not assignment_id:
                return Response({"error": "Assignment ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            assignment = get_object_or_404(Assignment, id=assignment_id)
            print(f"Assignment: {assignment.title} (Course: {assignment.course.title})")

            # Parse answers
            answers = request.data.get('answers')
            if isinstance(answers, str):
                try:
                    answers = json.loads(answers)
                except Exception as e:
                    print(f"Error parsing answers JSON: {e}")
                    answers = {}
            if not isinstance(answers, dict):
                answers = {}

            print(f"Answers received: {answers}")

            # Handle secure_mode_used as boolean
            secure_mode_used = request.data.get('secure_mode_used', False)
            if isinstance(secure_mode_used, str):
                secure_mode_used = secure_mode_used.lower() in ("true", "1", "yes")

            # Find or create submission
            submission, created = AssignmentSubmission.objects.get_or_create(
                assignment=assignment,
                student=request.user,
                defaults={
                    "submission_text": request.data.get("submission_text", ""),
                    "secure_mode_used": secure_mode_used,
                    "fullscreen_warnings": int(request.data.get("fullscreen_warnings", 0)),
                    "tab_switch_warnings": int(request.data.get("tab_switch_warnings", 0)),
                    "answers": answers,
                    "submitted_at": timezone.now(),
                }
            )
            if not created:
                # Update existing submission
                submission.submission_text = request.data.get("submission_text", "")
                submission.secure_mode_used = secure_mode_used
                submission.fullscreen_warnings = int(request.data.get("fullscreen_warnings", 0))
                submission.tab_switch_warnings = int(request.data.get("tab_switch_warnings", 0))
                submission.answers = answers
                submission.submitted_at = timezone.now()
                submission.save()
                print("Submission updated.")
            else:
                print("Submission created.")

            print(f"Saved submission with ID: {submission.id}")

            serializer = AssignmentSubmissionSerializer(submission, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        except Exception as e:
            print(f"ERROR in AssignmentSubmissionView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error submitting assignment: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class TeacherSubmissionsView(APIView):
    """View for teachers to see all submissions for an assignment"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, assignment_id):
        """Get all submissions for an assignment"""
        try:
            teacher = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Only teachers can view all submissions"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        assignment = get_object_or_404(Assignment, id=assignment_id, teacher=teacher)
        submissions = AssignmentSubmission.objects.filter(assignment=assignment).order_by('submitted_at')
        serializer = AssignmentSubmissionSerializer(submissions, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
        
class GradeSubmissionView(APIView):
    """View for teachers to grade submissions"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, submission_id):
        """Grade a submission"""
        try:
            teacher = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Only teachers can grade submissions"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        submission = get_object_or_404(AssignmentSubmission, id=submission_id)
        
        # Verify the teacher owns the assignment
        if submission.assignment.teacher != teacher:
            return Response(
                {"error": "You can only grade submissions for your own assignments"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Update grade and feedback
        submission.grade = request.data.get('grade')
        submission.feedback = request.data.get('feedback')
        submission.status = 'graded'
        submission.save()
        
        serializer = AssignmentSubmissionSerializer(submission, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class AssignmentTestLogView(APIView):
    """Handle logs for secure test mode"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Create a new test log entry"""
        assignment_id = request.data.get('assignment_id')
        action = request.data.get('action')
        details = request.data.get('details')
        
        if not assignment_id or not action:
            return Response({"error": "Assignment ID and action are required"}, status=status.HTTP_400_BAD_REQUEST)
            
        assignment = get_object_or_404(Assignment, id=assignment_id)
        
        # Check if student is enrolled in the course
        if not EnrolledCourse.objects.filter(user=request.user, course=assignment.course).exists():
            return Response(
                {"error": "You must be enrolled in this course to use test mode"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        log = AssignmentTestLog.objects.create(
            assignment=assignment,
            student=request.user,
            action=action,
            details=details
        )
        
        serializer = AssignmentTestLogSerializer(log)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    def get(self, request, assignment_id):
        """Get test logs for a specific assignment (teachers only)"""
        try:
            teacher = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Only teachers can view test logs"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        assignment = get_object_or_404(Assignment, id=assignment_id, teacher=teacher)
        logs = AssignmentTestLog.objects.filter(assignment=assignment).order_by('-timestamp')
        serializer = AssignmentTestLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class AssignmentFileDeleteView(APIView):
    """Delete an assignment file"""
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, file_id):
        """Delete a file from an assignment"""
        try:
            teacher = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Only teachers can delete assignment files"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        file = get_object_or_404(AssignmentFile, id=file_id)
        
        # Verify the teacher owns the assignment
        if file.assignment.teacher != teacher:
            return Response(
                {"error": "You can only delete files from your own assignments"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Delete the file
        file.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Add this class to your views.py file (near the other assignment views)
class StudentAssignmentDetailView(APIView):
    """Get details for a specific assignment for a student"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, assignment_id):
        try:
            print("\n===== STUDENT VIEWING ASSIGNMENT =====")
            print(f"Student: {request.user.username} (ID: {request.user.id})")
            print(f"Assignment ID: {assignment_id}")
            
            # Get the assignment
            assignment = get_object_or_404(Assignment, id=assignment_id)
            print(f"Assignment: {assignment.title} (Course: {assignment.course.title})")
            
            # Check if student is enrolled in the course
            if not EnrolledCourse.objects.filter(
                    user=request.user, 
                    course=assignment.course
                ).exists():
                print(f"ACCESS DENIED: Student not enrolled in course {assignment.course.title}")
                return Response(
                    {"error": "You are not enrolled in this course"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Check if assignment is published or user is a teacher
            if assignment.status != 'published':
                try:
                    teacher = Teacher.objects.get(user=request.user)
                    if teacher != assignment.teacher:
                        print(f"ACCESS DENIED: Unpublished assignment, and user is not the assigned teacher")
                        return Response(
                            {"error": "You don't have permission to view this unpublished assignment"},
                            status=status.HTTP_403_FORBIDDEN
                        )
                except Teacher.DoesNotExist:
                    print(f"ACCESS DENIED: Assignment not published")
                    return Response(
                        {"error": "This assignment is not published"}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Get submission if it exists
            submission = None
            try:
                submission = AssignmentSubmission.objects.get(
                    assignment=assignment,
                    student=request.user
                )
                print(f"Previous submission found: ID {submission.id}, Status: {submission.status}")
                print(f"Submitted on: {submission.submitted_at}")
                if submission.grade:
                    print(f"Grade: {submission.grade}/{assignment.points}")
            except AssignmentSubmission.DoesNotExist:
                print("No previous submission found")
                pass
                
            # Serialize assignment with questions
            serializer = AssignmentSerializer(assignment, context={'request': request})
            data = serializer.data
            
            # Add submission data if it exists
            if submission:
                submission_serializer = AssignmentSubmissionSerializer(
                    submission, 
                    context={'request': request}
                )
                data['submission'] = submission_serializer.data
                
            # Log how many questions are in the assignment
            if assignment.questions.count() > 0:
                question_types = assignment.questions.values_list('type', flat=True)
                mc_count = sum(1 for t in question_types if t == 'multiple_choice')
                text_count = sum(1 for t in question_types if t == 'text')
                print(f"Assignment has {assignment.questions.count()} questions: {mc_count} multiple choice, {text_count} text")
                
            print("===== ASSIGNMENT VIEW COMPLETE =====\n")
                
            return Response(data, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(f"ERROR in StudentAssignmentDetailView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Error retrieving assignment: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class VideoProgressAPIView(APIView):
    """API view to get or update video progress"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, lecture_id):
        """Get the user's progress for a lecture"""
        lecture = get_object_or_404(Lecture, id=lecture_id)
        
        progress = VideoProgress.objects.filter(
            user=request.user,
            lecture_id=lecture_id
        ).first()
        
        if not progress:
            return Response({"current_time": 0, "duration": 0, "percentage_complete": 0, "completed": False})
            
        serializer = VideoProgressSerializer(progress)
        return Response(serializer.data)
        
    def post(self, request, lecture_id):
        """Update progress for a lecture"""
        try:
            lecture = get_object_or_404(Lecture, id=lecture_id)
            course = lecture.course
            
            # Get or create progress record
            progress, created = VideoProgress.objects.get_or_create(
                user=request.user,
                lecture=lecture,
                course=course
            )
            
            # Update progress data
            current_time = request.data.get('current_time', 0)
            duration = request.data.get('duration', 0)
            
            # Only update if we have valid values
            if duration > 0 and isinstance(current_time, (int, float)):
                progress.current_time = current_time
                progress.duration = duration
                progress.save()  # This will auto-calculate percentage and completed
            
            # Return the updated progress
            serializer = VideoProgressSerializer(progress)
            return Response(serializer.data)
            
        except Exception as e:
            print(f"Error updating progress: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CourseProgressAPIView(APIView):
    """API view to get overall course progress for the current user"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        """Get the current user's overall progress for a course"""
        course = get_object_or_404(Course, id=course_id)
        
        # Get user's enrollment status
        enrollment = EnrolledCourse.objects.filter(
            user=request.user,
            course=course
        ).first()
        
        if not enrollment:
            return Response(
                {"error": "You are not enrolled in this course"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get all lectures for this course
        lectures = Lecture.objects.filter(course=course)
        total_lectures = lectures.count()
        
        if total_lectures == 0:
            return Response({"progress": 0, "completed_lectures": 0, "total_lectures": 0})
            
        # Get progress for all lectures - only for the authenticated user
        progress_records = VideoProgress.objects.filter(
            user=request.user,
            course=course
        )
        
        completed_lectures = progress_records.filter(completed=True).count()
        
        # Calculate overall percentage
        overall_percentage = (completed_lectures / total_lectures) * 100 if total_lectures > 0 else 0
            
        return Response({
            "progress": round(overall_percentage),
            "completed_lectures": completed_lectures,
            "total_lectures": total_lectures,
            "lectures": [{
                'lecture_id': record.lecture.id,
                'title': record.lecture.title,
                'percentage_complete': record.percentage_complete,
                'completed': record.completed,
                'current_time': record.current_time
            } for record in progress_records]
        })

class CheckCourseAccessAPIView(APIView):
    """API view to check if a user has access to a course"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        user = request.user
        course = get_object_or_404(Course, id=course_id)
        
        # Check if user directly purchased this course
        direct_purchase = EnrolledCourse.objects.filter(
            user=user, 
            course=course, 
            added_via_subscription=False
        ).exists()
        
        # Check if added through subscription
        subscription_enrollment = EnrolledCourse.objects.filter(
            user=user,
            course=course,
            added_via_subscription=True
        ).first()
        
        subscription_active = False
        if subscription_enrollment and subscription_enrollment.subscription:
            subscription = subscription_enrollment.subscription
            subscription_active = subscription.is_active and (
                not subscription.valid_until or 
                subscription.valid_until > timezone.now()
            )
        
        access_status = {
            "has_access": direct_purchase or subscription_active,
            "direct_purchase": direct_purchase,
            "subscription_access": bool(subscription_enrollment),
            "subscription_active": subscription_active
        }
        
        return Response(access_status)

class StudentProgressView(APIView):
    """API view to get all course progress for a student"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        """Get all course progress for the specified user"""
        # Security check - only allow users to access their own progress
        if int(user_id) != request.user.id:
            return Response({"error": "You can only access your own progress data"}, 
                           status=status.HTTP_403_FORBIDDEN)
        
        try:
            # Get all courses the student is enrolled in
            enrolled_courses = EnrolledCourse.objects.filter(user=request.user)
            
            if not enrolled_courses:
                return Response([], status=status.HTTP_200_OK)
            
            # Get progress data for each course
            progress_data = []
            
            for enrollment in enrolled_courses:
                course = enrollment.course
                
                # Get all lectures for this course
                lectures = Lecture.objects.filter(course=course)
                total_lectures = lectures.count()
                
                if total_lectures == 0:
                    # Skip courses with no lectures or add with 0 progress
                    progress_data.append({
                        "course_id": course.id,
                        "title": course.title,
                        "progress": 0,
                        "completed_lectures": 0,
                        "total_lectures": 0,
                        "added_via_subscription": enrollment.added_via_subscription,
                        "image": request.build_absolute_uri(course.image.url) if course.image else None
                    })
                    continue
                
                # Get progress records for this course
                progress_records = VideoProgress.objects.filter(
                    user=request.user,
                    course=course
                )
                
                # Count completed lectures
                completed_lectures = progress_records.filter(completed=True).count()
                
                # Calculate overall percentage - properly handle division by zero
                if total_lectures > 0:
                    overall_percentage = int((completed_lectures / total_lectures) * 100)
                else:
                    overall_percentage = 0
                
                # Add course progress to response
                progress_data.append({
                    "course_id": course.id,
                    "title": course.title,
                    "progress": overall_percentage,
                    "completed_lectures": completed_lectures,
                    "total_lectures": total_lectures,
                    "added_via_subscription": enrollment.added_via_subscription,
                    "image": request.build_absolute_uri(course.image.url) if course.image else None
                })
            
            return Response(progress_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error fetching student progress: {str(e)}")
            import traceback
            traceback.print.exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
import tempfile
import subprocess
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.conf import settings

def serve_video(request, path):
    """
    Stream video with proper range request handling for seeking
    """
    # Replace backslashes with forward slashes for consistency
    path = path.replace('\\', '/')
    
    # Build full path to file
    full_path = os.path.join(settings.MEDIA_ROOT, path)
    
    # Force forward slashes in the full path
    full_path = full_path.replace('\\', '/')
    
    # Debugging
    print(f"Streaming video: {path}")
    print(f"Full path: {full_path}")
    
    # Check if file exists
    if not os.path.exists(full_path):
        return HttpResponse(f"File not found: {full_path}", status=404)
    
    # Rest of your streaming code...

def should_optimize_video(video_path):
    """Check if a video needs keyframe optimization for seeking"""
    # This is a heuristic - you might want to improve it
    # For now, we'll optimize all WebM files since they're often problematic
    return video_path.lower().endswith('.webm')

def get_or_create_optimized_video(original_path):
    """Get path to optimized version or create it if it doesn't exist"""
    # Create a unique name for the optimized version
    file_name = os.path.basename(original_path)
    base_name, ext = os.path.splitext(file_name)
    optimized_name = f"{base_name}_optimized{ext}"
    
    # Store optimized videos in a cache directory
    cache_dir = os.path.join(settings.MEDIA_ROOT, "video_cache")
    os.makedirs(cache_dir, exist_ok=True)
    
    optimized_path = os.path.join(cache_dir, optimized_name)
    
    # If optimized version already exists, return its path
    if os.path.exists(optimized_path):
        # Check if original is newer than optimized
        if os.path.getmtime(original_path) > os.path.getmtime(optimized_path):
            # Original has been modified, recreate optimized version
            pass
        else:
            # Optimized version is up-to-date
            return optimized_path
    
    # Create optimized version with more keyframes
    if original_path.lower().endswith('.webm'):
        # For WebM files
        subprocess.run([
            'ffmpeg', '-i', original_path,
            '-c:v', 'libvpx', 
            '-keyint_min', '15', 
            '-g', '15',
            '-b:v', '1M',
            '-c:a', 'copy',
            '-f', 'webm',
            '-y',  # Overwrite output if it exists
            optimized_path
        ], check=True)
    else:
        # For MP4 files
        subprocess.run([
            'ffmpeg', '-i', original_path,
            '-c:v', 'libx264', 
            '-preset', 'fast',
            '-keyint_min', '15', 
            '-g', '15',
            '-c:a', 'copy',
            '-movflags', '+faststart',
            '-y',  # Overwrite output if it exists
            optimized_path
        ], check=True)
    
    return optimized_path

def serve_optimized_video(request, video_path, range_match):
    """Serve a video file from the optimized path with range support"""
    file_size = os.path.getsize(video_path)
    
    # Parse range
    start = int(range_match.group(1))
    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
    
    # Validate range
    if start >= file_size:
        return HttpResponse(status=416)  # Range Not Satisfiable
        
    # Limit end to file size
    end = min(end, file_size - 1)
    
    # Calculate content length
    content_length = end - start + 1
    
    # Open file at the right position
    file = open(video_path, 'rb')
    file.seek(start)
    
    # Create response with the requested range of bytes
    response = HttpResponse(
        file.read(content_length),
        status=206,  # Partial Content
        content_type='video/webm' if video_path.endswith('.webm') else 'video/mp4'
    )
    
    # Set required headers for range requests
    response['Content-Length'] = str(content_length)
    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
    response['Accept-Ranges'] = 'bytes'
    
    return response

def get_video_metadata(request, lecture_id):
    """Get metadata about a video file including duration, size and streaming URL"""
    try:
        # Fetch the lecture
        lecture = Lecture.objects.get(id=lecture_id)
        
        # Get the video file path (assuming lecture.video stores the relative path)
        video_path = lecture.video.path if hasattr(lecture.video, 'path') else str(lecture.video)
        
        # If video_path is a URL not a file path, return it directly
        if (video_path.startswith('http')):
            return JsonResponse({
                'url': video_path,
                'supports_seeking': True,
                'mime_type': 'video/mp4',  # Default assumption
                'size': 0,  # Unknown size for external URLs
            })
        
        # Check if file exists
        if not os.path.exists(video_path):
            return JsonResponse({'error': 'Video file not found'}, status=404)
        
        # Get file size
        file_size = os.path.getsize(video_path)
        
        # Determine MIME type based on file extension
        mime_type, _ = mimetypes.guess_type(video_path)
        if not mime_type:
            if video_path.endswith('.webm'):
                mime_type = 'video/webm'
            elif video_path.endswith('.mp4'):
                mime_type = 'video/mp4'
            else:
                mime_type = 'application/octet-stream'
        
        # Create a streaming URL that will use our serve_video function
        # Extract the relative path from the full path
        rel_path = os.path.relpath(video_path, settings.MEDIA_ROOT)
        streaming_url = f"/api/stream-video/{rel_path}"
        
        # Return metadata
        return JsonResponse({
            'id': lecture_id,
            'title': lecture.title,
            'url': streaming_url,
            'supports_seeking': True,
            'size': file_size,
            'mime_type': mime_type,
        })
        
    except Lecture.DoesNotExist:
        return JsonResponse({'error': 'Lecture not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def stream_video(request, path):
    """Stream video with proper range request handling"""
    try:
        # Build full path to file
        full_path = os.path.join(settings.MEDIA_ROOT, path)
        
        # Check if file exists
        if not os.path.exists(full_path):
            return HttpResponse("File not found", status=404)
        
        # Get file size and mime type
        file_size = os.path.getsize(full_path)
        mime_type, _ = mimetypes.guess_type(full_path)
        if not mime_type:
            mime_type = 'application/octet-stream'
            
            # Try to guess based on extension
            if full_path.endswith('.webm'):
                mime_type = 'video/webm'
            elif full_path.endswith('.mp4'):
                mime_type = 'video/mp4'
        
        # Parse range header
        range_header = request.META.get('HTTP_RANGE', '')
        range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
        
        # Add debug logging
        print(f"Streaming video: {path}")
        print(f"MIME type: {mime_type}")
        print(f"Size: {file_size} bytes")
        print(f"Range header: {range_header}")
        
        if range_match:
            # Handle range request
            start = int(range_match.group(1))
            end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
            
            # Validate range
            if start >= file_size:
                print(f"Invalid range: start ({start}) >= file_size ({file_size})")
                response = HttpResponse(status=416)  # Requested Range Not Satisfiable
                response['Content-Range'] = f'bytes */{file_size}'
                return response
            
            # Limit end to file size
            end = min(end, file_size - 1)
            
            # Calculate content length
            content_length = end - start + 1
            
            # Read the specified range of bytes
            with open(full_path, 'rb') as f:
                f.seek(start)
                data = f.read(content_length)
            
            # Create response
            response = HttpResponse(data, status=206, content_type=mime_type)
            
            # Add necessary headers
            response['Content-Length'] = str(content_length)
            response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
            response['Accept-Ranges'] = 'bytes'
            
            print(f"Serving partial content: bytes {start}-{end}/{file_size}")
            return response
        else:
            # Serve entire file
            print(f"Serving entire file: {file_size} bytes")
            
            # For large files, use FileWrapper to stream in chunks
            chunk_size = 8192
            response = FileResponse(
                FileWrapper(open(full_path, 'rb'), chunk_size),
                content_type=mime_type
            )
            
            response['Content-Length'] = str(file_size)
            response['Accept-Ranges'] = 'bytes'
            return response
            
    except Exception as e:
        print(f"Error streaming video: {str(e)}")
        return HttpResponse(f"Error: {str(e)}", status=500)

from rest_framework import status, viewsets, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Conversation, Message, Notification
from .serializer import ConversationSerializer, MessageSerializer, NotificationSerializer

# Serializers (add these to serializer.py)
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
        if (last_msg):
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
            # For group conversations
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

class NotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'type', 'title', 'content', 'url', 'seen', 'date', 'sender_name']
        
    def get_sender_name(self, obj):
        if obj.sender:
            return obj.sender.get_full_name() or obj.sender.username
        return None

# List all conversations for the current user
class ConversationList(generics.ListCreateAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).distinct()
    
    def create(self, request, *args, **kwargs):
        participants = request.data.get('participants', [])
        # Ensure the current user is included
        if request.user.id not in participants and int(request.user.id) not in participants:
            participants.append(request.user.id)
            
        # Check if a conversation with these exact participants already exists
        user_participants = User.objects.filter(id__in=participants)
        
        # For direct messages (2 participants), check if conversation exists
        if len(participants) == 2:
            # Find conversations where both users participate
            other_user_id = next(id for id in participants if int(id) != request.user.id)
            other_user = User.objects.get(id=other_user_id)
            
            existing_conversations = Conversation.objects.filter(participants=request.user).filter(participants=other_user)
            
            # If exactly 2 participants, this would be a direct conversation
            if existing_conversations.exists():
                conversation = existing_conversations.first()
                serializer = self.get_serializer(conversation)
                return Response(serializer.data, status=status.HTTP_200_OK)
        
        # Create new conversation
        conversation = Conversation.objects.create()
        conversation.participants.set(user_participants)
        conversation.save()
        
        # If initial message is provided, create it
        initial_message = request.data.get('message')
        if initial_message:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                content=initial_message
            )
            
        serializer = self.get_serializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# Get specific conversation and its messages
class ConversationDetail(generics.RetrieveAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user)
        
    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()
        
        # Mark all messages in this conversation as read by the current user
        unread_messages = conversation.messages.exclude(read_by=request.user)
        for message in unread_messages:
            message.read_by.add(request.user)
        
        # Get messages for this conversation
        messages = conversation.messages.all()
        message_serializer = MessageSerializer(
            messages, 
            many=True,
            context={'request': request}
        )
        
        # Get conversation details
        conversation_serializer = self.get_serializer(conversation)
        
        return Response({
            'conversation': conversation_serializer.data,
            'messages': message_serializer.data
        })
# Send a new message
class MessageCreate(generics.CreateAPIView):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def create(self, request, *args, **kwargs):
        conversation_id = request.data.get('conversation_id')
        content = request.data.get('content', '')
        file = request.data.get('file')
        
        if not conversation_id:
            return Response(
                {"error": "Conversation ID is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Verify user has access to this conversation
        try:
            conversation = Conversation.objects.get(id=conversation_id, participants=request.user)
        except Conversation.DoesNotExist:
            return Response(
                {"error": "Conversation not found or you do not have access"}, 
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Create the message with attachment if provided
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            attachment=file
        )
        
        # Auto-mark as read by the sender
        message.read_by.add(request.user)
        
        # Update conversation timestamp
        conversation.updated_at = timezone.now()
        conversation.save()
        
        # Create notifications for other participants
        for participant in conversation.participants.exclude(id=request.user.id):
            Notification.objects.create(
                user=participant,
                sender=request.user,
                message=message,
                type="New Message",
                title=f"New message from {request.user.get_full_name() or request.user.username}",
                content=content[:50] + ("..." if len(content) > 50 else ""),
                url=f"/messages/{conversation.id}/"
            )
        
        serializer = self.get_serializer(message, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
# Get all notifications for the current user
class NotificationList(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-date')

# Mark notification as read
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    try:
        notification = Notification.objects.get(id=pk, user=request.user)
        notification.seen = True
        notification.save()
        return Response({'success': True})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

# Mark all notifications as read
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, seen=False).update(seen=True)
    return Response({'success': True})

# Teacher-specific view to get all student conversations
class TeacherStudentConversations(generics.ListAPIView):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Check if the user is a teacher
        try:
            teacher = Teacher.objects.get(user=user)
        except Teacher.DoesNotExist:
            return Conversation.objects.none()
            
        # Get all conversations where the teacher is a participant
        return Conversation.objects.filter(participants=user)

class StudentQuizListAPIView(generics.ListAPIView):
    """API view to list quizzes for a student"""
    serializer_class = QuizSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user_id = self.kwargs['user_id']
        
        # Check if the requesting user is authorized to see these quizzes
        if str(self.request.user.id) != str(user_id):
            return Quiz.objects.none()
            
        # Get all courses the student is enrolled in
        enrolled_courses = EnrolledCourse.objects.filter(user_id=user_id).values_list('course', flat=True)
        
        # Get all published quizzes for those courses
        quizzes = Quiz.objects.filter(
            course__in=enrolled_courses,
            status='published'
        ).order_by('title')  # Sort by name/title instead of due date
        
        return quizzes

class TeacherDashboardAPIView(APIView):
    """API view to get dashboard data for teacher using real student activity"""
    permission_classes = [IsAuthenticated]

    def get(self, request, teacher_id):
        try:
            teacher = get_object_or_404(Teacher, id=teacher_id)
            
            # Check if requesting user has permission
            if str(request.user.id) != str(teacher.user.id):
                return Response({"error": "You don't have permission to view this dashboard"},
                               status=status.HTTP_403_FORBIDDEN)
            
            # Get all courses taught by this teacher
            courses = Course.objects.filter(teacher=teacher)
            course_ids = list(courses.values_list('id', flat=True))
            
            today = timezone.now().date()
            months = [(today.month - i) % 12 or 12 for i in range(3)][::-1]
            monthly_submissions = [0, 0, 0]
            monthly_logins = [0, 0, 0]
            monthly_quizzes = [0, 0, 0]
            
            # Activity breakdown data
            assignment_activities = 0
            quiz_activities = 0
            discussion_activities = 0
            content_activities = 0
            
            for i, month in enumerate(months):
                year = today.year
                if month > today.month:
                    year -= 1
                next_month = month % 12 + 1
                next_year = year
                if month == 12:
                    next_year = year + 1
                    next_month = 1

                start_date = timezone.make_aware(datetime(year, month, 1))
                end_date = timezone.make_aware(datetime(next_year, next_month, 1))

                # Assignment submissions
                monthly_submissions[i] = AssignmentSubmission.objects.filter(
                    assignment__course__in=courses,
                    submitted_at__gte=start_date,
                    submitted_at__lt=end_date
                ).count()

                # Logins tracked by MyTokenObtainPairView (UserActivity, activity_type='login')
                monthly_logins[i] = UserActivity.objects.filter(
                    activity_type='login',
                    user__enrolledcourse__course__in=courses,
                    timestamp__gte=start_date,
                    timestamp__lt=end_date
                ).count()

                # Quiz attempts
                monthly_quizzes[i] = UserActivity.objects.filter(
                    activity_type='quiz_attempt',
                    course__in=courses,
                    timestamp__gte=start_date,
                    timestamp__lt=end_date
                ).count()
            
            # Assignment activities (total)
            assignment_activities = AssignmentSubmission.objects.filter(
                assignment__course__in=courses
            ).count()
            
            quiz_activities = UserActivity.objects.filter(
                activity_type='quiz_attempt',
                course__in=courses
            ).count()
            
            discussion_activities = UserActivity.objects.filter(
                activity_type__in=['discussion_post', 'discussion_reply'],
                course__in=courses
            ).count()
            
            content_activities = UserActivity.objects.filter(
                activity_type='content_view',
                course__in=courses
            ).count()
            
            assignments_to_grade = AssignmentSubmission.objects.filter(
                assignment__course__in=courses,
                status='submitted'
            ).count()
            
            quizzes_created = Quiz.objects.filter(
                course__in=courses
            ).count()
            
            certificates_issued = Certificate.objects.filter(
                course__in=courses
            ).count()
            
            total_students = User.objects.filter(
                enrolledcourse__course__in=courses
            ).distinct().count()
            
            data = {
                'stats': {
                    'total_students': total_students,
                    'assignments_to_grade': assignments_to_grade,
                    'quizzes_created': quizzes_created,
                    'certificates_issued': certificates_issued
                },
                'monthly_submissions': monthly_submissions,
                'monthly_logins': monthly_logins,
                'monthly_quizzes': monthly_quizzes,
                'activity_breakdown': [
                    assignment_activities,
                    quiz_activities,
                    discussion_activities,
                    content_activities
                ]
            }
            
            return Response(data, status=status.HTTP_200_OK)
                
        except Exception as e:
            print(f"Error in TeacherDashboardAPIView: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class TrackLectureCompletionView(APIView):
    """API endpoint to track when a student completes a lecture"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get data from request
            lecture_id = request.data.get('lecture_id')
            course_id = request.data.get('course_id')
            
            if not lecture_id or not course_id:
                return Response(
                    {"error": "Lecture ID and Course ID are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get the lecture and course objects
            lecture = get_object_or_404(Lecture, id=lecture_id)
            course = get_object_or_404(Course, id=course_id)
            
            # Record the activity
            UserActivity.objects.create(
                user=request.user,
                user_type='user',
                activity_type='content_view',
                course=course,
                content_id=str(lecture_id),
                details={
                    'lecture_title': lecture.title,
                    'action': 'completed'
                }
            )
            
            # Update student progress
            try:
                progress, created = StudentProgress.objects.get_or_create(
                    student=request.user,
                    course=course
                )
                
                # Add the lecture to completed lectures
                completed_lectures = progress.completed_lectures or []
                if lecture_id not in completed_lectures:
                    completed_lectures.append(lecture_id)
                    progress.completed_lectures = completed_lectures
                    progress.save()
            except Exception as e:
                print(f"Error updating student progress: {str(e)}")
            
            # Check for quizzes linked to this lecture
            # This is a clean approach that will work for any lecture
            quiz = Quiz.objects.filter(lecture_id=lecture_id).first()
            
            if quiz:
                return Response({
                    "message": "Lecture completion tracked successfully",
                    "quiz_id": quiz.id
                })
            
            return Response(
                {"message": "Lecture completion tracked successfully"},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": "Error tracking lecture completion", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class StudentCourseProgressAPIView(APIView):
    """API endpoint to track student progress through courses"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        lecture_id = request.data.get('lecture_id')
        course_id = request.data.get('course_id')
        
        if not lecture_id or not course_id:
            return Response(
                {"error": "Lecture ID and Course ID are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            lecture = get_object_or_404(Lecture, id=lecture_id)
            course = get_object_or_404(Course, id=course_id)
            
            # Track this as completed lecture
            progress, created = StudentProgress.objects.get_or_create(
                student=request.user,
                course=course
            )
            
            # Convert to list if it's None
            completed_lectures = progress.completed_lectures or []
            
            # Add lecture ID if not already in the list
            if str(lecture_id) not in completed_lectures:
                completed_lectures.append(str(lecture_id))
                progress.completed_lectures = completed_lectures
                progress.save()
                progress.update_progress()
                
                # Also log this activity
                UserActivity.objects.create(
                    user=request.user,
                    user_type=UserActivity.USER,
                    activity_type=UserActivity.CONTENT_VIEW,
                    course=course,
                    content_id=str(lecture_id),
                    details={"action": "completed", "lecture_title": lecture.title}
                )
                
                # Check for quiz associated with this lecture
                quiz = Quiz.objects.filter(lecture=lecture, show_after_lecture=True).first()
                
                return Response({
                    "success": True, 
                    "message": "Lecture marked as complete",
                    "progress": progress.completed_percentage,
                    "has_quiz": quiz is not None,
                    "quiz_id": quiz.id if quiz else None
                })
                
            return Response({
                "success": True,
                "message": "Lecture was already marked as complete",
                "progress": progress.completed_percentage
            })
                
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LectureQuizAssociationView(APIView):
    """API endpoint to associate quizzes with lectures"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            lecture_id = request.data.get('lecture_id')
            quiz_id = request.data.get('quiz_id')
            show_after_lecture = request.data.get('show_after_lecture', True)
            
            if not lecture_id or not quiz_id:
                return Response(
                    {"error": "Lecture ID and Quiz ID are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the lecture and quiz objects
            lecture = get_object_or_404(Lecture, id=lecture_id)
            quiz = get_object_or_404(Quiz, id=quiz_id)
            
            # Update the quiz to associate with this lecture
            quiz.lecture = lecture
            quiz.show_after_lecture = show_after_lecture
            quiz.save()
            
            return Response({
                "success": True,
                "message": "Quiz successfully associated with lecture"
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                "error": f"Failed to associate quiz with lecture: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Add this to views.py
class TeacherSubmitEvent(APIView):
    """Dedicated API endpoint for teacher event submissions"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Verify user is authenticated
            if not request.user.is_authenticated:
                return Response({"error": "Authentication required"}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            
            # Create a copy of the data to modify
            data = request.data.copy()
            
            # Explicitly set the created_by field to the user object instead of email
            data['created_by'] = request.user.id  # Use ID instead of email or object
            
            # Convert event_datetime to date format if needed
            if 'event_datetime' in data:
                # Keep the datetime format but ensure it's properly formatted
                data['date'] = data['event_datetime']
                # Remove the original field to avoid conflicts
                if 'event_datetime' in data:
                    del data['event_datetime']
            
            # Create serializer with request context included
            serializer = EventSerializer(data=data, context={'request': request})
            
            if serializer.is_valid():
                # Pass the request user directly when saving
                event = serializer.save(created_by=request.user)
                
                return Response({
                    "success": True,
                    "message": "Event created successfully",
                    "id": event.id,
                    "name": event.name,
                    "date": event.date
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "success": False,
                    "errors": serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            print(f"Error creating event: {str(e)}")
            import traceback
            traceback.print_exc()  # Print full traceback for debugging
            return Response({
                "success": False, 
                "error": "Failed to create event", 
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AllowedEventPlatforms(APIView):
    """API endpoint to get allowed platform choices for events"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # These should match your backend model choices
        allowed_platforms = {
            'other': 'Other',
            'zoom': 'Zoom',
            'google_meet': 'Google Meet',
            'ms_teams': 'Microsoft Teams',
            'webex': 'WebEx'
        }
        
        return Response(allowed_platforms, status=status.HTTP_200_OK)

# Add to views.py
class GroupsAndUsersView(APIView):
    """API endpoint to get groups and users for event targeting"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get all groups
        groups = Group.objects.all()
        # Get all users (excluding the current user)
        users = User.objects.exclude(id=request.user.id)
        
        # Convert to simple dict format
        groups_data = [{'id': group.id, 'name': group.name} for group in groups]
        users_data = [{'id': user.id, 'name': user.get_full_name() or user.username} 
                     for user in users]
        
        return Response({
            'groups': groups_data,
            'users': users_data
        }, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import UserAppearanceSettings
from .serializer import UserAppearanceSettingsSerializer

class UserAppearanceSettingsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            settings = UserAppearanceSettings.objects.get(user=request.user)
            serializer = UserAppearanceSettingsSerializer(settings)
            return Response(serializer.data)
        except UserAppearanceSettings.DoesNotExist:
            # Return default settings if none exist
            return Response({
                "dark_mode": False,
                "font_size": 16,
                "high_contrast": False,
                "color_theme": "default",
                "density": "comfortable"
            })
            
    def post(self, request):
        # Get or create settings object
        settings, created = UserAppearanceSettings.objects.get_or_create(
            user=request.user,
            defaults={
                'dark_mode': False,
                'font_size': 16,
                'high_contrast': False,
                'color_theme': 'default',
                'density': 'comfortable'
            }
        )
        
        # Update with new data
        serializer = UserAppearanceSettingsSerializer(settings, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StudentQuizzesView(APIView):
    """List all quizzes for a student"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # Verify user has access
        if str(request.user.id) != str(user_id):
            return Response(
                {"error": "You do not have permission to access these quizzes"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Find all courses the student is enrolled in
        enrolled_courses = EnrolledCourse.objects.filter(user=request.user).values_list('course', flat=True)

        # Find all published quizzes for those courses
        quizzes = Quiz.objects.filter(
            course__in=enrolled_courses,
            status='published'
        ).select_related('course', 'lecture').order_by('title')

        serializer = QuizSerializer(quizzes, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class TeacherQuizzesView(APIView):
    """List all quizzes for a teacher's course"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        try:
            # Verify teacher owns this course
            teacher = Teacher.objects.get(user=request.user)
            course = get_object_or_404(Course, id=course_id, teacher=teacher)
            
            # Get all quizzes for this course
            quizzes = Quiz.objects.filter(course=course).order_by('-created_at')
            
            # Add submission counts manually
            result_data = []
            for quiz in quizzes:
                # Count quiz submissions
                submission_count = QuizSubmission.objects.filter(
                    quiz=quiz
                ).values('student').distinct().count()
                
                # Count enrolled students in this course
                enrolled_count = EnrolledCourse.objects.filter(
                    course=course
                ).count()
                
                # Serialize the quiz
                quiz_data = QuizSerializer(quiz).data
                
                # Add the counts
                quiz_data['submissions_count'] = submission_count
                quiz_data['enrolled_students'] = enrolled_count
                
                result_data.append(quiz_data)
                
            return Response(result_data, status=status.HTTP_200_OK)
            
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher profile not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(f"Error fetching quizzes: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QuizDetailView(APIView):
    """Get details for a specific quiz"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, quiz_id):
        try:
            quiz = get_object_or_404(Quiz, id=quiz_id)
            
            # Check if user is a teacher or student enrolled in the course
            try:
                teacher = Teacher.objects.get(user=request.user)
                if quiz.teacher != teacher:
                    return Response(
                        {"error": "You do not have permission to view this quiz"}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Teacher.DoesNotExist:
                # User is a student, check if enrolled in the course
                if quiz.course and not EnrolledCourse.objects.filter(user=request.user, course=quiz.course).exists():
                    return Response(
                        {"error": "You must be enrolled in this course to view quizzes"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                # If it's a lecture quiz, check if enrolled in the lecture's course
                elif quiz.lecture and not EnrolledCourse.objects.filter(user=request.user, course=quiz.lecture.course).exists():
                    return Response(
                        {"error": "You must be enrolled in this course to view quizzes"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Serialize and return the quiz
            serializer = QuizSerializer(quiz)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error getting quiz: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Add the delete method to handle DELETE requests
    def delete(self, request, quiz_id):
        try:
            # Verify user is a teacher and owns the quiz
            try:
                teacher = Teacher.objects.get(user=request.user)
            except Teacher.DoesNotExist:
                return Response(
                    {"error": "Only teachers can delete quizzes"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
            quiz = get_object_or_404(Quiz, id=quiz_id)
            
            # Check if the teacher owns this quiz
            if quiz.teacher != teacher:
                return Response(
                    {"error": "You can only delete your own quizzes"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Delete the quiz
            quiz.delete()
            
            return Response(
                {"message": "Quiz deleted successfully"}, 
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Exception as e:
            print(f"Error deleting quiz: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CreateQuizView(APIView):
    """Create a new quiz"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Verify user is a teacher
            teacher = get_object_or_404(Teacher, user=request.user)
            
            # Extract and verify course_id and lecture_id
            course_id = request.data.get('course_id')
            lecture_id = request.data.get('lecture_id')
            
            if not course_id and not lecture_id:
                return Response(
                    {"error": "Either course_id or lecture_id must be provided"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get course if provided
            course = None
            if course_id:
                course = get_object_or_404(Course, id=course_id, teacher=teacher)
            
            # Get lecture if provided
            lecture = None
            if lecture_id:
                lecture = get_object_or_404(Lecture, id=lecture_id)
                # Verify the lecture's course belongs to this teacher
                if lecture.course.teacher != teacher:
                    return Response(
                        {"error": "You don't have permission to create quizzes for this lecture"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Create the quiz
            quiz = Quiz.objects.create(
                title=request.data.get('title', 'Untitled Quiz'),
                description=request.data.get('description', ''),
                course=course,
                lecture=lecture,
                teacher=teacher,
                points=request.data.get('points', 100),
                status=request.data.get('status', 'draft')
            )
            
            # Extract questions from the request
            questions_data = request.data.get('questions', [])
            
            # Process each question
            for idx, q_data in enumerate(questions_data):
                question = QuizQuestion.objects.create(
                    quiz=quiz,
                    title=q_data.get('title', ''),
                    description=q_data.get('description', ''),
                    type=q_data.get('type', 'multiple_choice'),
                    required=q_data.get('required', True),
                    points=q_data.get('points', 1),
                    order=idx,
                    options=q_data.get('options', []),
                    correct_feedback=q_data.get('correct_feedback', ''),
                    incorrect_feedback=q_data.get('incorrect_feedback', '')
                )
            
            # Return the created quiz
            serializer = QuizSerializer(quiz)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Only teachers can create quizzes"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            print(f"Error creating quiz: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateQuizView(APIView):
    """Update an existing quiz"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, quiz_id):
        try:
            # Verify user is a teacher and owns the quiz
            teacher = get_object_or_404(Teacher, user=request.user)
            quiz = get_object_or_404(Quiz, id=quiz_id, teacher=teacher)
            
            # Update basic quiz fields
            quiz.title = request.data.get('title', quiz.title)
            quiz.description = request.data.get('description', quiz.description)
            quiz.points = request.data.get('points', quiz.points)
            quiz.status = request.data.get('status', quiz.status)
            
            # Update course/lecture if provided
            course_id = request.data.get('course_id')
            lecture_id = request.data.get('lecture_id')
            
            if course_id:
                course = get_object_or_404(Course, id=course_id, teacher=teacher)
                quiz.course = course
                quiz.lecture = None  # Reset lecture if course is provided
                
            if lecture_id:
                lecture = get_object_or_404(Lecture, id=lecture_id)
                # Verify the lecture's course belongs to this teacher
                if lecture.course.teacher != teacher:
                    return Response(
                        {"error": "You don't have permission to assign quizzes to this lecture"},
                        status=status.HTTP_403_FORBIDDEN
                    )
                quiz.lecture = lecture
                quiz.course = lecture.course  # Set the course to the lecture's course
            
            quiz.save()
            
            # Extract questions data
            questions_data = request.data.get('questions', [])
            
            # Delete existing questions
            quiz.questions.all().delete()
            
            # Add new questions
            for idx, q_data in enumerate(questions_data):
                question = QuizQuestion.objects.create(
                    quiz=quiz,
                    title=q_data.get('title', ''),
                    description=q_data.get('description', ''),
                    type=q_data.get('type', 'multiple_choice'),
                    required=q_data.get('required', True),
                    points=q_data.get('points', 1),
                    order=idx,
                    options=q_data.get('options', []),
                    correct_feedback=q_data.get('correct_feedback', ''),
                    incorrect_feedback=q_data.get('incorrect_feedback', '')
                )
            
            # Return the updated quiz
            serializer = QuizSerializer(quiz)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Only teachers can update quizzes"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            print(f"Error updating quiz: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self, request, quiz_id):
        try:
            # Verify user is a teacher and owns the quiz
            teacher = get_object_or_404(Teacher, user=request.user)
            quiz = get_object_or_404(Quiz, id=quiz_id, teacher=teacher)
            
            # Delete the quiz
            quiz.delete()
            
            return Response({"message": "Quiz deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
            
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Only teachers can delete quizzes"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            print(f"Error deleting quiz: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class QuizSubmissionView(APIView):
    """Handle student submissions for quizzes"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get quiz and verify access
            quiz_id = request.data.get('quiz_id')
            if not quiz_id:
                return Response(
                    {"error": "Quiz ID is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            quiz = get_object_or_404(Quiz, id=quiz_id)
            
            # Verify student is enrolled in the course
            course = quiz.course or (quiz.lecture.course if quiz.lecture else None)
            if course and not EnrolledCourse.objects.filter(user=request.user, course=course).exists():
                return Response(
                    {"error": "You must be enrolled in this course to submit the quiz"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if student has already submitted this quiz
            existing_submission = QuizSubmission.objects.filter(
                quiz=quiz, 
                student=request.user
            ).first()
            
            # Create or update the submission
            if existing_submission:
                submission = existing_submission
            else:
                submission = QuizSubmission(
                    quiz=quiz,
                    student=request.user
                )
            
            # Get answers from request data
            answers = request.data.get('answers', {})
            submission.answers = answers
            
            # Auto-grade quiz if all questions are multiple choice or true/false
            auto_gradeable = True
            total_points = 0
            earned_points = 0
            correct_answers = 0
            
            for question in quiz.questions.all():
                total_points += question.points
                
                if question.type not in ['multiple_choice', 'true_false', 'checkbox']:
                    auto_gradeable = False
                    continue
                    
                # Get student's answer(s) for this question
                student_answer = answers.get(str(question.id))
                if not student_answer:
                    continue
                
                # For checkbox questions (multiple correct answers possible)
                if question.type == 'checkbox':
                    options = question.options or []
                    student_selections = set(student_answer if isinstance(student_answer, list) else [student_answer])
                    correct_options = set(str(i) for i, opt in enumerate(options) if opt.get('isCorrect'))
                    
                    # Award partial credit for checkbox questions
                    if student_selections and correct_options:
                        correct_selections = student_selections.intersection(correct_options)
                        incorrect_selections = student_selections.difference(correct_options)
                        
                        # Calculate score based on correct selections vs incorrect selections
                        if len(correct_selections) > 0:
                            accuracy = len(correct_selections) / len(correct_options)
                            penalty = len(incorrect_selections) / (len(options) - len(correct_options)) if len(options) > len(correct_options) else 0
                            question_score = max(0, accuracy - penalty) * question.points
                            earned_points += question_score
                            
                            if accuracy == 1 and penalty == 0:
                                correct_answers += 1
                    
                # For multiple choice and true/false (single correct answer)
                else:
                    options = question.options or []
                    correct_option_index = next((i for i, opt in enumerate(options) if opt.get('isCorrect')), None)
                    
                    if str(student_answer) == str(correct_option_index):
                        earned_points += question.points
                        correct_answers += 1
            
            # Update submission with auto-grading results
            if auto_gradeable:
                # Calculate percentage score
                percentage = (earned_points / total_points * 100) if total_points > 0 else 0
                submission.score = round(percentage)
                submission.correct_answers = correct_answers
                submission.total_questions = quiz.questions.count()
                submission.status = 'graded'
                submission.auto_graded = True
                
                # Add grading timestamp
                submission.graded_at = timezone.now()
            
            # Save the submission
            submission.submitted_at = timezone.now()
            submission.save()
            
            # Track this quiz attempt
            UserActivity.objects.create(
                user=request.user,
                user_type=UserActivity.USER,
                activity_type=UserActivity.QUIZ_ATTEMPT,
                course=course,
                content_id=str(quiz_id),
                details={
                    "quiz_title": quiz.title,
                    "score": getattr(submission, "score", None)
                }
            )
            
            # Create notification for teacher
            if not submission.notification_sent:
                Notification.objects.create(
                    user=quiz.teacher.user,
                    sender=request.user,
                    quiz=quiz,
                    type="Quiz Submission",
                    title=f"New quiz submission",
                    content=f"{request.user.username} has submitted the quiz '{quiz.title}'",
                    url=f"/teacher/quizzes/{quiz.id}/submissions"
                )
                submission.notification_sent = True
                submission.save(update_fields=['notification_sent'])
            
            # Return response based on whether the quiz was auto-graded
            if auto_gradeable:
                return Response({
                    "message": "Quiz submitted and automatically graded",
                    "submission_id": submission.id,
                    "score": submission.score,
                    "correct_answers": submission.correct_answers,
                    "total_questions": submission.total_questions,
                    "auto_graded": True
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "message": "Quiz submitted successfully",
                    "submission_id": submission.id,
                    "auto_graded": False
                }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            # print(f"Error submitting quiz: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StudentQuizzesView(APIView):
    """List all quizzes for a student"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, user_id):
        # Verify user has access
        if str(request.user.id) != str(user_id):
            return Response(
                {"error": "You do not have permission to access these quizzes"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Find all courses the student is enrolled in
        enrolled_courses = EnrolledCourse.objects.filter(user=request.user).values_list('course', flat=True)
        
        # Find all published quizzes for those courses
        course_quizzes = Quiz.objects.filter(
            course__in=enrolled_courses,
            status='published'
        )
        
        # Find all lecture quizzes for lectures in those courses
        lecture_quizzes = Quiz.objects.filter(
            lecture__course__in=enrolled_courses,
            status='published'
        )
        
        # Combine the querysets
        quizzes = course_quizzes.union(lecture_quizzes)
        
        # Add submission status for each quiz
        result_data = []
        for quiz in quizzes:
            submission = QuizSubmission.objects.filter(
                quiz=quiz,
                student=request.user
            ).first()
            
            quiz_data = QuizSerializer(quiz).data
            if submission:
                quiz_data['submission'] = {
                    'id': submission.id,
                    'submitted_at': submission.submitted_at,
                    'status': submission.status,
                    'score': submission.score,
                    'correct_answers': submission.correct_answers,
                    'total_questions': submission.total_questions
                }
            else:
                quiz_data['submission'] = None
                
            result_data.append(quiz_data)
            
        return Response(result_data, status=status.HTTP_200_OK)


# Add view to get all quizzes for a teacher (across all courses)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_quizzes_all(request, teacher_id):
    """Get all quizzes for a teacher (across all courses)"""
    try:
        teacher = get_object_or_404(Teacher, id=teacher_id)
        
        # Verify user has permission to access these quizzes
        if request.user != teacher.user:
            return Response(
                {"error": "You do not have permission to access these quizzes"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get all quizzes by this teacher
        quizzes = Quiz.objects.filter(teacher=teacher)
        
        # Get counts manually
        result_data = []
        for quiz in quizzes.order_by('-created_at'):
            # Count quiz submissions
            submission_count = QuizSubmission.objects.filter(
                quiz=quiz
            ).values('student').distinct().count()
            
            # Count enrolled students in this course
            course = quiz.course or (quiz.lecture.course if quiz.lecture else None)
            enrolled_count = EnrolledCourse.objects.filter(
                course=course
            ).count() if course else 0
            
            # Serialize the quiz
            quiz_data = QuizSerializer(quiz).data
            
            # Add the counts
            quiz_data['submissions_count'] = submission_count
            quiz_data['enrolled_students'] = enrolled_count
            
            result_data.append(quiz_data)
        
        return Response(result_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error getting teacher quizzes: {str(e)}")
        return Response(
            {"error": f"Failed to fetch quizzes: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class QuizSubmissionView(APIView):
    """Handle student submissions for quizzes"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Get quiz and verify access
            quiz_id = request.data.get('quiz_id')
            if not quiz_id:
                return Response(
                    {"error": "Quiz ID is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            quiz = get_object_or_404(Quiz, id=quiz_id)
            
            # Verify student is enrolled in the course
            course = quiz.course or (quiz.lecture.course if quiz.lecture else None)
            if course and not EnrolledCourse.objects.filter(user=request.user, course=course).exists():
                return Response(
                    {"error": "You must be enrolled in this course to submit the quiz"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if student has already submitted this quiz
            existing_submission = QuizSubmission.objects.filter(
                quiz=quiz, 
                student=request.user
            ).first()
            
            # Create or update the submission
            if existing_submission:
                submission = existing_submission
            else:
                submission = QuizSubmission(
                    quiz=quiz,
                    student=request.user
                )
            
            # Get answers from request data
            answers = request.data.get('answers', {})
            submission.answers = answers
            
            # Auto-grade quiz if all questions are multiple choice or true/false
            auto_gradeable = True
            total_points = 0
            earned_points = 0
            correct_answers = 0
            
            for question in quiz.questions.all():
                total_points += question.points
                
                if question.type not in ['multiple_choice', 'true_false', 'checkbox']:
                    auto_gradeable = False
                    continue
                    
                # Get student's answer(s) for this question
                student_answer = answers.get(str(question.id))
                if not student_answer:
                    continue
                
                # For checkbox questions (multiple correct answers possible)
                if question.type == 'checkbox':
                    options = question.options or []
                    student_selections = set(student_answer if isinstance(student_answer, list) else [student_answer])
                    correct_options = set(str(i) for i, opt in enumerate(options) if opt.get('isCorrect'))
                    
                    # Award partial credit for checkbox questions
                    if student_selections and correct_options:
                        correct_selections = student_selections.intersection(correct_options)
                        incorrect_selections = student_selections.difference(correct_options)
                        
                        # Calculate score based on correct selections vs incorrect selections
                        if len(correct_selections) > 0:
                            accuracy = len(correct_selections) / len(correct_options)
                            penalty = len(incorrect_selections) / (len(options) - len(correct_options)) if len(options) > len(correct_options) else 0
                            question_score = max(0, accuracy - penalty) * question.points
                            earned_points += question_score
                            
                            if accuracy == 1 and penalty == 0:
                                correct_answers += 1
                    
                # For multiple choice and true/false (single correct answer)
                else:
                    options = question.options or []
                    correct_option_index = next((i for i, opt in enumerate(options) if opt.get('isCorrect')), None)
                    
                    if str(student_answer) == str(correct_option_index):
                        earned_points += question.points
                        correct_answers += 1
            
            # Update submission with auto-grading results
            if auto_gradeable:
                # Calculate percentage score
                percentage = (earned_points / total_points * 100) if total_points > 0 else 0
                submission.score = round(percentage)
                submission.correct_answers = correct_answers
                submission.total_questions = quiz.questions.count()
                submission.status = 'graded'
                submission.auto_graded = True
                
                # Add grading timestamp
                submission.graded_at = timezone.now()
            
            # Save the submission
            submission.submitted_at = timezone.now()
            submission.save()
            
            # Track this quiz attempt - FIXED VERSION
            try:
                # Get the course first - handle both direct course and lecture course
                course = quiz.course
                if not course and quiz.lecture:
                    course = quiz.lecture.course
                
                # Now create the activity with proper error handling
                if course:  # Only create if we have a valid course
                    UserActivity.objects.create(
                        user=request.user,
                        user_type='user',  # Use literal string instead of constant
                        activity_type='quiz_attempt',  # Use literal string
                        course=course,
                        content_id=str(quiz_id),
                        details={
                            "quiz_title": quiz.title,
                            "score": submission.score if hasattr(submission, "score") else None
                        }
                    )
                    print(f"Successfully tracked quiz attempt for user {request.user.id}, quiz {quiz_id}")
            except Exception as tracking_error:
                # Log the error but don't fail the submission
                print(f"Failed to track quiz attempt: {str(tracking_error)}")
            
            # Create notification for teacher
            if not submission.notification_sent:
                Notification.objects.create(
                    user=quiz.teacher.user,
                    sender=request.user,
                    quiz=quiz,
                    type="Quiz Submission",
                    title=f"New quiz submission",
                    content=f"{request.user.username} has submitted the quiz '{quiz.title}'",
                    url=f"/teacher/quizzes/{quiz.id}/submissions"
                )
                submission.notification_sent = True
                submission.save(update_fields=['notification_sent'])
            
            # Return response based on whether the quiz was auto-graded
            if auto_gradeable:
                return Response({
                    "message": "Quiz submitted and automatically graded",
                    "submission_id": submission.id,
                    "score": submission.score,
                    "correct_answers": submission.correct_answers,
                    "total_questions": submission.total_questions,
                    "auto_graded": True
                }, status=status.HTTP_201_CREATED)
            else:
                return Response({
                    "message": "Quiz submitted successfully",
                    "submission_id": submission.id,
                    "auto_graded": False
                }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print(f"Error submitting quiz: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_assignment(request):
    """Create a new assignment"""
    try:
        # Verify user is a teacher
        try:
            teacher = Teacher.objects.get(user=request.user)
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Only teachers can create assignments"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        # Get next available ID
        last_assignment = Assignment.objects.all().order_by('-id').first()
        next_id = (last_assignment.id + 1) if last_assignment else 1
            
        # Extract and verify course_id
        course_id = request.data.get('course_id')
        if not course_id:
            return Response({"error": "Course ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            course = Course.objects.get(id=course_id, teacher=teacher)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or access denied"}, status=status.HTTP_404_NOT_FOUND)
        
        # Prepare data for serializer
        data = request.data.copy()
        data['id'] = next_id  # Set the next available ID
        data['teacher'] = teacher.id
        data['course'] = course.id
        
        # Extract questions from the request
        questions_data = data.pop('questions', [])
        
        try:
            # Create the assignment first
            assignment = Assignment.objects.create(
                id=next_id,
                teacher=teacher,
                course=course,
                title=data.get('title', 'Untitled Assignment'),
                description=data.get('description', ''),
                due_date=data.get('due_date'),
                points=data.get('points', 100),
                status=data.get('status', 'draft'),
                has_test_mode=data.get('has_test_mode', False),
                time_limit_minutes=data.get('time_limit_minutes'),
                test_content=data.get('test_content')
            )

            # Now create questions with the proper assignment reference
            for idx, question_data in enumerate(questions_data):
                # Get next available question ID
                last_question = AssignmentQuestion.objects.all().order_by('-id').first()
                next_question_id = (last_question.id + 1) if last_question else 1

                # Create the question directly
                AssignmentQuestion.objects.create(
                    id=next_question_id,
                    assignment=assignment,  # This is now a valid assignment instance
                    title=question_data.get('title', ''),
                    description=question_data.get('description', ''),
                    type=question_data.get('type', 'multiple_choice'),
                    required=question_data.get('required', True),
                    points=question_data.get('points', 0),
                    order=idx,
                    options=question_data.get('options')
                )

            # Return the complete assignment data
            serializer = AssignmentSerializer(assignment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            # If anything fails during creation, clean up
            if 'assignment' in locals():
                assignment.delete()
            raise e

    except Exception as e:
        # print(f"Error creating assignment: {str(e)}")
        return Response(
            {"error": f"Failed to create assignment: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_assignments_all(request, teacher_id):
    """Get all assignments for a teacher (across all courses)"""
    try:
        teacher = get_object_or_404(Teacher, id=teacher_id)
        
        # Verify user has permission to access these assignments
        if request.user != teacher.user:
            return Response(
                {"error": "You do not have permission to access these assignments"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get all assignments by this teacher
        assignments = Assignment.objects.filter(teacher=teacher)
        
        # Add logging to diagnose the issue
        # print(f"Found {assignments.count()} assignments for teacher {teacher_id}")
        
        # Get counts manually instead of using annotations
        result_data = []
        for assignment in assignments.order_by('-created_at'):
            # Count unique students who submitted this assignment
            submission_count = AssignmentSubmission.objects.filter(
                assignment=assignment
            ).values('student').distinct().count()
            
            # Count enrolled students in this course
            enrolled_count = EnrolledCourse.objects.filter(
                course=assignment.course
            ).count()
            
            # Log the counts for debugging
            print(f"Assignment {assignment.id} ({assignment.title}): {submission_count}/{enrolled_count}")
            
            # Serialize the assignment
            assignment_data = AssignmentListSerializer(assignment).data
            
            # Add the correct counts
            assignment_data['submissions_count'] = submission_count
            assignment_data['enrolled_students'] = enrolled_count
            
            result_data.append(assignment_data)
        
        return Response(result_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        # print(f"Error getting teacher assignments: {str(e)}")
        return Response(
            {"error": f"Failed to fetch assignments: {str(e)}"}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_assignment(request, assignment_id):
    """Get details for a specific assignment"""
    try:
        # Check if user is a teacher
        is_teacher = hasattr(request.user, 'teacher')
        
        if is_teacher:
            # For teachers, they should only be able to get their own assignments
            teacher = request.user.teacher
            assignment = get_object_or_404(Assignment, id=assignment_id, teacher=teacher)
        else:
            # For students, they should only be able to get assignments from courses they're enrolled in
            assignment = get_object_or_404(Assignment, id=assignment_id)
            
            # Check if student is enrolled in the course
            if not EnrolledCourse.objects.filter(user=request.user, course=assignment.course).exists():
                return Response(
                    {"error": "You do not have access to this assignment"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Serialize and return the assignment
        serializer = AssignmentSerializer(assignment)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        # print(f"Error getting assignment: {str(e)}")
        return Response(
            {"error": f"Failed to fetch assignment: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
@api_view(['POST', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def update_assignment(request, assignment_id):
    """Update or delete an assignment"""
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return Response(
            {"error": "Only teachers can modify assignments"}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    assignment = get_object_or_404(Assignment, id=assignment_id, teacher=teacher)
    
    if request.method == 'DELETE':
        # Handle DELETE request
        assignment.delete()
        return Response({"message": "Assignment deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    # Continue with POST or PUT logic for updating (handle both methods the same way)
    # Extract and verify course_id
    course_id = request.data.get('course_id')
    if course_id:
        try:
            course = Course.objects.get(id=course_id, teacher=teacher)
            request.data['course'] = course.id
        except Course.DoesNotExist:
            return Response({"error": "Course not found or access denied"}, status=status.HTTP_404_NOT_FOUND)
    
    # Extract questions from request
    questions_data = request.data.pop('questions', [])
    
    # Update assignment fields
    serializer = AssignmentSerializer(assignment, data=request.data, partial=True)
    if serializer.is_valid():
        assignment = serializer.save()
        
        # Delete existing questions and create new ones
        assignment.questions.all().delete()
        
        # Save new questions
        for idx, question_data in enumerate(questions_data):
            options = question_data.pop('options', None) if isinstance(question_data, dict) else None
            
            question_data = {
                'title': question_data.get('title', ''),
                'description': question_data.get('description', ''),
                'type': question_data.get('type', 'multiple_choice'),
                'required': question_data.get('required', True),
                'points': question_data.get('points', 0),
                'order': idx,
            }
            
            question = AssignmentQuestion.objects.create(
                assignment=assignment,
                **question_data
            )
            
            if options:
                question.options = options
                question.save()
                
        # Return the updated assignment
        result = AssignmentSerializer(assignment)
        return Response(result.data, status=status.HTTP_200_OK)
        
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class QuizAnswerCheckView(APIView):
    """API view to check if a quiz answer is correct (during quiz attempt)"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            quiz_id = request.data.get('quiz_id')
            question_id = request.data.get('question_id')
            selected_answer = request.data.get('selected_answer')
            
            if not quiz_id or not question_id:
                return Response({"error": "Quiz ID and Question ID are required"},
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Get the quiz question
            question = get_object_or_404(QuizQuestion, id=question_id, quiz_id=quiz_id)
            quiz = question.quiz
            
            # Get the course for activity tracking
            course = quiz.course or (quiz.lecture.course if quiz.lecture and hasattr(quiz.lecture, 'course') else None)
            
            # Track this quiz attempt 
            try:
                UserActivity.objects.create(
                    user=request.user,
                    user_type='user',
                    activity_type='quiz_attempt',
                    course=course,
                    content_id=str(quiz_id),
                    details={
                        "quiz_title": quiz.title,
                        "question_id": question_id,
                        "timestamp": timezone.now().isoformat()
                    }
                )
                print(f"Quiz attempt tracked for quiz {quiz_id} by user {request.user.id}")
            except Exception as track_error:
                print(f"Error tracking quiz attempt: {str(track_error)}")
            
            # Check if the answer is correct based on question type
            correct = False
            
            # Debug info to troubleshoot the issue
            print(f"Question type: {question.type}")
            print(f"Selected answer: {selected_answer} (type: {type(selected_answer).__name__})")
            print(f"Question options: {question.options}")
            
            # For multiple choice questions - FIXED VALIDATION
            if question.type == 'multiple_choice':
                options = question.options or []
                
                # Ensure selected_answer is treated as an integer index
                try:
                    selected_index = int(selected_answer)
                except (ValueError, TypeError):
                    selected_index = None
                
                # Check each option for correctness
                for i, option in enumerate(options):
                    is_correct = option.get('isCorrect', False) or option.get('is_correct', False)
                    
                    if i == selected_index and is_correct:
                        correct = True
                        break
                        
                print(f"Answer validation result: {correct}")
            
            # Return the result with the correct answer index
            correct_index = next((i for i, opt in enumerate(question.options or []) 
                              if opt.get('isCorrect') or opt.get('is_correct')), None)
            
            return Response({
                "is_correct": correct,
                "correct_answer": correct_index,
                "explanation": question.correct_feedback if correct else question.incorrect_feedback
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # print(f"Error checking quiz answer: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class StudentQuizDetailView(APIView):
    """API view to get quiz details with questions for a student"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, quiz_id):
        try:
            # Get the quiz
            quiz = get_object_or_404(Quiz, id=quiz_id)
            
            # Verify the student is enrolled in the course
            if quiz.course:
                is_enrolled = EnrolledCourse.objects.filter(
                    user=request.user, 
                    course=quiz.course
                ).exists()
                
                if not is_enrolled:
                    return Response(
                        {"error": "You must be enrolled in this course to access this quiz"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Or if it's a lecture quiz, check enrollment in that lecture's course
            elif quiz.lecture:
                is_enrolled = EnrolledCourse.objects.filter(
                    user=request.user, 
                    course=quiz.lecture.course
                ).exists()
                
                if not is_enrolled:
                    return Response(
                        {"error": "You must be enrolled in this course to access this quiz"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            
            # Get questions for the quiz
            questions = QuizQuestion.objects.filter(quiz=quiz)
            
            # Serialize the quiz with questions
            quiz_data = QuizSerializer(quiz).data
            questions_data = QuizQuestionSerializer(questions, many=True).data
            
            # Add questions to the response
            quiz_data['questions'] = questions_data
            
            return Response(quiz_data, status=status.HTTP_200_OK)
            
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # print(f"Error fetching quiz: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Add to views.py - proper event update functionality
class EventUpdateView(APIView):
    """API endpoint to update an existing event"""
    permission_classes = [IsAuthenticated]
    
    def put(self, request, event_id):
        try:
            # Find the event
            event = get_object_or_404(Event, id=event_id)
            
            # Check if user has permission to update this event
            if event.created_by != request.user:
                return Response(
                    {"error": "You don't have permission to update this event"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create serializer with the event and the request data
            serializer = EventSerializer(event, data=request.data, partial=True)
            
            if serializer.is_valid():
                # Save the updated event
                updated_event = serializer.save()
                return Response(
                    EventSerializer(updated_event).data,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            print(f"Error updating event: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response(
                {"error": f"Failed to update event: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    class TeacherLectureListView(APIView):
        """API endpoint to list and create lectures for a course"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request, course_id):
        """Get all lectures for a specific course"""
        try:
            # Verify user is the course teacher
            try:
                teacher = Teacher.objects.get(user=request.user)
                course = get_object_or_404(Course, id=course_id, teacher=teacher)
            except (Teacher.DoesNotExist, Course.DoesNotExist):
                return Response(
                    {"error": "Course not found or you don't have permission to access it"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Get all lectures for this course, ordered by their position
            lectures = Lecture.objects.filter(course=course).order_by('order')
            
            # Serialize the lectures
            serializer = LectureSerializer(lectures, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            # print(f"Error getting lectures: {str(e)}")
            return Response(
                {"error": f"Failed to fetch lectures: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, course_id):
        """Create a new lecture for a course"""
        try:
            # Verify user is the course teacher
            try:
                teacher = Teacher.objects.get(user=request.user)
                course = get_object_or_404(Course, id=course_id, teacher=teacher)
            except (Teacher.DoesNotExist, Course.DoesNotExist):
                return Response(
                    {"error": "Course not found or you don't have permission to access it"},
                    status=status.HTTP_403_FORBIDDEN
                )
               
            # Create a copy of the request data and add course_id
            data = request.data.copy()
            data['course'] = course_id
            
            # If order is not specified, add it at the end
            if 'order' not in data:
                last_lecture = Lecture.objects.filter(course=course).order_by('-order').first()
                next_order = (last_lecture.order + 1) if last_lecture else 0
                data['order'] = next_order
                
            # Create serializer and validate
            serializer = LectureSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                # Save the new lecture
                lecture = serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            # print(f"Error creating lecture: {str(e)}")
            return Response(
                {"error": f"Failed to create lecture: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# Fix the TeacherLectureListView class - it was indented inside EventUpdateView
class TeacherLectureListView(APIView):
    """API endpoint to list and create lectures for a course"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request, course_id):
        """Get all lectures for a specific course"""
        try:
            # Verify user is the course teacher
            try:
                teacher = Teacher.objects.get(user=request.user)
                course = get_object_or_404(Course, id=course_id, teacher=teacher)
            except (Teacher.DoesNotExist, Course.DoesNotExist):
                return Response(
                    {"error": "Course not found or you don't have permission to access it"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Get all lectures for this course, ordered by their position
            lectures = Lecture.objects.filter(course=course).order_by('order')
            
            # Serialize the lectures
            serializer = LectureSerializer(lectures, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error getting lectures: {str(e)}")
            return Response(
                {"error": f"Failed to fetch lectures: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, course_id):
        """Create a new lecture for a course"""
        try:
            # Verify user is the course teacher
            try:
                teacher = Teacher.objects.get(user=request.user)
                course = get_object_or_404(Course, id=course_id, teacher=teacher)
            except (Teacher.DoesNotExist, Course.DoesNotExist):
                return Response(
                    {"error": "Course not found or you don't have permission to access it"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Create a copy of the request data and add course_id
            data = request.data.copy()
            data['course'] = course_id
            
            # If order is not specified, add it at the end
            if 'order' not in data:
                last_lecture = Lecture.objects.filter(course=course).order_by('-order').first()
                next_order = (last_lecture.order + 1) if last_lecture else 0
                data['order'] = next_order
                
            # Create serializer and validate
            serializer = LectureSerializer(data=data, context={'request': request})
            if serializer.is_valid():
                # Save the new lecture
                lecture = serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            print(f"Error creating lecture: {str(e)}")
            return Response(
                {"error": f"Failed to create lecture: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class LectureOrderUpdateView(APIView):
    """API endpoint to update lecture order"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id):
        """Update the order of lectures in a course"""
        try:
            # Verify user is the course teacher
            try:
                teacher = Teacher.objects.get(user=request.user)
                course = get_object_or_404(Course, id=course_id, teacher=teacher)
            except (Teacher.DoesNotExist, Course.DoesNotExist):
                return Response(
                    {"error": "Course not found or you don't have permission to access it"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Extract ordered lecture IDs from request data
            lecture_order = request.data.get('lecture_order', [])
            if not lecture_order or not isinstance(lecture_order, list):
                return Response(
                    {"error": "Invalid lecture order data. Expected array of lecture IDs."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Update the order of each lecture
            with transaction.atomic():
                for index, lecture_id in enumerate(lecture_order):
                    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
                    lecture.order = index
                    lecture.save()
                    
            # Return the updated lectures in their new order
            lectures = Lecture.objects.filter(course=course).order_by('order')
            serializer = LectureSerializer(lectures, many=True, context={'request': request})
            
            return Response({
                "message": "Lecture order updated successfully",
                "lectures": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            # print(f"Error updating lecture order: {str(e)}")
            return Response(
                {"error": f"Failed to update lecture order: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class TeacherLectureDetailView(APIView):
    """API endpoint to manage a specific lecture"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get(self, request, lecture_id):
        """Get details of a specific lecture"""
        try:
            lecture = get_object_or_404(Lecture, id=lecture_id)
            
            # Verify user is the course teacher
            try:
                teacher = Teacher.objects.get(user=request.user)
                if lecture.course.teacher != teacher:
                    return Response(
                        {"error": "You don't have permission to access this lecture"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Teacher.DoesNotExist:
                return Response(
                    {"error": "Teacher profile not found"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Serialize and return the lecture
            serializer = LectureSerializer(lecture, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Lecture.DoesNotExist:
            return Response({"error": "Lecture not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # print(f"Error retrieving lecture: {str(e)}")
            return Response(
                {"error": f"Failed to fetch lecture: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request, lecture_id):
        """Update a specific lecture"""
        try:
            lecture = get_object_or_404(Lecture, id=lecture_id)
            
            # Verify user is the course teacher
            try:
                teacher = Teacher.objects.get(user=request.user)
                if lecture.course.teacher != teacher:
                    return Response(
                        {"error": "You don't have permission to modify this lecture"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Teacher.DoesNotExist:
                return Response(
                    {"error": "Teacher profile not found"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Update the lecture
            serializer = LectureSerializer(lecture, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                updated_lecture = serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Lecture.DoesNotExist:
            return Response({"error": "Lecture not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # print(f"Error updating lecture: {str(e)}")
            return Response(
                {"error": f"Failed to update lecture: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, lecture_id):
        """Delete a specific lecture"""
        try:
            lecture = get_object_or_404(Lecture, id=lecture_id)
            
            # Verify user is the course teacher
            try:
                teacher = Teacher.objects.get(user=request.user)
                if lecture.course.teacher != teacher:
                    return Response(
                        {"error": "You don't have permission to delete this lecture"},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Teacher.DoesNotExist:
                return Response(
                    {"error": "Teacher profile not found"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Delete the lecture
            lecture.delete()
            return Response(
                {"message": "Lecture deleted successfully"},
                status=status.HTTP_204_NO_CONTENT
            )
                
        except Lecture.DoesNotExist:
            return Response({"error": "Lecture not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # print(f"Error deleting lecture: {str(e)}")
            return Response(
                {"error": f"Failed to delete lecture: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LectureOrderUpdateView(APIView):
    """API endpoint to update lecture order"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id):
        """Update the order of lectures in a course"""
        try:
            # Verify user is the course teacher
            try:
                teacher = Teacher.objects.get(user=request.user)
                course = get_object_or_404(Course, id=course_id, teacher=teacher)
            except (Teacher.DoesNotExist, Course.DoesNotExist):
                return Response(
                    {"error": "Course not found or you don't have permission to access it"},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Extract ordered lecture IDs from request data
            lecture_order = request.data.get('lecture_order', [])
            if not lecture_order or not isinstance(lecture_order, list):
                return Response(
                    {"error": "Invalid lecture order data. Expected array of lecture IDs."},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Update the order of each lecture
            with transaction.atomic():
                for index, lecture_id in enumerate(lecture_order):
                    lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
                    lecture.order = index
                    lecture.save()
                    
            # Return the updated lectures in their new order
            lectures = Lecture.objects.filter(course=course).order_by('order')
            serializer = LectureSerializer(lectures, many=True, context={'request': request})
            
            return Response({
                "message": "Lecture order updated successfully",
                "lectures": serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error updating lecture order: {str(e)}")
            return Response(
                {"error": f"Failed to update lecture order: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TeacherAllCoursesView(APIView):
    """API endpoint to get all courses for a teacher"""
    permission_classes = [IsAuthenticated]
    def delete(self, request, course_id):
        # Only allow the teacher who owns the course to delete it
        teacher = get_object_or_404(Teacher, user=request.user)
        course = get_object_or_404(Course, id=course_id, teacher=teacher)
        course.delete()
        return Response({"message": "Course deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    def get(self, request):
        """Get all courses for the authenticated teacher"""
        try:
            # Get the teacher
            teacher = get_object_or_404(Teacher, user=request.user)
            
            # Get all courses for this teacher
            courses = Course.objects.filter(teacher=teacher)
            
            # Serialize the courses
            serializer = CourseSerializer(courses, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Teacher.DoesNotExist:
            return Response(
                {"error": "Teacher profile not found for this user"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # print(f"Error fetching teacher courses: {str(e)}")
            return Response(
                {"error": f"Failed to fetch courses: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class TeacherCourseDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, course_id):
        # Only allow the teacher who owns the course to delete it
        teacher = get_object_or_404(Teacher, user=request.user)
        course = get_object_or_404(Course, id=course_id, teacher=teacher)
        course.delete()
        return Response({"message": "Course deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

from rest_framework.parsers import MultiPartParser, FormParser

class LectureCreateAPIView(APIView):
    """API endpoint to create a new lecture for a course"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, course_id):
        try:
            teacher = Teacher.objects.get(user=request.user)
            course = get_object_or_404(Course, id=course_id, teacher=teacher)
        except (Teacher.DoesNotExist, Course.DoesNotExist):
            return Response(
                {"error": "Course not found or you don't have permission to access it"},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy() if not hasattr(request.data, 'copy') else request.data.dict()
        data['course'] = course_id

        # Set order if not provided
        if 'order' not in data:
            last_lecture = Lecture.objects.filter(course=course).order_by('-order').first()
            next_order = (last_lecture.order + 1) if last_lecture else 0
            data['order'] = next_order

        serializer = LectureSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            lecture = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
class TeacherCreateResourceAPIView(APIView):
    """
    API endpoint for teachers to create a resource for a specific lecture in their course.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id, lecture_id):
        try:
            # Ensure the user is a teacher
            teacher = getattr(request.user, 'teacher', None)
            if not teacher:
                return Response({"error": "Only teachers can add resources."}, status=status.HTTP_403_FORBIDDEN)

            # Get the course and lecture
            course = Course.objects.get(id=course_id, teacher=teacher)
            lecture = Lecture.objects.get(id=lecture_id, course=course)

            # Prepare data for serializer
            data = request.data.copy()
            data['course'] = course.id
            data['lecture'] = lecture.id

            serializer = api_serializer.CourseResourceSerializer(data=data, context={"request": request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Course.DoesNotExist:
            return Response({"error": "Course not found or not owned by you."}, status=status.HTTP_404_NOT_FOUND)
        except Lecture.DoesNotExist:
            return Response({"error": "Lecture not found in this course."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class TeacherEditResourceAPIView(APIView):
    """
    API endpoint for teachers to edit (update/delete) a resource for a specific lecture in their course.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def put(self, request, course_id, lecture_id, resource_id):
        try:
            # Ensure the user is a teacher
            teacher = getattr(request.user, 'teacher', None)
            if not teacher:
                return Response({"error": "Only teachers can edit resources."}, status=status.HTTP_403_FORBIDDEN)

            # Get the course, lecture, and resource
            course = Course.objects.get(id=course_id, teacher=teacher)
            lecture = Lecture.objects.get(id=lecture_id, course=course)
            resource = CourseResource.objects.get(id=resource_id, course=course, lecture=lecture)

            serializer = api_serializer.CourseResourceSerializer(resource, data=request.data, partial=True, context={"request": request})
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Course.DoesNotExist:
            return Response({"error": "Course not found or not owned by you."}, status=status.HTTP_404_NOT_FOUND)
        except Lecture.DoesNotExist:
            return Response({"error": "Lecture not found in this course."}, status=status.HTTP_404_NOT_FOUND)
        except CourseResource.DoesNotExist:
            return Response({"error": "Resource not found in this lecture."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, course_id, lecture_id, resource_id):
        try:
            teacher = getattr(request.user, 'teacher', None)
            if not teacher:
                return Response({"error": "Only teachers can delete resources."}, status=status.HTTP_403_FORBIDDEN)

            course = Course.objects.get(id=course_id, teacher=teacher)
            lecture = Lecture.objects.get(id=lecture_id, course=course)
            resource = CourseResource.objects.get(id=resource_id, course=course, lecture=lecture)

            resource.delete()
            return Response({"message": "Resource deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

        except Course.DoesNotExist:
            return Response({"error": "Course not found or not owned by you."}, status=status.HTTP_404_NOT_FOUND)
        except Lecture.DoesNotExist:
            return Response({"error": "Lecture not found in this course."}, status=status.HTTP_404_NOT_FOUND)
        except CourseResource.DoesNotExist:
            return Response({"error": "Resource not found in this lecture."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class LectureQuizView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lecture_id):
        try:
            quiz = Quiz.objects.filter(lecture_id=lecture_id).first()
            if quiz:
                return Response({"quiz_id": quiz.id})
            else:
                return Response({"quiz_id": None})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
from django.http import HttpResponse

def generate_certificate(request):
    """
    Generate a certificate image using PIL for a specific user and course
    """
    try:
        # Get user and course information
        user = request.user
        course_id = request.GET.get('course_id')  # Changed from request.query_params.get()
        if not course_id:
                return HttpResponse("Course ID is required", status=400)  # Changed from Response to HttpResponse

            # Fetch course and certificate
        course = get_object_or_404(Course, course_id=course_id)
        certificate = get_object_or_404(Certificate, student=user, course=course)
        
        # Get actual data for the certificate
        recipient_name = user.get_full_name() or user.username
        course_name = course.title
        award_date = timezone.now().strftime('%B %d, %Y')
        certificate_id = certificate.certificate_id
        
        # Load background image
        background_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'Certificate_Bg.png')
        background = Image.open(background_path).convert("RGBA")
        Logo_path = os.path.join(settings.BASE_DIR, 'static', 'logo', 'admin-logo.png')
        Logo = Image.open(Logo_path).convert("RGBA")
        Logo = Logo.resize((150, 150))
        
        # Load fonts
        try:
            font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf')
            font_large = ImageFont.truetype(font_path, 80)
            font_medium = ImageFont.truetype(font_path, 36)
            font_small = ImageFont.truetype(font_path, 24)
        except (IOError, OSError):
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Draw text
        draw = ImageDraw.Draw(background)
        draw.text((800, 680), recipient_name, font=font_large, fill="black")
        draw.text((900, 780), course_name, font=font_medium, fill="black")
        draw.text((900, 920), award_date, font=font_medium, fill="black")
        draw.text((350, 1250), f"Certificate ID: {certificate_id}", font=font_small, fill="black")

        # Get QR code
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=https://bonjourclasse.co.za/verify/{certificate_id}"
        qr_response = requests.get(qr_url)
        qr_img = Image.open(BytesIO(qr_response.content)).convert("RGBA")
        qr_img = qr_img.resize((200, 200))

        # Paste QR code
        background.paste(qr_img, (350, 1025), qr_img)
        background.paste(Logo, (925, 1050), Logo)

        # Save to database - create or update certificate file
        output = BytesIO()
        background.save(output, format='PNG')
        output.seek(0)
        
        # Create or update the certificate file record
        expires_at = timezone.now() + timedelta(days=30)
        cert_file_obj, _ = CertificateFile.objects.update_or_create(
            certificate=certificate,
            defaults={'expires_at': expires_at}
        )
        
        # Save the image to the model's image field
        file_name = f'cert_{certificate_id}'
        cert_file_obj.image.save(f'{file_name}.png', ContentFile(output.getvalue()))
        cert_file_obj.save()
        
        # Return the image directly as an HTTP response
        output.seek(0)
        return HttpResponse(output.getvalue(), content_type="image/png")
    
    except Exception as e:
        return HttpResponse(f"Error generating certificate: {str(e)}", content_type="text/plain", status=500)
from weasyprint import HTML
from pdf2image import convert_from_path
from io import BytesIO
import os

class GetCertificateAPIView(APIView):
    def get(self, request):
        try:
            # Get user and course information
            user = request.user
            course_id = request.GET.get('course_id')
            if not course_id:
                return Response({'error': 'Course ID is required'}, status=400)

            # Fetch course 
            course = get_object_or_404(Course, course_id=course_id)
            
            # Check if certificate exists, otherwise create one
            certificate, created = Certificate.objects.get_or_create(
                student=user, 
                course=course,
                defaults={'certificate_id': f"BC-{user.id}-{course.id}-{timezone.now().strftime('%Y%m%d')}"}
            )
            certificate_id = certificate.certificate_id
            
            # Define file paths - CHANGED FROM 'certificates' to 'certs'
            file_name = f'Cert_{certificate_id}'
            certificates_dir = os.path.join(settings.MEDIA_ROOT, 'certs')
            os.makedirs(certificates_dir, exist_ok=True)
            
            png_path = os.path.join(certificates_dir, f'{file_name}.png')
            pdf_path = os.path.join(certificates_dir, f'{file_name}.pdf')
            
            print(f"Looking for certificate files at: {png_path} and {pdf_path}")
        except Exception as e:
            return Response({'error': f"Failed to prepare certificate: {str(e)}"}, status=500)
            
        try:
          # Get user and course information
            user = request.user
            course_id = request.GET.get('course_id')
            if not course_id:
                return Response({'error': 'Course ID is required'}, status=400)

            # Fetch course and certificate
            course = get_object_or_404(Course, course_id=course_id)
            certificate = get_object_or_404(Certificate, student=user, course=course)
            certificate_id = certificate.certificate_id
            
            # Define file paths - CHANGED FROM 'certificates' to 'certs'
            file_name = f'Cert_{certificate_id}'
            certificates_dir = os.path.join(settings.MEDIA_ROOT, 'certs')
            os.makedirs(certificates_dir, exist_ok=True)
            
            png_path = os.path.join(certificates_dir, f'{file_name}.png')
            pdf_path = os.path.join(certificates_dir, f'{file_name}.pdf')
            
            print(f"Looking for certificate files at: {png_path} and {pdf_path}")
            
            # Check if certificate files already exist
            if os.path.exists(png_path) and os.path.exists(pdf_path):
                print(f"Found existing certificate files for ID: {certificate_id}")
                
                # Files already exist, get or create CertificateFile object
                cert_file_obj, created = CertificateFile.objects.get_or_create(
                    certificate=certificate,
                    defaults={
                        'expires_at': timezone.now() + timedelta(days=30)
                    }
                )
                
                # If the CertificateFile exists but doesn't have file fields populated,
                # attach the existing files from the filesystem
                if not cert_file_obj.file or not cert_file_obj.image:
                    with open(png_path, 'rb') as png_file:
                        cert_file_obj.image.save(f'{file_name}.png', ContentFile(png_file.read()), save=False)
                    
                    with open(pdf_path, 'rb') as pdf_file:
                        cert_file_obj.file.save(f'{file_name}.pdf', ContentFile(pdf_file.read()), save=False)
                    
                    cert_file_obj.save()
                
                return Response({
                    'download_pdf': cert_file_obj.file.url,
                    'download_png': cert_file_obj.image.url,
                    'expiry_date': cert_file_obj.expires_at
                })
            
            # Certificate files don't exist, generate them
            print(f"Generating new certificate for ID: {certificate_id}")
            
            # Get actual data for the certificate
            recipient_name = user.get_full_name() or user.username
            course_name = course.title
            award_date = timezone.now().strftime('%B %d, %Y')
        
            # Load background image
            background_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'Certificate_Bg.png')
            print(f"Looking for background image at: {background_path}")
            background = Image.open(background_path).convert("RGBA")
            
            Logo_path = os.path.join(settings.BASE_DIR, 'static', 'logo', 'admin-logo.png')
            print(f"Looking for logo image at: {Logo_path}")
            Logo = Image.open(Logo_path).convert("RGBA")
            Logo = Logo.resize((150, 150))
        
            # Load fonts
            try:
                font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf')
                font_large = ImageFont.truetype(font_path, 80)
                font_medium = ImageFont.truetype(font_path, 36)
                font_small = ImageFont.truetype(font_path, 24)
            except (IOError, OSError):
                print("Could not load custom fonts, using default")
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()

            # Draw text
            draw = ImageDraw.Draw(background)
            draw.text((800, 680), recipient_name, font=font_large, fill="black")
            draw.text((900, 780), course_name, font=font_medium, fill="black")
            draw.text((900, 920), award_date, font=font_medium, fill="black")
            draw.text((350, 1250), f"Certificate ID: {certificate_id}", font=font_small, fill="black")

            # Get QR code
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=https://bonjourclasse.co.za/verify/{certificate_id}"
            qr_response = requests.get(qr_url)
            qr_img = Image.open(BytesIO(qr_response.content)).convert("RGBA")
            qr_img = qr_img.resize((200, 200))

            # Paste QR code
            background.paste(qr_img, (350, 1025), qr_img)
            background.paste(Logo, (925, 1050), Logo)

            # Save image to BytesIO buffer
            png_buffer = BytesIO()
            background.save(png_buffer, format='PNG', quality=100, dpi=(300, 300))
            png_buffer.seek(0)
            
            # Improved PDF conversion function with rotation
            def image_to_fullpage_pdf(image_bytes):
                # Create a buffer for the PDF
                pdf_buffer = BytesIO()
                
                # Use landscape orientation for the PDF (swap width and height)
                pagesize = (A4[1], A4[0])  # Landscape orientation
                c = canvas.Canvas(pdf_buffer, pagesize=pagesize)
                width, height = pagesize  # Now width is the longer dimension
                
                # Open the image
                if isinstance(image_bytes, BytesIO):
                    image_bytes.seek(0)
                    img = Image.open(image_bytes)
                else:
                    img = Image.open(image_bytes)
                
                # Calculate dimensions to fill the page while maintaining aspect ratio
                img_width, img_height = img.size
                aspect = img_width / img_height
                page_aspect = width / height
                
                if aspect > page_aspect:
                    # Fit to width
                    new_width = width
                    new_height = width / aspect
                else:
                    # Fit to height
                    new_height = height
                    new_width = height * aspect
                
                # Create high-quality resized image
                img_buffer = BytesIO()
                img = img.resize((int(new_width), int(new_height)), Image.LANCZOS)
                img.save(img_buffer, format='PNG', quality=100, dpi=(300, 300))
                img_buffer.seek(0)
                
                # Center the image on the page
                x = (width - new_width) / 2
                y = (height - new_height) / 2
                
                # Use ImageReader for better quality
                c.drawImage(ImageReader(img_buffer), x, y, width=new_width, height=new_height)
                c.showPage()
                c.save()
                
                pdf_buffer.seek(0)
                return pdf_buffer
            
            # Generate PDF from the image
            pdf_buffer = image_to_fullpage_pdf(png_buffer)
        
            # Create or update the certificate file record
            expires_at = timezone.now() + timedelta(days=30)
            cert_file_obj, _ = CertificateFile.objects.update_or_create(
                certificate=certificate,
                defaults={'expires_at': expires_at}
            )
        
            # Save both PNG and PDF to the model's fields
            cert_file_obj.image.save(f'{file_name}.png', ContentFile(png_buffer.getvalue()))
            cert_file_obj.file.save(f'{file_name}.pdf', ContentFile(pdf_buffer.getvalue()))
            cert_file_obj.save()
            
            # Ensure the certs directory exists
            os.makedirs(certificates_dir, exist_ok=True)
            
            # Save files to the filesystem directly in certs directory
            with open(png_path, 'wb') as f:
                f.write(png_buffer.getvalue())
                print(f"Saved PNG to {png_path}")
                
            with open(pdf_path, 'wb') as f:
                f.write(pdf_buffer.getvalue())
                print(f"Saved PDF to {pdf_path}")
            
            return Response({
                'download_pdf': cert_file_obj.file.url,
                'download_png': cert_file_obj.image.url,
                'expiry_date': expires_at
            })
    
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': f"Failed to generate certificate: {str(e)}"}, status=500)

class UserProfilesListAPIView(APIView):
    """API view to list user profiles for messaging with proper access controls"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            current_user = request.user

            if current_user.is_superuser:
                # Superuser: show all users except themselves
                users = User.objects.exclude(id=current_user.id)
            elif hasattr(current_user, 'teacher'):
                # Teachers: see all students enrolled in their courses and other teachers
                teacher_courses = Course.objects.filter(teacher=current_user.teacher)
                enrolled_students = EnrolledCourse.objects.filter(course__in=teacher_courses).values_list('user', flat=True).distinct()
                users = User.objects.filter(
                    models.Q(id__in=enrolled_students) |  
                    models.Q(is_staff=True) |           
                    models.Q(is_superuser=True)          
                ).exclude(id=current_user.id).distinct()
            else:
                # Students: only see teachers of courses they're enrolled in
                enrolled_courses = EnrolledCourse.objects.filter(user=current_user).values_list('course', flat=True)
                teacher_ids = Course.objects.filter(id__in=enrolled_courses).values_list('teacher__user', flat=True).distinct()
                users = User.objects.filter(
                    models.Q(id__in=teacher_ids) |      
                    models.Q(is_staff=True) |           
                    models.Q(is_superuser=True)         
                ).exclude(id=current_user.id).distinct()
            
            # Format the response data
            user_data = []
            for user in users:
                profile_image = None
                try:
                    if hasattr(user, 'profile') and user.profile and user.profile.image:
                        profile_image = request.build_absolute_uri(user.profile.image.url)
                except:
                    pass
                
                full_name = user.get_full_name() or getattr(user, 'full_name', None)
                is_teacher = hasattr(user, 'teacher')
                
                user_data.append({
                    'user_id': user.id,
                    'username': user.username,
                    'full_name': full_name if full_name else None,
                    'profile_picture': profile_image,
                    'email': user.email,
                    'is_teacher': is_teacher,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser
                })
            
            return Response(user_data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error fetching user profiles: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from api.models import Notification
from api.serializer import NotificationSerializer

class UserNotificationList(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        # Only allow users to see their own notifications, or superusers/staff
        if request.user.id != user_id and not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Permission denied."}, status=403)
        notifications = Notification.objects.filter(user_id=user_id).order_by('-date')
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)