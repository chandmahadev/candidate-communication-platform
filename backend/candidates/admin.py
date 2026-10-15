from django.contrib import admin

from .models import Candidate, Message, MessageStatusEvent


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['id', 'code', 'name', 'email', 'phone', 'created_at']
    search_fields = ['code', 'name', 'email', 'phone']
    readonly_fields = ['code', 'created_at', 'updated_at']


class MessageStatusEventInline(admin.TabularInline):
    model = MessageStatusEvent
    extra = 0
    can_delete = False
    readonly_fields = ['provider_event_id', 'previous_status', 'new_status', 'occurred_at', 'received_at']
    fields = readonly_fields


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'candidate', 'status', 'attempt', 'error_code', 'created_at']
    list_filter = ['status', 'is_retryable']
    search_fields = ['provider_message_id', 'candidate__name', 'candidate__email']
    readonly_fields = ['created_at', 'sent_at', 'updated_at']
    inlines = [MessageStatusEventInline]


@admin.register(MessageStatusEvent)
class MessageStatusEventAdmin(admin.ModelAdmin):
    list_display = ['provider_event_id', 'message', 'previous_status', 'new_status', 'occurred_at']
    list_filter = ['new_status']
    search_fields = ['provider_event_id', 'message__provider_message_id']
