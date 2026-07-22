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