from api import views as api_views
from django.urls import path, re_path

from rest_framework_simplejwt.views import TokenRefreshView
from .views import get_video_metadata, serve_video, stream_video, StudentQuizListAPIView
from api.views import (
    StudentQuizzesView,
    TeacherQuizzesView,
    QuizDetailView,
    CreateQuizView,
    UpdateQuizView,
    QuizSubmissionView,)
from .views import UploadCertificateBackground

urlpatterns = [
    # Authentication Endpoints

    path("user/token/", api_views.MyTokenObtainPairView.as_view()),
    path("user/token/refresh/", TokenRefreshView.as_view()),
    path("user/register/", api_views.RegisterView.as_view()),
    path("user/password-change/", api_views.PasswordChangeAPIView.as_view()),
    path("user/profile/<user_id>/", api_views.ProfileAPIView.as_view()),
    path("user/change-password/<str:email>/", api_views.PasswordChangeAPIView.as_view(), name="change-password"), 
    path("user/request-otp/", api_views.RequestOTPAPIView.as_view(), name="request-otp"),  # Endpoint to request OTP
    path("user/verify-otp/", api_views.VerifyOtpAPIView.as_view(), name="verify-otp"),  # Endpoint to verify OTP
    path("user/verify-otp/<str:email>/", api_views.VerifyOtpAPIView.as_view(), name="verify-otp"),  # Endpoint to verify OTP with email
    path("user/password-reset-with-otp/", api_views.PasswordResetAPIView.as_view(), name="password-reset-with-otp"),  # Password reset using OTP
    path('user/appearance-settings/', api_views.UserAppearanceSettingsView.as_view(), name='user-appearance-settings'),

    # Email Settings Endpoint
    path("email-settings/", api_views.EmailSettingsViewSet.as_view({'get': 'list', 'post': 'create'})),
    path("email-settings/<int:pk>/", api_views.EmailSettingsViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'})),
    path("events/", api_views.EventViewSet.as_view({'get': 'list', 'post': 'create'})),
    path('events/', api_views.EventViewSet.as_view({'get': 'list', 'post': 'create'}), name='event-list'),
    
    # Core Endpoints
    path("course/category/", api_views.CategoryListAPIView.as_view()),
    path("course/course-list/", api_views.CourseListAPIView.as_view()),
    path("course/search/", api_views.SearchCourseAPIView.as_view()),
    path("course/course-detail/<slug>/", api_views.CourseDetailAPIView.as_view()),
    path("course/cart/", api_views.CartAPIView.as_view()),
    path("course/cart-list/<cart_id>/", api_views.CartListAPIView.as_view()),
    path("cart/stats/<cart_id>/", api_views.CartStatsAPIView.as_view()),
    path("course/cart-item-delete/<cart_id>/<item_id>/", api_views.CartItemDeleteAPIView.as_view()),
    path("order/create-order/", api_views.CreateOrderAPIView.as_view()),
    path("order/checkout/<oid>/", api_views.CheckoutAPIView.as_view()),
    path("order/coupon/", api_views.CouponApplyAPIView.as_view()),
    path("payment/create-checkout/", api_views.create_yoco_checkout, name="create-yoco-checkout"),
    path("payment/yoco-webhook/", api_views.yoco_webhook_handler, name="yoco-webhook"),

    # Student API Endpoints
    path("student/summary/<user_id>/", api_views.StudentSummaryAPIView.as_view()),
    path("student/course-list/<user_id>/", api_views.StudentCourseListAPIView.as_view()),
    path("student/course-detail/<user_id>/<enrollment_id>/", api_views.StudentCourseDetailAPIView.as_view()),
    path("student/course-completed/", api_views.StudentCourseCompletedCreateAPIView.as_view()),
    path("student/course-note/<user_id>/<enrollment_id>/", api_views.StudentNoteCreateAPIView.as_view()),
    path("student/course-note-detail/<user_id>/<enrollment_id>/<note_id>/", api_views.StudentNoteDetailAPIView.as_view()),
    path("student/rate-course/", api_views.StudentRateCourseCreateAPIView.as_view()),
    path("student/review-detail/<user_id>/<review_id>/", api_views.StudentRateCourseUpdateAPIView.as_view()),
    path("student/wishlist/<user_id>/", api_views.StudentWishListListCreateAPIView.as_view()),
    path("student/question-answer-list-create/<course_id>/", api_views.QuestionAnswerListCreateAPIView.as_view()),
    path("student/question-answer-message-create/", api_views.QuestionAnswerMessageSendAPIView.as_view()),
    path("course/<int:course_id>/lectures/", api_views.CourseLecturesAPIView.as_view(), name="course-lectures"),
    path('lecture/<int:lecture_id>/video-metadata/', get_video_metadata, name='video-metadata'),
    path('api/stream-video/<path:path>', stream_video, name='stream-video'),
    path('lecture/<int:lecture_id>/progress/', api_views.VideoProgressAPIView.as_view(), name='lecture-progress'),
    path('course/<int:course_id>/progress/', api_views.CourseProgressAPIView.as_view(), name='course-progress'),
    path('student/<int:user_id>/progress/', api_views.StudentProgressView.as_view(), name='student-progress'),
    path('lecture/<int:lecture_id>/quiz/', api_views.LectureQuizView.as_view(), name='lecture-quiz'),
    path('notifications/user/<int:user_id>/', api_views.UserNotificationList.as_view(), name='user-notification-list'),
    
    # Course Resources endpoints
    path("course/<int:course_id>/resources/", api_views.CourseResourceListCreateAPIView.as_view(), name="course-resources"),
    path("resources/<int:resource_id>/", api_views.CourseResourceDetailAPIView.as_view(), name="resource-detail"),
    path("resources/", api_views.CourseResourceDetailAPIView.as_view(), name="resource-detail"),
    path("course/<int:course_id>/lecture/<int:lecture_id>/resources/", api_views.LectureResourceListAPIView.as_view(), name="lecture-resources"),
    path("resources/<int:resource_id>/download/", api_views.download_resource, name="download-resource"),
    # Teacher Routes
    path("teacher/summary/<teacher_id>/", api_views.TeacherSummaryAPIView.as_view()),
    path("teacher/course-lists/<teacher_id>/", api_views.TeacherCourseListAPIView.as_view()),
    path("teacher/review-lists/<teacher_id>/", api_views.TeacherReviewListAPIView.as_view()),
    path("teacher/review-detail/<teacher_id>/<review_id>/", api_views.TeacherReviewDetailAPIView.as_view()),
    path("teacher/student-lists/<teacher_id>/", api_views.TeacherStudentsListAPIVIew.as_view({'get': 'list'})),
    path("teacher/all-months-earning/<teacher_id>/", api_views.TeacherAllMonthEarningAPIView),
    path("teacher/best-course-earning/<teacher_id>/", api_views.TeacherBestSellingCourseAPIView.as_view({'get': 'list'})),
    path("teacher/course-order-list/<teacher_id>/", api_views.TeacherCourseOrdersListAPIView.as_view()),
    path("teacher/question-answer-list/<teacher_id>/", api_views.TeacherQuestionAnswerListAPIView.as_view()),
    path("teacher/coupon-list/<teacher_id>/", api_views.TeacherCouponListCreateAPIView.as_view()),
    path("teacher/coupon-detail/<teacher_id>/<coupon_id>/", api_views.TeacherCouponDetailAPIView.as_view()),
    path("teacher/noti-list/<teacher_id>/", api_views.TeacherNotificationListAPIView.as_view()),
    path("teacher/noti-detail/<teacher_id>/<noti_id>", api_views.TeacherNotificationDetailAPIView.as_view()),
    path("teacher/course-create/", api_views.CourseCreateAPIView.as_view()),
    path("teacher/course-update/<teacher_id>/<course_id>/", api_views.CourseUpdateAPIView.as_view()),
    path("teacher/course-detail/<course_id>/", api_views.CourseDetailAPIView.as_view()),
    path("teacher/course/variant-delete/<variant_id>/<teacher_id>/<course_id>/", api_views.CourseVariantDeleteAPIView.as_view()),
    path("teacher/course/variant-item-delete/<variant_id>/<variant_item_id>/<teacher_id>/<course_id>/", api_views.CourseVariantItemDeleteAPIVIew.as_view()),
    path("student/unbought-courses/<user_id>/", api_views.UnboughtCoursesAPIView.as_view(), name="unbought-courses"),
    path("payment/test-webhook/", api_views.test_webhook_setup, name="test-webhook"),

    # Subscription API
    path("subscription/", api_views.SubscriptionAPIView.as_view(), name="subscription"),
    path('subscription/add-courses/', api_views.AddSubscriptionCoursesToLibraryAPIView.as_view(), name='add_subscription_courses'),
    path("subscription-packages/", api_views.SubscriptionPackageAPIView.as_view(), name="subscription-packages"),
    path('landingpage/subscription-packages/', api_views.LandingPageSubscriptionPackageAPIView.as_view(), name='landingpage-subscription-packages'),
    
    # Student assignment endpoints
    path('student/assignments/<int:user_id>/', api_views.StudentAssignmentsView.as_view(), name='student-assignments'),
    path('student/assignment-submission/', api_views.AssignmentSubmissionView.as_view(), name='submit-assignment'),
    path('student/assignment-submission/<int:assignment_id>/', api_views.AssignmentSubmissionView.as_view(), name='get-submission'),
    path('student/assignment-test-log/', api_views.AssignmentTestLogView.as_view(), name='create-test-log'),
    path('student/assignment/<int:assignment_id>/', api_views.StudentAssignmentDetailView.as_view(), name='student-assignment-detail'),

    # Teacher assignment endpoints
    
    path('teacher/assignments/<int:course_id>/', api_views.TeacherAssignmentView.as_view(), name='teacher-course-assignments'),
    path('teacher/assignment-submissions/<int:assignment_id>/', api_views.TeacherSubmissionsView.as_view(), name='assignment-submissions'),
    path('teacher/grade-submission/<int:submission_id>/', api_views.GradeSubmissionView.as_view(), name='grade-submission'),
    path('teacher/assignment-test-logs/<int:assignment_id>/', api_views.AssignmentTestLogView.as_view(), name='test-logs'),
    path('teacher/assignment-file/<int:file_id>/', api_views.AssignmentFileDeleteView.as_view(), name='delete-assignment-file'),
    path('teacher/assignment/', api_views.create_assignment, name='create-assignment'),
    path('teacher/assignment/<int:assignment_id>/', api_views.update_assignment, name='update-assignment'),

    # Add this new URL pattern for video serving
    path('media/lectures/<path:path>', serve_video, name='serve_video'),
    path('media/resources/<path:path>', serve_video, name='serve_video'),
    path('media/<path:path>', serve_video, name='serve_media'),

    #certificate URLs
    path('certificates/generate/', api_views.generate_certificate, name='generate-certificate'),
    path('certificates/get/', api_views.GetCertificateAPIView.as_view(), name='get-certificate'),

    # Messaging URLs
    path('conversations/', api_views.ConversationList.as_view(), name='conversation-list'),
    path('conversations/<int:pk>/', api_views.ConversationDetail.as_view(), name='conversation-detail'),
    path('messages/', api_views.MessageCreate.as_view(), name='message-create'),
    path('users/profiles/', api_views.UserProfilesListAPIView.as_view(), name='user-profile-list'),

    # Notification URLs
    path('notifications/', api_views.NotificationList.as_view(), name='notification-list'),
    path('notifications/<int:pk>/read/', api_views.mark_notification_read, name='notification-read'),
    path('notifications/read-all/', api_views.mark_all_notifications_read, name='notification-read-all'),

    # Teacher-specific URLs
    path('teacher/conversations/', api_views.TeacherStudentConversations.as_view(), name='teacher-conversations'),
    path('student/quiz-list/<int:user_id>/', api_views.StudentQuizListAPIView.as_view(), name='student-quiz-list'),
    path("teacher/dashboard/<int:teacher_id>/", api_views.TeacherDashboardAPIView.as_view(), name="teacher-dashboard"),
    path('student/track-lecture-completion/', api_views.TrackLectureCompletionView.as_view(), name='track-lecture-completion'),
    path('lecture-quiz-association/', api_views.LectureQuizAssociationView.as_view(), name='lecture-quiz-association'),
    path('teacher/submit-event/', api_views.TeacherSubmitEvent.as_view(), name='teacher-submit-event'),
    path('events/allowed-platforms/', api_views.AllowedEventPlatforms.as_view(), name='allowed-platforms'),
    path('groups/', api_views.GroupsAndUsersView.as_view(), name='groups-and-users'),
    
   
    path('teacher/assignment/', api_views.create_assignment, name='create-assignment'),
    path('teacher/assignment/<int:assignment_id>/', api_views.update_assignment, name='update-assignment'),
    path('teacher/assignment/<int:assignment_id>/get/', api_views.get_assignment, name='get-assignment'),
    path('teacher/assignments/all/<int:teacher_id>/', api_views.teacher_assignments_all, name='get-all-assignments'),
    path('student/quizzes/<int:user_id>/', api_views.StudentQuizzesView.as_view(), name='student-quizzes'),
    path('teacher/quizzes/<int:course_id>/', api_views.TeacherQuizzesView.as_view(), name='teacher-quizzes'),
    path('quizzes/<int:quiz_id>/', api_views.QuizDetailView.as_view(), name='quiz-detail'),
    path('quizzes/create/', api_views.CreateQuizView.as_view(), name='create-quiz'),
    path('quizzes/<int:quiz_id>/update/', api_views.UpdateQuizView.as_view(), name='update-quiz'),
    path('quizzes/submit/', api_views.QuizSubmissionView.as_view(), name='submit-quiz'),
    path('teacher/quizzes/all/<int:teacher_id>/', api_views.teacher_quizzes_all, name='get-all-quizzes'),
    path('student/quiz/<int:quiz_id>/', api_views.StudentQuizDetailView.as_view(), name='student-quiz-detail'),
    path('student/quiz-answer-check/', api_views.QuizAnswerCheckView.as_view(), name='quiz-answer-check'),
    path('events/<int:pk>/', api_views.EventViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='event-detail'),
    path('teacher/courses/', api_views.TeacherAllCoursesView.as_view(), name='teacher-courses'),
    path('teacher/course/<int:course_id>/lectures/', api_views.TeacherLectureListView.as_view(), name='teacher-course-lectures'),
    path('teacher/lecture/<int:lecture_id>/', api_views.TeacherLectureDetailView.as_view(), name='teacher-lecture-detail'),
    path('teacher/course/<int:course_id>/lecture-order/', api_views.LectureOrderUpdateView.as_view(), name='lecture-order-update'),
    path('teacher/course/<int:course_id>/', api_views.TeacherCourseDeleteAPIView.as_view(), name='delete-teacher-courses'),
    path('teacher/course/<int:course_id>/lecture-create/', api_views.LectureCreateAPIView.as_view(), name='teacher-lecture-create'),
    path('teacher/course/<int:course_id>/<int:lecture_id>/resources/create/',api_views.TeacherCreateResourceAPIView.as_view(), name='teacher-course-resource-create'),
    path('teacher/course/<int:course_id>/<int:lecture_id>/resources/<int:resource_id>/',api_views.TeacherEditResourceAPIView.as_view(), name='teacher-course-resource-update'),
    path('upload-background/', UploadCertificateBackground.as_view(), name='upload-background'),
]






