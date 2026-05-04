import geocoder

def get_live_location():
    g = geocoder.ip('me')

    if g.ok:
        lat, lon = g.latlng
        link = f"https://www.google.com/maps?q={lat},{lon}"
        return lat, lon, link
    else:
        return None, None, "Location not available"