"""Middleware for user authentication and password management."""
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin


class ForcePasswordChangeMiddleware(MiddlewareMixin):
    """
    Middleware to force password change on first login.
    Redirects users with force_password_change=True to password change page.
    """

    # URLs that should be accessible even when password change is required
    ALLOWED_PATHS = [
        "/accounts/logout/",
        "/users/password/first-login/",
        "/static/",
        "/media/",
        "/__debug__/",
    ]

    def process_request(self, request):
        """Check if user needs to change password."""
        # Skip for anonymous users
        if not request.user.is_authenticated:
            return None

        # Skip if user doesn't need password change
        if not request.user.should_force_password_change():
            return None

        # Allow certain paths
        for allowed_path in self.ALLOWED_PATHS:
            if request.path.startswith(allowed_path):
                return None

        # Allow the password change URL itself
        password_change_url = reverse("users:first-login-password-change")
        if request.path == password_change_url:
            return None

        # Redirect to password change with next parameter
        next_url = request.get_full_path()
        return redirect(f"{password_change_url}?next={next_url}")

