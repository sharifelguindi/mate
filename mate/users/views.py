from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

# Removed tenant imports - tenants now handled at AWS deployment level
from mate.users.forms import FirstLoginPasswordChangeForm
from mate.users.models import User


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


@login_required
def first_login_password_change(request):
    """Force password change on first login."""
    # Check if user has force_password_change flag
    if (
        hasattr(request.user, "force_password_change")
        and not request.user.force_password_change
    ):
        return redirect("home")

    if request.method == "POST":
        form = FirstLoginPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            form.save()
            # Update session to prevent logout
            update_session_auth_hash(request, request.user)
            messages.success(request, _("Your password has been changed successfully!"))
            return redirect("home")
    else:
        form = FirstLoginPasswordChangeForm(request.user)

    return render(
        request,
        "users/first_login_password_change.html",
        {"form": form},
    )


# Hospital/Tenant views removed - multi-tenancy now handled at AWS deployment level
# Each deployment will be a separate instance for a specific hospital/organization
