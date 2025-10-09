import requests

from jeevay.api.models import Address


class NominatimGeocoder:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Jeevay/1.0 (Accessible mapping demo)",
        })

    def search_address(self, query: str, limit: int = 5) -> list[Address]:
        """Search for addresses using Nominatim API."""
        params = {
            "q": query,
            "format": "json",
            "limit": limit,
            "addressdetails": 1,
            "extratags": 1
        }

        try:
            response = self.session.get(
                f"{self.base_url}/search", params=params
            )
            response.raise_for_status()
            data = response.json()

            addresses = []
            for item in data:
                address = Address(
                    display_name=item["display_name"],
                    lat=float(item["lat"]),
                    lon=float(item["lon"]),
                    place_id=item["place_id"],
                )
                addresses.append(address)

            return addresses

        except requests.RequestException as e:
            print(f"Error searching address: {e}")
            return []

    def get_address_details(self, place_id: str) -> Address | None:
        """Get detailed information for a specific place."""
        params = {
            "place_id": place_id,
            "format": "json",
            "addressdetails": 1,
        }

        try:
            response = self.session.get(
                f"{self.base_url}/lookup", params=params
            )
            response.raise_for_status()
            data = response.json()

            if data:
                item = data[0]
                return Address(
                    display_name=item["display_name"],
                    lat=float(item["lat"]),
                    lon=float(item["lon"]),
                    place_id=item["place_id"],
                )

        except requests.RequestException as e:
            print(f"Error getting address details: {e}")

        return None
