from django.urls import path
from .views import RegisterView, LoginView, ProfileView, LogoutView, SchoolListView
from .admin_views import AdminCreateStudentView, AdminCreateParentView, LinkGuardianView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('schools/', SchoolListView.as_view(), name='schools'),
    path('admin/students/', AdminCreateStudentView.as_view(), name='admin-students'),
    path('admin/parents/', AdminCreateParentView.as_view(), name='admin-parents'),
    path('admin/link/', LinkGuardianView.as_view(), name='admin-link-guardian'),
]
