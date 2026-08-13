import math


def CalculateDistance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates
    using Haversine formula.
    Returns distance in kilometers.
    """
    # Earth radius in kilometers
    R = 6371

    lat1 = math.radians(float(lat1))
    lat2 = math.radians(float(lat2))
    lon1 = math.radians(float(lon1))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def CalculateDeliveryFee(distance_km):
    """
    Flat KES 150 for anything within 10km, then +KES 50 for every extra
    10km (or part thereof) beyond that. Replaces the old fixed per-branch
    delivery zones - the fee is now purely a function of distance.

    e.g. 4km -> 150, 10km -> 150, 10.5km -> 200, 21km -> 250
    """
    if distance_km <= 10:
        return 150

    extra_km = distance_km - 10
    extra_blocks = math.ceil(extra_km / 10)
    return 150 + (50 * extra_blocks)