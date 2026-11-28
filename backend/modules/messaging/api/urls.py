from django.urls import path

from .views import ConnectionView, TemplateListView, TemplateSyncView, TestMessageView, WhatsAppWebhookView

urlpatterns = [
    path('whatsapp/webhook/', WhatsAppWebhookView.as_view(), name='messaging-whatsapp-webhook'),
    path('whatsapp/connection/', ConnectionView.as_view(), name='messaging-whatsapp-connection'),
    path('whatsapp/test-message/', TestMessageView.as_view(), name='messaging-whatsapp-test-message'),
    path('whatsapp/templates/', TemplateListView.as_view(), name='messaging-whatsapp-templates'),
    path('whatsapp/templates/sync/', TemplateSyncView.as_view(), name='messaging-whatsapp-templates-sync'),
]
