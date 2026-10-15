from django.urls import path

from .views import BulkSendMessageView, MessageDetailView, MessageListView, RetryMessageView, SendMessageView

app_name = 'messaging'

urlpatterns = [
    path('', MessageListView.as_view(), name='message-list'),
    path('send/', SendMessageView.as_view(), name='message-send'),
    path('bulk-send/', BulkSendMessageView.as_view(), name='message-bulk-send'),
    path('<int:pk>/', MessageDetailView.as_view(), name='message-detail'),
    path('<int:pk>/retry/', RetryMessageView.as_view(), name='message-retry'),
]
