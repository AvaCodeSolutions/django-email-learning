from django.contrib import admin
from .models import Organization, BlockedEmail


admin.site.register(Organization)
admin.site.register(BlockedEmail)
