from django.utils import timezone
from core.models import FoodDonation

def explain_priority(donation_id):
    try:
        donation = FoodDonation.objects.get(donation_id=donation_id)

        reasons = []
        hours_left = (donation.expiry_time - timezone.now()).total_seconds() / 3600

        if hours_left <= 2:
            reasons.append("the food is very close to expiry")
        elif hours_left <= 6:
            reasons.append("the food has limited remaining time")

        if donation.quantity >= 20:
            reasons.append("the quantity of food is high")

        if donation.priority_score >= 0.7:
            reasons.append("the ML model predicted high urgency")

        if not reasons:
            return "This donation currently has low urgency."

        return "This donation has high priority because " + ", ".join(reasons) + "."

    except FoodDonation.DoesNotExist:
        return "Donation not found."
