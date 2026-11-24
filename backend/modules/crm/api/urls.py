from django.urls import path

from .views import (BoardArchiveView, BoardDetailView, BoardListCreateView, BoardReactivateView, StageArchiveView,
                    StageCreateView, StageDetailView, StageOrderView)

urlpatterns = [
    path('', BoardListCreateView.as_view(), name='crm-board-list'),
    path('<uuid:board_id>/', BoardDetailView.as_view(), name='crm-board-detail'),
    path('<uuid:board_id>/archive/', BoardArchiveView.as_view(), name='crm-board-archive'),
    path('<uuid:board_id>/reactivate/', BoardReactivateView.as_view(), name='crm-board-reactivate'),
    path('<uuid:board_id>/stages/', StageCreateView.as_view(), name='crm-stage-create'),
    path('<uuid:board_id>/stages/order/', StageOrderView.as_view(), name='crm-stage-order'),
    path('<uuid:board_id>/stages/<uuid:stage_id>/', StageDetailView.as_view(), name='crm-stage-detail'),
    path('<uuid:board_id>/stages/<uuid:stage_id>/archive/', StageArchiveView.as_view(), name='crm-stage-archive'),
]
