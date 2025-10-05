import math


class LocalProjection:
    """Local coordinate projection for neighborhood-scale mapping."""

    def __init__(self, center_lat: float, center_lon: float):
        self.center_lat = center_lat
        self.center_lon = center_lon
        # Approximate conversion factors
        self.lat_to_meters = 111320.0  # roughly constant globally
        self.lon_to_meters = 111320.0 * math.cos(math.radians(center_lat))

    def project_to_meters(self, lat: float, lon: float) -> tuple[float, float]:
        """Convert lat/lon to local Cartesian coordinates in meters."""
        x = (lon - self.center_lon) * self.lon_to_meters
        y = (lat - self.center_lat) * self.lat_to_meters
        return x, y

    def meters_to_latlon(self, x: float, y: float) -> tuple[float, float]:
        """Convert local meters back to lat/lon."""
        lat = self.center_lat + (y / self.lat_to_meters)
        lon = self.center_lon + (x / self.lon_to_meters)
        return lat, lon


class GridMapper:
    """Maps coordinates to ASCII grid positions."""

    def __init__(self, grid_resolution: float = 10.0):
        self.grid_resolution = grid_resolution  # meters per grid cell
        self.min_x = 0
        self.min_y = 0
        self.max_x = 0
        self.max_y = 0

    def set_bounds(self, coordinates: list[tuple[float, float]]):
        """Set grid bounds based on coordinate list (in meters)."""
        if not coordinates:
            return

        x_coords = [coord[0] for coord in coordinates]
        y_coords = [coord[1] for coord in coordinates]

        self.min_x = min(x_coords)
        self.max_x = max(x_coords)
        self.min_y = min(y_coords)
        self.max_y = max(y_coords)

        # Add padding
        padding = 50  # meters
        self.min_x -= padding
        self.max_x += padding
        self.min_y -= padding
        self.max_y += padding

    def meters_to_grid(self, x: float, y: float) -> tuple[int, int]:
        """Convert meter coordinates to grid coordinates."""
        # Normalize to grid origin
        norm_x = x - self.min_x
        norm_y = y - self.min_y

        # Convert to grid coordinates
        grid_x = int(norm_x / self.grid_resolution)
        # Flip Y axis for north-up display
        grid_y = int((self.max_y - self.min_y - norm_y) / self.grid_resolution)

        return grid_x, grid_y

    def grid_to_meters(self, grid_x: int, grid_y: int) -> tuple[float, float]:
        """Convert grid coordinates back to meters."""
        # Convert from grid coordinates
        norm_x = grid_x * self.grid_resolution
        norm_y = (self.max_y - self.min_y) - (grid_y * self.grid_resolution)

        # Add back offset
        x = norm_x + self.min_x
        y = norm_y + self.min_y

        return x, y

    def get_grid_dimensions(self) -> tuple[int, int]:
        """Get the dimensions of the grid in cells."""
        width = int((self.max_x - self.min_x) / self.grid_resolution) + 1
        height = int((self.max_y - self.min_y) / self.grid_resolution) + 1
        return width, height


class BoundingBox:
    """Helper class for managing coordinate bounds."""

    def __init__(self):
        self.min_lat = float('inf')
        self.max_lat = float('-inf')
        self.min_lon = float('inf')
        self.max_lon = float('-inf')

    def add_coordinate(self, lat: float, lon: float):
        """Add a coordinate to the bounding box."""
        self.min_lat = min(self.min_lat, lat)
        self.max_lat = max(self.max_lat, lat)
        self.min_lon = min(self.min_lon, lon)
        self.max_lon = max(self.max_lon, lon)

    def get_center(self) -> tuple[float, float]:
        """Get the center coordinate of the bounding box."""
        center_lat = (self.min_lat + self.max_lat) / 2
        center_lon = (self.min_lon + self.max_lon) / 2
        return center_lat, center_lon

    def is_valid(self) -> bool:
        """Check if the bounding box contains valid coordinates."""
        return (self.min_lat != float('inf') and
                self.max_lat != float('-inf') and
                self.min_lon != float('inf') and
                self.max_lon != float('-inf'))
