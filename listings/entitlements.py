"""
Single source of truth for a user's unlock credits / Ultimate subscription.

Everything is calculated from the database (Purchase + UserUnlock), so it is the
same on every device, after logout/login, and after clearing cookies/storage.
"""
from datetime import timedelta

from django.utils import timezone

from .models import Purchase, UserUnlock

UNLIMITED_DAYS = 30

# plan_name (as sent by the frontend) -> number of unlock credits
CREDIT_PLANS = {
    'single unlock': 1,
    'value pack': 5,
    'pro pack': 10,
}
UNLIMITED_PLAN_KEYWORDS = ('ultimate', 'unlimited')


def plan_credits(plan_name):
    """Returns ('unlimited', None) | ('credits', n) | (None, 0) for a plan name."""
    name = (plan_name or '').strip().lower()
    if any(k in name for k in UNLIMITED_PLAN_KEYWORDS):
        return 'unlimited', None
    for key, n in CREDIT_PLANS.items():
        if key in name:
            return 'credits', n
    return None, 0


def pricing_key_for_plan(plan_name):
    kind, n = plan_credits(plan_name)
    if kind == 'unlimited':
        return 'unlimited'
    if kind == 'credits':
        return str(n)
    return None


def get_entitlement(user):
    purchases = Purchase.objects.filter(user=user, status='SUCCESS').order_by('created_at')
    unlocks = list(UserUnlock.objects.filter(user=user).order_by('unlocked_at'))

    credits_bought = 0
    windows = []  # (start, end) of each Ultimate subscription
    for p in purchases:
        kind, n = plan_credits(p.plan_name)
        if kind == 'credits':
            credits_bought += n
        elif kind == 'unlimited':
            # small grace window: the unlock call can land a moment before the payment is saved
            windows.append((p.created_at - timedelta(minutes=10), p.created_at + timedelta(days=UNLIMITED_DAYS)))

    # Unlocks made while an Ultimate subscription was active are free.
    def during_unlimited(ts):
        return any(start <= ts <= end for start, end in windows)

    credits_used = sum(1 for u in unlocks if not during_unlimited(u.unlocked_at))

    now = timezone.now()
    active = [end for start, end in windows if start <= now <= end]
    unlimited_expires_at = max(active) if active else None

    return {
        'credits_bought': credits_bought,
        'credits_used': credits_used,
        'credits_left': max(0, credits_bought - credits_used),
        'is_unlimited': unlimited_expires_at is not None,
        'unlimited_expires_at': unlimited_expires_at.isoformat() if unlimited_expires_at else None,
        'unlocked_ids': [u.property_id for u in unlocks],
    }


def current_tier(ent):
    """'unlimited' while Ultimate is active, else the biggest pack size the unused credits still cover (0 = none)."""
    if ent.get('is_unlimited'):
        return 'unlimited'
    left = ent.get('credits_left') or 0
    return 10 if left >= 10 else 5 if left >= 5 else 1 if left >= 1 else 0


def plan_block_reason(user, plan_name):
    """Why this user can't buy this unlock plan right now (None = allowed).
    Ultimate active: nothing until it ends. Unused credits: no smaller pack (upgrades are fine)."""
    kind, n = plan_credits(plan_name)
    if kind is None:
        return None
    ent = get_entitlement(user)
    tier = current_tier(ent)
    if tier == 'unlimited':
        until = (ent.get('unlimited_expires_at') or '')[:10]
        if kind == 'unlimited':
            return f'You already have the Ultimate plan (active until {until}).'
        return f'Your Ultimate plan already includes unlimited unlocks (until {until}).'
    if kind == 'credits' and tier and n < tier:
        return f'You still have {ent.get("credits_left")} unlocks left. You can only upgrade to a bigger plan.'
    return None
