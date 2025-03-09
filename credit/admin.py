from django.contrib import admin
from credit.models import CreditSettings, Credit, Guarantor

@admin.register(CreditSettings)
class CreditSettingsAdmin(admin.ModelAdmin):
    list_display = ("max_repayment_months", "savings_credit_ratio", "last_updated", "updated_by")
    list_filter = ("last_updated",)
    search_fields = ("updated_by__email",)

@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    list_display = ("id", "applicant", "credit_type", "amount_requested", "status", "date_applied")
    list_filter = ("status", "credit_type", "date_applied")
    search_fields = ("applicant__email", "tracking_id")
    readonly_fields = ("id", "tracking_id", "date_applied")

@admin.register(Guarantor)
class GuarantorAdmin(admin.ModelAdmin):
    list_display = ("id", "guarantor", "credit", "status", "action_date")
    list_filter = ("status", "action_date")
    search_fields = ("guarantor__email", "credit__id")

from credit.models import Murabaha, Musharaka, Ijarah, Repayment, TransactionLog, CreditCommittee, CommitteeAction

@admin.register(Murabaha)
class MurabahaAdmin(admin.ModelAdmin):
    list_display = ("id", "credit", "asset_name", "asset_price", "profit_margin", "selling_price", "created_at")
    search_fields = ("id", "credit__id", "asset_name")
    list_filter = ("created_at",)
    readonly_fields = ("selling_price", "profit_margin")  # Auto-calculated fields


@admin.register(Musharaka)
class MusharakaAdmin(admin.ModelAdmin):
    list_display = ("id", "credit", "partner_contribution", "profit_sharing_ratio", "created_at")
    search_fields = ("id", "credit__id")
    list_filter = ("created_at",)


@admin.register(Ijarah)
class IjarahAdmin(admin.ModelAdmin):
    list_display = ("id", "credit", "asset_name", "lease_period", "rental_amount", "created_at")
    search_fields = ("id", "credit__id", "asset_name")
    list_filter = ("created_at",)


@admin.register(Repayment)
class RepaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "credit", "amount", "repayment_method", "status", "repayment_date")
    search_fields = ("id", "credit__id")
    list_filter = ("status", "repayment_method", "repayment_date")


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = ("id", "credit", "transaction_type", "amount", "transaction_date")
    search_fields = ("id", "credit__id")
    list_filter = ("transaction_type", "transaction_date")


@admin.register(CreditCommittee)
class CreditCommitteeAdmin(admin.ModelAdmin):
    list_display = ("id", "member", "role", "date_added")
    search_fields = ("id", "member__email", "role")
    list_filter = ("role", "date_added")


@admin.register(CommitteeAction)
class CommitteeActionAdmin(admin.ModelAdmin):
    list_display = ("id", "committee_member", "credit", "action_taken", "action_date")
    search_fields = ("id", "committee_member__member__email", "credit__id")
    list_filter = ("action_taken", "action_date")

