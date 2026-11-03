from django.urls import path

from .api import AbsenceView, ShiftView, WeekView


urlpatterns = [
    path('<uuid:professional_id>/week/', WeekView.as_view()),
    path('<uuid:professional_id>/shifts/', ShiftView.as_view()),
    path('<uuid:professional_id>/shifts/<int:shift_id>/', ShiftView.as_view()),
    path('<uuid:professional_id>/absences/', AbsenceView.as_view()),
]
