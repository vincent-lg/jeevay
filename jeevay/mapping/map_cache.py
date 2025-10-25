from dataclasses import dataclass
import math

from jeevay.api.models import Street, Intersection, PedestrianPath, Building


@dataclass
class MapDataCache:
    """
    Caches raw map data fetched from the API.
    Separates data storage from rendering concerns.
    """
    # Raw data from API
    streets: list[Street]
    intersections: list[Intersection]
    pedestrian_paths: list[PedestrianPath]
    buildings: list[Building]

    # Geographic center and fetch parameters
    center_lat: float
    center_lon: float
    fetch_radius: int  # in meters

    def __init__(self):
        self.streets = []
        self.intersections = []
        self.pedestrian_paths = []
        self.buildings = []
        self.center_lat = 0.0
        self.center_lon = 0.0
        self.fetch_radius = 0

    def set_data(
        self,
        streets: list[Street],
        intersections: list[Intersection],
        pedestrian_paths: list[PedestrianPath],
        buildings: list[Building],
        center_lat: float,
        center_lon: float,
        fetch_radius: int,
    ):
        """Store fetched map data."""
        self.streets = streets
        self.intersections = intersections
        self.pedestrian_paths = pedestrian_paths
        self.buildings = buildings
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.fetch_radius = fetch_radius

    def needs_refetch(self, new_center_lat: float, new_center_lon: float) -> bool:
        """
        Check if new center point requires refetching data.
        Returns True if new center is too far from cached center.
        """
        if not self.streets and not self.buildings:
            return True  # No data cached yet

        # Calculate distance between centers (approximate)
        lat_diff = (new_center_lat - self.center_lat) * 111320  # meters
        lon_diff = (new_center_lon - self.center_lon) * 111320 * math.cos(math.radians(self.center_lat))
        distance = math.sqrt(lat_diff**2 + lon_diff**2)

        # If new center is more than 50% of fetch radius away, refetch
        threshold = self.fetch_radius * 0.5
        return distance > threshold

    def has_data(self) -> bool:
        """Check if cache contains any data."""
        return bool(self.streets or self.intersections or self.pedestrian_paths or self.buildings)
