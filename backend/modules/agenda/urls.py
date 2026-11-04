from django.urls import path

from .api import AbsenceDetailView, AbsenceView, ShiftView, WeekView
from .appointments_api import (
    AppointmentActionView, AppointmentDetailView, AppointmentListCreateView, FreeSlotsView,
)


urlpatterns = [
    path('appointments/', AppointmentListCreateView.as_view()),
    path('appointments/free-slots/', FreeSlotsView.as_view()),
    path('appointments/<uuid:appointment_id>/', AppointmentDetailView.as_view()),
    path('appointments/<uuid:appointment_id>/confirm/', AppointmentActionView.as_view(action='confirm')),
    path('appointments/<uuid:appointment_id>/reschedule/', AppointmentActionView.as_view(action='reschedule')),
    path('appointments/<uuid:appointment_id>/cancel/', AppointmentActionView.as_view(action='cancel')),
    path('appointments/<uuid:appointment_id>/attend/', AppointmentActionView.as_view(action='attend')),
    path('appointments/<uuid:appointment_id>/no-show/', AppointmentActionView.as_view(action='no_show')),
    path('<uuid:professional_id>/week/', WeekView.as_view()),
    path('<uuid:professional_id>/shifts/', ShiftView.as_view()),
    path('<uuid:professional_id>/shifts/<int:shift_id>/', ShiftView.as_view()),
    path('<uuid:professional_id>/absences/', AbsenceView.as_view()),
    path('<uuid:professional_id>/absences/<int:absence_id>/', AbsenceDetailView.as_view()),
]
