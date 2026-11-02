from django.urls import path

from .views import ProfileDetailView, ProfileListView, ProfileStateView, UserOptionsView


def profile_urls(kind):
    return [
        path('', ProfileListView.as_view(kind=kind)),
        path('<uuid:profile_id>/', ProfileDetailView.as_view(kind=kind)),
        path('<uuid:profile_id>/activate/', ProfileStateView.as_view(kind=kind, active=True)),
        path('<uuid:profile_id>/deactivate/', ProfileStateView.as_view(kind=kind, active=False)),
    ]


professional_urls = [path('users/', UserOptionsView.as_view()), *profile_urls('professionals')]
specialty_urls = profile_urls('specialties')
