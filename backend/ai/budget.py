"""Monthly AI budget per organization (calendar month, UTC).

A soft cap: new reports are refused once the month's spend reaches the budget;
reports already running finish. Admins are warned once a month at
AI_BUDGET_WARNING_RATIO of the budget (in-app, email and the budget.warning
webhook event).
"""
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from .models import AIUsage


def month_start():
    return timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def spent_this_month(organization):
    total = AIUsage.objects.filter(organization=organization, created_at__gte=month_start()).aggregate(
        total=Sum("cost_usd")
    )["total"]
    return total or Decimal(0)


def budget_status(organization):
    budget = organization.monthly_ai_budget_usd
    spent = spent_this_month(organization)
    if budget is None:
        return {"budget_usd": None, "spent_usd": str(spent), "ratio": None, "status": "unlimited"}
    ratio = float(spent / budget) if budget else 1.0
    status = "exceeded" if ratio >= 1 else "warning" if ratio >= settings.AI_BUDGET_WARNING_RATIO else "ok"
    return {"budget_usd": str(budget), "spent_usd": str(spent), "ratio": round(ratio, 4), "status": status}


def warn_if_near_budget(organization):
    """Call after recording usage, inside the organization's tenant transaction."""
    from notifications.models import Notification
    from notifications.service import notify
    from tenancy.models import Membership
    from webhooks.events import emit

    status = budget_status(organization)
    if status["status"] not in ("warning", "exceeded"):
        return
    if Notification.objects.filter(organization=organization, kind="budget_warning", created_at__gte=month_start()).exists():
        return  # once a month
    percent = round(status["ratio"] * 100)
    title = f"AI budget: {percent}% used this month"
    body = (
        f"{organization.name} has used {status['spent_usd']} of its {status['budget_usd']} USD monthly AI budget. "
        "New reports are refused once it is reached."
    )
    for membership in Membership.objects.filter(organization=organization, role=Membership.ADMIN).select_related("user"):
        notify(user=membership.user, organization=organization, kind="budget_warning", title=title, body=body)
    emit(organization, "budget.warning", status)
