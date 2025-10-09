from jeevay.mapping.street_network import StreetNetwork, GridCell


class ASCIIRenderer:
    """Renders street network as ASCII map."""

    def __init__(self):
        self.street_char = '.'
        self.intersection_char = '+'
        self.empty_char = ' '

    def render_map(self, network: StreetNetwork) -> list[str]:
        """Render the street network as ASCII lines."""
        if not network or network.grid_width == 0 or network.grid_height == 0:
            return ["No map data available"]

        lines = []

        for y in range(network.grid_height):
            line = []
            for x in range(network.grid_width):
                cell = network.get_cell_info(x, y)
                char = self._get_cell_character(cell)
                line.append(char)

            # Convert to string and strip trailing spaces
            line_str = "".join(line).rstrip()
            lines.append(line_str)

        # Remove trailing empty lines
        while lines and not lines[-1].strip():
            lines.pop()

        return lines

    def _get_cell_character(self, cell: GridCell) -> str:
        """
        Determine the character to display for a grid cell.
        Uses priority system: street (.) > pedestrian path (=) > building (#)
        """
        if not cell:
            return self.empty_char

        # Use the GridCell's priority-based character method
        return cell.get_priority_character()

    def render_with_coordinates(self, network: StreetNetwork) -> list[str]:
        """Render map with coordinate grid for debugging."""
        lines = self.render_map(network)

        if not lines:
            return lines

        # Add coordinate markers every 10 characters
        coord_lines = []

        # Add top coordinate line
        max_width = max(len(line) for line in lines) if lines else 0
        top_coord = ""
        for x in range(0, max_width, 10):
            if x < max_width:
                coord_str = str(x).ljust(10)[:10]
                top_coord += coord_str
        coord_lines.append(top_coord[:max_width])

        # Add map lines with left coordinate markers
        for y, line in enumerate(lines):
            if y % 10 == 0:
                prefix = f"{y:3d}:"
            else:
                prefix = "    "
            coord_lines.append(prefix + line)

        return coord_lines


class GridFormatter:
    """Formats grid output for accessibility."""

    @staticmethod
    def format_for_screen_reader(lines: list[str]) -> str:
        """Format map for screen reader accessibility."""
        if not lines:
            return "Empty map"

        formatted_lines = []
        for i, line in enumerate(lines):
            # Add line numbers for navigation
            formatted_line = f"Line {i + 1}: {line}"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)

    @staticmethod
    def get_map_summary(network: StreetNetwork) -> str:
        """Generate a summary of the map for accessibility."""
        summary_parts = []

        # Count streets
        if network.streets:
            street_count = len(network.streets)
            summary_parts.append(f"{street_count} street(s)")

            # List unique street names
            street_names = set()
            for street in network.streets:
                if street.name and street.name != "Unnamed Street":
                    street_names.add(street.name)

            if street_names:
                if len(street_names) <= 5:
                    names_list = ", ".join(sorted(street_names))
                    summary_parts.append(f"Streets: {names_list}")
                else:
                    summary_parts.append(f"Including {len(street_names)} named streets")

        # Count pedestrian paths
        if network.pedestrian_paths:
            path_count = len(network.pedestrian_paths)
            summary_parts.append(f"{path_count} pedestrian path(s)")

        # Count buildings
        if network.buildings:
            building_count = len(network.buildings)
            summary_parts.append(f"{building_count} building(s)")

        # Add dimensions
        if network.grid_width and network.grid_height:
            summary_parts.append(f"Map size: {network.grid_width} by {network.grid_height} cells")

        if not summary_parts:
            return "No map data found in this area."

        return "Map contains " + ", ".join(summary_parts) + "."
