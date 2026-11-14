from django.urls import path

from .views import (
    ChangePasswordView,
    CurrentUserView,
    LoginView,
    LogoutView,
    RefreshView,
    RegisterView,
)


app_name = "accounts"

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path("password/", ChangePasswordView.as_view(), name="change_password"),
]
