from django.contrib import admin
from withdrawal.models import Charges, Withdrawals, EmployeeAccountDetails

@admin.register(Charges)
class ChargesAdmin(admin.ModelAdmin):
    list_display = ('id', 'charge_percentage', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('id',)
    ordering = ('-created_at',)

@admin.register(Withdrawals)
class WithdrawalsAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'amount_requested', 'status', 'request_date', 'action_date', 'payment_date')
    list_filter = ('status',)
    search_fields = ('id', 'employee__email')
    ordering = ('-request_date',)
    readonly_fields = ('id', 'request_date', 'action_date', 'payment_date')

@admin.register(EmployeeAccountDetails)
class EmployeeAccountDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'bank_name', 'account_number', 'account_holder_name')
    search_fields = ('employee__email', 'bank_name', 'account_number')
    ordering = ('bank_name',)

