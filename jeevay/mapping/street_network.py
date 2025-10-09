from dataclasses import dataclass

from jeevay.api.models import Street, Intersection, PedestrianPath, Building
from jeevay.mapping.coordinate_system import LocalProjection, GridMapper, BoundingBox
from jeevay.mapping.viewport import ViewportGrid, ViewportConfig, ViewportCalculator


@dataclass
class GridCell:
    """Represents a single cell in the ASCII grid."""
    has_street: bool = False
    street_names: list[str] = None
    has_pedestrian_path: bool = False
    pedestrian_path_names: list[str] = None
    has_building: bool = False
    building_info: list[tuple[str, str]] = None  # List of (name, address) tuples
    is_intersection: bool = False
    character: str = ' '

    def __post_init__(self):
        if self.street_names is None:
            self.street_names = []
        if self.pedestrian_path_names is None:
            self.pedestrian_path_names = []
        if self.building_info is None:
            self.building_info = []

    def get_priority_character(self) -> str:
        """
        Get the character to display based on priority rules.
        Priority (highest to lowest): street > pedestrian path > building

        Display rules:
        - '.' for streets (highest priority)
        - '=' for pedestrian paths (if no street present)
        - '#' for buildings (if no street or path present)
        - '+' for intersections (overrides street)
        """
        if self.is_intersection:
            return '+'
        elif self.has_street:
            return '.'
        elif self.has_pedestrian_path:
            return '='
        elif self.has_building:
            return '#'
        else:
            return ' '


class StreetNetwork:
    """Internal representation of street network for rendering."""

    def __init__(self, viewport_config: ViewportConfig = None):
        self.streets: list[Street] = []
        self.intersections: list[Intersection] = []
        self.pedestrian_paths: list[PedestrianPath] = []
        self.buildings: list[Building] = []
        self.projection: LocalProjection | None = None
        self.grid_mapper: GridMapper | None = None
        self.viewport_grid: ViewportGrid | None = None
        self.viewport_config = viewport_config or ViewportConfig()

        # Grid storage uses extended grid but renders only viewport
        self.extended_grid: dict[tuple[int, int], GridCell] = {}
        self.grid_width = self.viewport_config.width
        self.grid_height = self.viewport_config.height

        # Center coordinate for the map
        self.center_lat: float = 0.0
        self.center_lon: float = 0.0

        # Calculator for viewport requirements
        self.viewport_calculator = ViewportCalculator(self.viewport_config)

    def add_streets(self, streets: list[Street]):
        """Add streets to the network."""
        self.streets.extend(streets)

    def add_intersections(self, intersections: list[Intersection]):
        """Add intersections to the network."""
        self.intersections.extend(intersections)

    def add_pedestrian_paths(self, paths: list[PedestrianPath]):
        """Add pedestrian paths to the network."""
        self.pedestrian_paths.extend(paths)

    def add_buildings(self, buildings: list[Building]):
        """Add buildings to the network."""
        self.buildings.extend(buildings)

    def build_grid(self, center_lat: float, center_lon: float):
        """Build the internal grid representation using viewport system."""
        self.center_lat = center_lat
        self.center_lon = center_lon

        # Set up projection centered on the specified coordinates
        self.projection = LocalProjection(center_lat, center_lon)

        # Set up viewport grid
        self.viewport_grid = ViewportGrid(self.viewport_config)

        # Initialize extended grid
        self.extended_grid = {}
        for x in range(self.viewport_grid.extended_width):
            for y in range(self.viewport_grid.extended_height):
                self.extended_grid[(x, y)] = GridCell()

        # Populate grid with all features
        self._rasterize_streets()
        self._rasterize_pedestrian_paths()
        self._rasterize_buildings()
        self._mark_intersections()

    def _rasterize_streets(self):
        """Convert street coordinates to grid cells using viewport system."""
        for street in self.streets:
            coords_in_meters = []
            for lat, lon in street.coordinates:
                x, y = self.projection.project_to_meters(lat, lon)
                coords_in_meters.append((x, y))

            # Draw line segments between consecutive points
            for i in range(len(coords_in_meters) - 1):
                x1, y1 = coords_in_meters[i]
                x2, y2 = coords_in_meters[i + 1]

                # Get extended grid coordinates
                gx1, gy1 = self.viewport_grid.meters_to_extended_grid(x1, y1)
                gx2, gy2 = self.viewport_grid.meters_to_extended_grid(x2, y2)

                # Draw line using Bresenham-like algorithm
                points = self._line_points(gx1, gy1, gx2, gy2)

                for gx, gy in points:
                    if self.viewport_grid.is_valid_extended_position(gx, gy):
                        cell = self.extended_grid[(gx, gy)]
                        cell.has_street = True
                        if street.name not in cell.street_names:
                            cell.street_names.append(street.name)

    def _line_points(self, x1: int, y1: int, x2: int, y2: int) -> list[tuple[int, int]]:
        """Generate points along a line (simplified Bresenham algorithm)."""
        points = []

        dx = abs(x2 - x1)
        dy = abs(y2 - y1)

        if dx == 0 and dy == 0:
            return [(x1, y1)]

        # Use simple interpolation for this proof of concept
        steps = max(dx, dy)
        if steps == 0:
            return [(x1, y1)]

        x_step = (x2 - x1) / steps
        y_step = (y2 - y1) / steps

        for i in range(steps + 1):
            x = int(x1 + i * x_step)
            y = int(y1 + i * y_step)
            points.append((x, y))

        return points

    def _rasterize_pedestrian_paths(self):
        """Convert pedestrian path coordinates to grid cells."""
        for path in self.pedestrian_paths:
            coords_in_meters = []
            for lat, lon in path.coordinates:
                x, y = self.projection.project_to_meters(lat, lon)
                coords_in_meters.append((x, y))

            # Draw line segments between consecutive points
            for i in range(len(coords_in_meters) - 1):
                x1, y1 = coords_in_meters[i]
                x2, y2 = coords_in_meters[i + 1]

                # Get extended grid coordinates
                gx1, gy1 = self.viewport_grid.meters_to_extended_grid(x1, y1)
                gx2, gy2 = self.viewport_grid.meters_to_extended_grid(x2, y2)

                # Draw line using Bresenham-like algorithm
                points = self._line_points(gx1, gy1, gx2, gy2)

                for gx, gy in points:
                    if self.viewport_grid.is_valid_extended_position(gx, gy):
                        cell = self.extended_grid[(gx, gy)]
                        cell.has_pedestrian_path = True
                        if path.name not in cell.pedestrian_path_names:
                            cell.pedestrian_path_names.append(path.name)

    def _rasterize_buildings(self):
        """Mark grid cells that contain buildings."""
        for building in self.buildings:
            x, y = self.projection.project_to_meters(building.lat, building.lon)
            gx, gy = self.viewport_grid.meters_to_extended_grid(x, y)

            if self.viewport_grid.is_valid_extended_position(gx, gy):
                cell = self.extended_grid[(gx, gy)]
                cell.has_building = True
                building_tuple = (building.name, building.address or "")
                if building_tuple not in cell.building_info:
                    cell.building_info.append(building_tuple)

    def _mark_intersections(self):
        """Mark grid cells that are intersections."""
        for intersection in self.intersections:
            x, y = self.projection.project_to_meters(intersection.lat, intersection.lon)
            gx, gy = self.viewport_grid.meters_to_extended_grid(x, y)

            if self.viewport_grid.is_valid_extended_position(gx, gy):
                self.extended_grid[(gx, gy)].is_intersection = True

    def _is_valid_grid_pos(self, x: int, y: int) -> bool:
        """Check if grid position is valid within viewport."""
        return 0 <= x < self.grid_width and 0 <= y < self.grid_height

    def get_cell_info(self, grid_x: int, grid_y: int) -> GridCell | None:
        """Get information about a specific viewport grid cell."""
        if not self._is_valid_grid_pos(grid_x, grid_y):
            return None

        # Convert viewport coordinates to extended grid coordinates
        ext_x = grid_x + self.viewport_grid.viewport_offset_x
        ext_y = grid_y + self.viewport_grid.viewport_offset_y

        if self.viewport_grid.is_valid_extended_position(ext_x, ext_y):
            return self.extended_grid[(ext_x, ext_y)]
        return None

    def get_cell_details(self, grid_x: int, grid_y: int) -> str:
        """Get detailed description of a grid cell for accessibility."""
        cell = self.get_cell_info(grid_x, grid_y)
        if not cell:
            return "Invalid position"

        if not cell.has_street and not cell.has_pedestrian_path and not cell.has_building:
            return "Empty area"

        details = []

        # Intersection status
        if cell.is_intersection:
            details.append("Intersection")

        # Streets (highest priority - always shown if present)
        if cell.street_names:
            if len(cell.street_names) == 1:
                details.append(f"Street: {cell.street_names[0]}")
            else:
                street_list = ", ".join(cell.street_names)
                details.append(f"Streets: {street_list}")

        # Pedestrian paths
        if cell.pedestrian_path_names:
            # Filter out generic "Unnamed Path" if we have named paths
            named_paths = [name for name in cell.pedestrian_path_names if name != "Unnamed Path"]
            if named_paths:
                if len(named_paths) == 1:
                    details.append(f"Pedestrian path: {named_paths[0]}")
                else:
                    path_list = ", ".join(named_paths)
                    details.append(f"Pedestrian paths: {path_list}")
            else:
                # All paths are unnamed
                details.append("Pedestrian path")

        # Buildings
        if cell.building_info:
            for name, address in cell.building_info:
                if address:
                    details.append(f"Building: {address}")
                elif name and name != "Unnamed Building":
                    details.append(f"Building: {name}")
                else:
                    details.append("Building")

        return " - ".join(details) if details else "Location"

    def get_required_radius(self) -> int:
        """Get the radius needed to ensure complete viewport coverage."""
        return self.viewport_calculator.calculate_required_radius()
