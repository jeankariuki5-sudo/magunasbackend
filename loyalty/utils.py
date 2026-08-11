from decimal import Decimal
from django.utils import timezone


def GetEffectivePrice(branch_product):
    """
    Returns the price that should currently be charged for a branch product:
    either its normal BranchProduct.price, or a currently-active promotion's
    discounted_price if one exists.

    IMPORTANT: this never mutates branch_product.price. The base price stays
    exactly as the admin/branch manager set it; the discount is only ever
    applied at read/checkout time. This means there's nothing to "reset" when
    a promotion ends, and no scheduled job is needed to revert prices.
    """
    now = timezone.now()
    promo = branch_product.promotions.filter(
        is_active = True,
        start_datetime__lte = now,
        end_datetime__gte = now,
    ).order_by('-created_at').first()

    return promo.discounted_price if promo else branch_product.price


def CalculatePointsEarned(amount):
    """
    Floor division, not rounding. KES 340 and KES 390 both earn 3 points -
    only at KES 400 do you earn 4.
    """
    return int(Decimal(amount) // 100)


def AwardPoints(customer, amount, order = None):
    """
    Called when a payment actually succeeds. `amount` should be what was
    actually charged (e.g. after any points-redemption discount), so a
    customer can't earn points on money they paid for with points.
    """
    from .models import LoyaltyAccount, LoyaltyTransaction

    points = CalculatePointsEarned(amount)
    if points <= 0:
        return 0

    account, _ = LoyaltyAccount.objects.get_or_create(customer = customer)
    account.points_balance += points
    account.lifetime_points_earned += points
    account.save()

    LoyaltyTransaction.objects.create(
        account = account,
        order = order,
        transaction_type = 'earned',
        points = points,
    )
    return points


def RedeemPoints(customer, points, order = None):
    """
    Deducts points 1:1 for KES off an order total. Raises ValueError if the
    customer doesn't have enough points - callers should validate/catch this
    BEFORE creating the order itself.
    """
    from .models import LoyaltyAccount, LoyaltyTransaction

    if points <= 0:
        return

    account, _ = LoyaltyAccount.objects.get_or_create(customer = customer)
    if account.points_balance < points:
        raise ValueError('Not enough points')

    account.points_balance -= points
    account.save()

    LoyaltyTransaction.objects.create(
        account = account,
        order = order,
        transaction_type = 'redeemed',
        points = -points,
    )


def ReverseRedeemedPoints(order):
    """
    Refunds any points that were redeemed against an order that later gets
    cancelled. (A paid order can't be cancelled at all, so this only ever
    applies to unpaid, pre-payment cancellations.)
    """
    from .models import LoyaltyTransaction

    redeemed = LoyaltyTransaction.objects.filter(order = order, transaction_type = 'redeemed').first()
    if not redeemed:
        return

    account = redeemed.account
    refund_points = -redeemed.points  # stored negative, flip it back to positive

    account.points_balance += refund_points
    account.save()

    LoyaltyTransaction.objects.create(
        account = account,
        order = order,
        transaction_type = 'reversed',
        points = refund_points,
    )
