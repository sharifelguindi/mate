from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.http import Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import ListView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from mate.tenants.models import TenantUser
from mate.users.forms import CreateHospitalUserForm
from mate.users.forms import FirstLoginPasswordChangeForm
from mate.users.forms import UpdateHospitalUserForm
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

    def get_object(self, queryset: QuerySet | None=None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self) -> str:
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


def debug_vite_settings(request):
    """Debug view for django-vite configuration."""
    # Access vite configuration directly from Django settings
    vite_config = settings.DJANGO_VITE.get("default", {})

    return JsonResponse({
        "DEBUG": settings.DEBUG,
        "DJANGO_VITE": settings.DJANGO_VITE,
        "dev_mode": vite_config.get("dev_mode", False),
        "dev_server_host": vite_config.get("dev_server_host", "localhost"),
        "dev_server_port": vite_config.get("dev_server_port", 5173),
    })


# Hospital User Management Views
class HospitalAdminMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to ensure user is a hospital admin for their tenant."""

    def test_func(self):
        return (
            hasattr(self.request, "tenant_user") and
            self.request.tenant_user.role == "hospital_admin"
        )

    def handle_no_permission(self):
        messages.error(
            self.request,
            _("You must be a hospital administrator to access this page."),
        )
        return redirect("users:redirect")


class HospitalUserListView(HospitalAdminMixin, ListView):
    """List all users in the hospital."""
    model = TenantUser
    template_name = "users/hospital_user_list.html"
    context_object_name = "tenant_users"
    paginate_by = 25

    def get_queryset(self):
        return TenantUser.objects.filter(
            tenant=self.request.tenant,
        ).select_related("user", "supervisor").order_by("user__name", "user__email")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tenant"] = self.request.tenant
        context["role_counts"] = {}

        # Count users by role
        for role_code, role_name in TenantUser.role.field.choices:
            count = self.get_queryset().filter(role=role_code).count()
            context["role_counts"][role_name] = count

        return context


hospital_user_list_view = HospitalUserListView.as_view()


class HospitalUserCreateView(HospitalAdminMixin, SuccessMessageMixin, CreateView):
    """Create a new user in the hospital."""
    form_class = CreateHospitalUserForm
    template_name = "users/hospital_user_form.html"
    success_message = _("User %(name)s has been created successfully.")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant"] = self.request.tenant
        kwargs["created_by"] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse("users:hospital-user-list")

    def form_valid(self, form):
        response = super().form_valid(form)

        # Show additional message with login instructions
        if form.cleaned_data.get("auth_method") == "local":
            messages.info(
                self.request,
                _("Temporary password: %s - Please share this securely with the user.")
                % form.temp_password,
            )

        return response


hospital_user_create_view = HospitalUserCreateView.as_view()


class HospitalUserUpdateView(HospitalAdminMixin, SuccessMessageMixin, UpdateView):
    """Update a hospital user."""
    form_class = UpdateHospitalUserForm
    template_name = "users/hospital_user_form.html"
    success_message = _("User %(name)s has been updated successfully.")

    def get_object(self):
        return get_object_or_404(
            TenantUser,
            tenant=self.request.tenant,
            user__username=self.kwargs["username"],
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["tenant_user"] = self.get_object()
        # Pass the User instance to the form
        kwargs["instance"] = self.get_object().user
        return kwargs

    def get_success_url(self):
        return reverse("users:hospital-user-list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["tenant_user"] = self.get_object()
        context["is_update"] = True
        return context


hospital_user_update_view = HospitalUserUpdateView.as_view()


# Password Change Views
@login_required
def first_login_password_change(request):
    """Force password change on first login."""
    # Check if user actually needs to change password
    if not request.user.should_force_password_change():
        return redirect("users:redirect")

    if request.method == "POST":
        form = FirstLoginPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Keep user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, _("Your password has been set successfully."))

            # Redirect to where they were trying to go
            next_url = request.GET.get("next", reverse("users:redirect"))
            return redirect(next_url)
    else:
        form = FirstLoginPasswordChangeForm(request.user)

    return render(request, "users/first_login_password_change.html", {
        "form": form,
        "user": request.user,
    })


# Hospital User Detail View (for viewing user info)
class HospitalUserDetailView(LoginRequiredMixin, DetailView):
    """View details of a hospital user."""
    model = TenantUser
    template_name = "users/hospital_user_detail.html"
    context_object_name = "tenant_user"

    def get_object(self):
        tenant_user = get_object_or_404(
            TenantUser,
            tenant=self.request.tenant,
            user__username=self.kwargs["username"],
        )

        # Hospital admins can view anyone
        # Others can only view themselves
        if (self.request.tenant_user.role != "hospital_admin" and
            tenant_user.user != self.request.user):
            raise Http404

        return tenant_user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add supervised users if applicable
        if self.object.is_supervisor:
            context["supervised_users"] = TenantUser.objects.filter(
                supervisor=self.object,
                tenant=self.request.tenant,
            ).select_related("user")

        return context


hospital_user_detail_view = HospitalUserDetailView.as_view()

