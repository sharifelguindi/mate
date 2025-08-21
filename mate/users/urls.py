from django.urls import path

from .views import debug_vite_settings
from .views import first_login_password_change
from .views import hospital_user_create_view
from .views import hospital_user_detail_view
from .views import hospital_user_list_view
from .views import hospital_user_update_view
from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("debug-vite/", view=debug_vite_settings, name="debug_vite"),

    # Hospital user management
    path("hospital/users/", view=hospital_user_list_view, name="hospital-user-list"),
    path(
        "hospital/users/create/",
        view=hospital_user_create_view,
        name="hospital-user-create",
    ),
    path(
        "hospital/users/<str:username>/",
        view=hospital_user_detail_view,
        name="hospital-user-detail",
    ),
    path(
        "hospital/users/<str:username>/edit/",
        view=hospital_user_update_view,
        name="hospital-user-update",
    ),

    # Password change
    path(
        "password/first-login/",
        view=first_login_password_change,
        name="first-login-password-change",
    ),

    # Keep original user detail at the end
    path("<str:username>/", view=user_detail_view, name="detail"),
]

