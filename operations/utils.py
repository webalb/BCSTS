from django.db.models import Sum
from decimal import Decimal
from operations.models import ContributionRecord
from withdrawal.models import Withdrawals
from credit.models import Credit

def get_employee_financial_summary(employee):
    """
    Returns:
    - total_contributions (100%)
    - savings_balance (60% of contributions - paid withdrawals)
    - investment_balance (40% of contributions)
    - total_remained_balance (contributions - withdrawals)
    """
    total_contributions = ContributionRecord.objects.filter(
        employee=employee, status='paid'
    ).aggregate(total=Sum('amount'))['total'] or Decimal(0.00)

    disbursed_credits = Credit.objects.filter(applicant=employee, status='Disbursed').aggregate(total=Sum('amount_requested'))['total'] or Decimal(0.00)
    repaid_credits = Credit.objects.filter(applicant=employee, status='Repaid').aggregate(total=Sum('amount_repaid'))['total'] or Decimal(0.00)

    # Ensure the method returns a Decimal, not None
    total_paid_withdrawals = Withdrawals.get_employee_total_paid_withdrawals(employee) or Decimal(0.00)

    # Calculate balances
    savings_balance = (Decimal(0.60) * total_contributions) - total_paid_withdrawals
    investment_balance = Decimal(0.40) * total_contributions
    total_remained_balance = total_contributions - total_paid_withdrawals

    return {
        "total_contributions": total_contributions,
        "savings_balance": round(max(savings_balance, Decimal(0.00)), 2),  # Ensure non-negative balance
        "investment_balance": round(investment_balance, 2),
        "total_remained_balance": max(total_remained_balance, Decimal(0.00)),  # Ensure non-negative balance
        "total_withdrawn": total_paid_withdrawals,
        'disbursed_credits': disbursed_credits,
        'repaid_credits': repaid_credits,
    }

def get_system_financial_summary():
    """
    Returns a dictionary with system-wide financial details:
    - total_system_contributions: Total amount contributed by all employees.
    - total_system_savings_balance: Savings balance (60% of total contributions minus withdrawals).
    - total_system_investment_balance: Investment balance (40% of total contributions).
    - total_remained_balance: Remaining system balance after withdrawals.
    """
    total_system_contributions = ContributionRecord.objects.aggregate(Sum('amount'))['amount__sum'] or Decimal(0.00)
    total_withdrawn = Withdrawals.get_system_total_paid_withdrawals()
    
    disbursed_credits = Credit.objects.filter(status='Disbursed').aggregate(total=Sum('amount_requested'))['total'] or Decimal(0.00)
    repaid_credits = Credit.objects.filter(status='Repaid').aggregate(total=Sum('amount_repaid'))['total'] or Decimal(0.00)

    # Calculate balances using Decimal to maintain precision
    total_system_savings_balance = (Decimal(0.60) * total_system_contributions) - total_withdrawn
    total_system_investment_balance = Decimal(0.40) * total_system_contributions
    total_remained_balance = total_system_contributions - total_withdrawn
    total_remained_balance = (total_remained_balance - Decimal(disbursed_credits)) + Decimal(repaid_credits)

    return {
        "total_system_contributions": total_system_contributions,
        "total_system_savings_balance": round(max(total_system_savings_balance, Decimal(0.00)), 2),  # Prevent negative balance
        "total_system_investment_balance": round(max(total_system_investment_balance, Decimal(0.00)), 2),
        "total_remained_balance": max(total_remained_balance, Decimal(0.00)),  # Ensure it doesn't go negative
        "total_withdrawn": max(total_withdrawn, Decimal(0.00)),
        "disbursed_credits": disbursed_credits,
        "repaid_credits": repaid_credits,

    }
