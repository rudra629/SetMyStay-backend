from django.urls import path
from .views import GoogleLoginView, CompleteProfileView, ListUsersView

urlpatterns = [
    path('', ListUsersView.as_view(), name='list-users'),
    path('google-login/', GoogleLoginView.as_view(), name='google-login'),
    path('complete-profile/', CompleteProfileView.as_view(), name='complete-profile'),
]