from django.urls import path

from .views import first_login_password_change
from .views import user_detail_view
from .views import user_redirect_view
from .views import user_update_view

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    # Password change
    path(
        "password/first-login/",
        view=first_login_password_change,
        name="first-login-password-change",
    ),
    # Keep original user detail at the end
    path("<str:username>/", view=user_detail_view, name="detail"),
]
