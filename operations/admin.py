from django.contrib import admin
from operations.models import (
    CustomUser, ContributionSetting, ContributionSettingHistory,
    ContributionChangeRequest, ContributionRecord, TargetSavings,
    TargetSavingsTransaction
)

# Registering models in the Django Admin
admin.site.register(ContributionSetting)
admin.site.register(ContributionSettingHistory)
admin.site.register(ContributionChangeRequest)
admin.site.register(ContributionRecord)
admin.site.register(TargetSavings)
admin.site.register(TargetSavingsTransaction)