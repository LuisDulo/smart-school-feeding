from rest_framework.permissions import BasePermission


class IsSchoolAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and
                    request.user.is_authenticated and
                    request.user.role == 'admin')


class IsKitchenStaff(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and
                    request.user.is_authenticated and
                    request.user.role == 'kitchen')


class IsBursar(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and
                    request.user.is_authenticated and
                    request.user.role == 'bursar')


class IsParentOrStudent(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and
                    request.user.is_authenticated and
                    request.user.role in ['parent', 'student'])


class IsAdminOrBursar(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and
                    request.user.is_authenticated and
                    request.user.role in ['admin', 'bursar'])


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and
                    request.user.is_authenticated and
                    request.user.role == 'superadmin')


class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and
                    request.user.is_authenticated and
                    request.user.role in ['superadmin', 'admin'])
