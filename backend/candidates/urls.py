from django.urls import path

from .views import (
    CandidateBulkDeleteView,
    CandidateDetailView,
    CandidateListCreateView,
    CandidateMessageListView,
)

app_name = 'candidates'

urlpatterns = [
    path('', CandidateListCreateView.as_view(), name='candidate-list'),
    path('bulk-delete/', CandidateBulkDeleteView.as_view(), name='candidate-bulk-delete'),
    path('<int:pk>/', CandidateDetailView.as_view(), name='candidate-detail'),
    path('<int:pk>/messages/', CandidateMessageListView.as_view(), name='candidate-messages'),
]
