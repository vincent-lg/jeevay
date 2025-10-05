from dataclasses import dataclass
import math


@dataclass
class ViewportConfig:
    """Configuration for the viewport system."""
    width: int = 40  # characters
    height: int = 40  # characters
    cell_size_meters: float = 25.0  # meters per character
    margin_factor: float = 1.2  # extra radius margin for safety


class ViewportCalculator:
    """Calculates viewport parameters and radius requirements."""

    def __init__(self, config: ViewportConfig = None):
        self.config = config or ViewportConfig()

    def calculate_required_radius(self) -> int:
        """Calculate the minimum radius needed to cover viewport corners."""
        # Viewport dimensions in meters
        width_meters = self.config.width * self.config.cell_size_meters
        height_meters = self.config.height * self.config.cell_size_meters

        # Distance from center to corner (half diagonal)
        diagonal_half = math.sqrt((width_meters/2)**2 + (height_meters/2)**2)

        # Add margin and round up
        required_radius = int(diagonal_half * self.config.margin_factor) + 1

        return required_radius

    def get_viewport_bounds_meters(self, center_lat: float, center_lon: float) -> tuple[float, float, float, float]:
        """Get viewport bounds in meters relative to center.

        Returns: (min_x, max_x, min_y, max_y) in meters
        """
        half_width = (self.config.width * self.config.cell_size_meters) / 2
        half_height = (self.config.height * self.config.cell_size_meters) / 2

        return (-half_width, half_width, -half_height, half_height)

    def is_coordinate_in_viewport(self, x_meters: float, y_meters: float) -> bool:
        """Check if a coordinate (in meters from center) is within the viewport."""
        min_x, max_x, min_y, max_y = self.get_viewport_bounds_meters(0, 0)
        return min_x <= x_meters <= max_x and min_y <= y_meters <= max_y


class ViewportGrid:
    """Manages a fixed-size viewport grid with coordinates beyond visible area."""

    def __init__(self, config: ViewportConfig = None):
        self.config = config or ViewportConfig()
        self.calculator = ViewportCalculator(config)

        # The visible grid is always config.width x config.height
        self.visible_width = self.config.width
        self.visible_height = self.config.height

        # Extended grid for storing data beyond viewport
        # This allows for smooth panning in future if needed
        self.extended_factor = 2.0  # Store 2x the viewport size in each direction
        self.extended_width = int(self.visible_width * self.extended_factor)
        self.extended_height = int(self.visible_height * self.extended_factor)

        # Offset to center the viewport within the extended grid
        self.viewport_offset_x = (self.extended_width - self.visible_width) // 2
        self.viewport_offset_y = (self.extended_height - self.visible_height) // 2

    def meters_to_viewport_grid(self, x_meters: float, y_meters: float) -> tuple[int, int]:
        """Convert meter coordinates to viewport grid coordinates.

        Returns coordinates within the visible viewport (0 to width-1, 0 to height-1).
        Returns (-1, -1) if outside viewport.
        """
        # Convert to grid cells centered on viewport
        grid_x = int(x_meters / self.config.cell_size_meters + self.visible_width / 2)
        grid_y = int(-y_meters / self.config.cell_size_meters + self.visible_height / 2)  # Flip Y for north-up

        # Check if within viewport bounds
        if 0 <= grid_x < self.visible_width and 0 <= grid_y < self.visible_height:
            return grid_x, grid_y
        else:
            return -1, -1

    def meters_to_extended_grid(self, x_meters: float, y_meters: float) -> tuple[int, int]:
        """Convert meter coordinates to extended grid coordinates.

        This includes coordinates outside the viewport for data storage.
        """
        # Convert to grid cells with extended bounds centered
        grid_x = int(x_meters / self.config.cell_size_meters + self.extended_width / 2)
        grid_y = int(-y_meters / self.config.cell_size_meters + self.extended_height / 2)  # Flip Y for north-up

        return grid_x, grid_y

    def is_valid_extended_position(self, grid_x: int, grid_y: int) -> bool:
        """Check if position is valid within extended grid."""
        return 0 <= grid_x < self.extended_width and 0 <= grid_y < self.extended_height

    def is_valid_viewport_position(self, grid_x: int, grid_y: int) -> bool:
        """Check if position is valid within visible viewport."""
        return 0 <= grid_x < self.visible_width and 0 <= grid_y < self.visible_height

    def extended_to_viewport_coords(self, ext_x: int, ext_y: int) -> tuple[int, int]:
        """Convert extended grid coordinates to viewport coordinates.

        Returns (-1, -1) if outside viewport.
        """
        viewport_x = ext_x - self.viewport_offset_x
        viewport_y = ext_y - self.viewport_offset_y

        if self.is_valid_viewport_position(viewport_x, viewport_y):
            return viewport_x, viewport_y
        else:
            return -1, -1
