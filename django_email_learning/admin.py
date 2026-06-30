from django.contrib import admin

from .models import BlockedEmail, Organization

admin.site.register(Organization)
admin.site.register(BlockedEmail)
