from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or request.user.is_staff


class IsSeller(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff
                 or (request.user.account_type == "SELLER" and request.user.seller.is_approved))
        )

    def has_object_permission(self, request, view, obj):
        return obj.seller == request.user.seller or request.user.is_staff


class IsAdminOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsBuyer(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)
