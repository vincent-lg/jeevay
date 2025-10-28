import wx

from jeevay.mapping.street_network import StreetNetwork
from jeevay.screen_reader import ScreenReader as SR


class AccessibleMapDisplay(wx.TextCtrl):
    """Accessible text control for displaying ASCII maps with navigation."""

    def __init__(self, parent):
        super().__init__(
            parent,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
            name="MapDisplay"
        )

        self.network: StreetNetwork | None = None
        self.map_lines: list[str] = []

        # Cursor position tracking for inline info display
        self.last_cursor_grid_y: int = -1  # Track cursor's line to know when to update
        self.last_cursor_grid_x: int = -1  # Track cursor's column for horizontal movement
        self.last_insertion_point: int = -1  # Track insertion point before modifications

        # Legend tracking - we maintain only ONE legend at the cursor's line
        self.legend_line_y: int = -1  # Which line has the legend currently
        self.legend_start_pos: int = 0  # Text position where legend starts on its line
        self.legend_length: int = 0  # Length of the current legend

        # Set up accessibility
        self.SetLabel("ASCII Map Display")

        # Use monospace font for proper alignment
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.SetFont(font)

        # Bind keyboard events
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

        # Timer for cursor position polling (50ms as per requirements)
        self.cursor_poll_timer = wx.Timer(self, wx.ID_ANY)
        self.Bind(wx.EVT_TIMER, self.on_cursor_poll_timer, self.cursor_poll_timer)
        self.cursor_poll_timer.Start(50)  # Poll every 50ms

    def set_map_data(self, network: StreetNetwork, lines: list[str]):
        """Set the map data and display it."""
        self.network = network
        self.map_lines = lines
        self.last_cursor_grid_y = -1  # Reset cursor tracking

        # Reset legend tracking
        self.legend_line_y = -1
        self.legend_start_pos = 0
        self.legend_length = 0

        # Display the map (pure map, no legends yet)
        map_text = "\n".join(lines)
        self.SetValue(map_text)

        # Set focus to beginning
        self.SetInsertionPoint(0)

    def on_cursor_poll_timer(self, event):
        """
        Timer callback that polls cursor position and updates inline tile information.
        This is called every 50ms to detect cursor movement.

        Updates when:
        - Cursor moves to a different LINE, or
        - Cursor moves horizontally on the SAME line
        """
        if not self.network or not self.map_lines:
            return

        # Get current cursor position
        grid_x, grid_y = self.get_cursor_grid_position()
        current_insertion_point = self.GetInsertionPoint()

        # Check if cursor has moved to a different LINE or moved horizontally on same line
        if grid_y != self.last_cursor_grid_y or grid_x != self.last_cursor_grid_x:
            # Calculate adjustment needed if legend is removed from a line above cursor
            insertion_adjustment = 0
            if self.legend_line_y >= 0 and self.legend_line_y < grid_y:
                # Legend is on a line ABOVE the new cursor line
                # When we remove it, all positions below shift up
                insertion_adjustment = -self.legend_length

            self.update_legend_for_line(grid_y, grid_x)

            # Restore the cursor to its original position, adjusted for text changes
            adjusted_position = current_insertion_point + insertion_adjustment
            if adjusted_position >= 0:
                self.SetInsertionPoint(adjusted_position)

            self.last_cursor_grid_y = grid_y
            self.last_cursor_grid_x = grid_x

    def invalidate_cursor_position(self):
        """
        Called when the map is rebuilt (zoom, recenter) to force an update
        of the legend even if the cursor grid position hasn't changed.
        This ensures legend reflects the new map data.
        """
        self.legend_line_y = -1
        self.legend_length = 0
        self.last_cursor_grid_y = -1

    def update_legend_for_line(self, grid_y: int, grid_x: int):
        """
        Surgically update the legend for a new cursor line.

        1. Remove old legend from previous line (if any)
        2. Add new legend to current line
        3. Keep cursor on the map portion of the line
        """
        # Step 1: Remove old legend from the previous line (if one exists)
        if self.legend_line_y >= 0 and self.legend_length > 0:
            self._remove_legend_from_line(self.legend_line_y)

        # Step 2: Add legend to the new cursor line
        self._add_legend_to_line(grid_y, grid_x)

    def _remove_legend_from_line(self, line_y: int):
        """
        Remove the legend from a specific line by deleting the characters.
        Uses the stored legend position and length for precise deletion.
        """
        if self.legend_length == 0 or self.legend_start_pos < 0:
            return

        # Use the stored position and length - we know exactly what we added
        start_pos = self.legend_start_pos
        end_pos = start_pos + self.legend_length

        # Temporarily make editable, remove the legend, make read-only again
        self.SetEditable(True)
        self.Remove(start_pos, end_pos)
        self.SetEditable(False)

        # Reset legend tracking
        self.legend_line_y = -1
        self.legend_length = 0
        self.legend_start_pos = 0

    def _add_legend_to_line(self, line_y: int, grid_x: int):
        """
        Add the legend to the cursor's current line.
        """
        if not (0 <= line_y < len(self.map_lines)):
            return

        # Get tile details for the current cursor position
        details = self.network.get_cell_details(grid_x, line_y)

        # Only add if there's actual detail to show
        if not details or details in ("Empty area", "Invalid position", "Location"):
            return

        # Calculate the text position where the legend should be inserted
        # (right after the map line)
        line_text = self.map_lines[line_y]
        text_pos = self._get_text_position(line_y, len(line_text))

        # Format the legend with a space delimiter
        legend_text = f" {details}"

        # Insert the legend
        self.SetEditable(True)
        self.SetInsertionPoint(text_pos)
        self.WriteText(legend_text)
        self.SetEditable(False)

        # Track the legend position and length
        self.legend_line_y = line_y
        self.legend_start_pos = text_pos
        self.legend_length = len(legend_text)

    def _get_text_position(self, grid_y: int, grid_x: int) -> int:
        """
        Convert grid coordinates to text position in the control.
        """
        text_pos = 0
        for i in range(grid_y):
            if i < len(self.map_lines):
                text_pos += len(self.map_lines[i]) + 1  # +1 for newline
        text_pos += grid_x
        return text_pos

    def _handle_arrow_navigation(self, key_code: int):
        """
        Handle up/down arrow navigation to keep cursor on map portion,
        ignoring any legend text that may wrap to the next line.
        """
        grid_x, grid_y = self.get_cursor_grid_position()

        # Clamp grid_x to map width to avoid landing in legend
        max_x = len(self.map_lines[grid_y]) if grid_y < len(self.map_lines) else 0
        grid_x = min(grid_x, max_x - 1) if max_x > 0 else 0

        if key_code == wx.WXK_UP:
            # Move up one line
            grid_y = max(0, grid_y - 1)
        elif key_code == wx.WXK_DOWN:
            # Move down one line
            grid_y = min(len(self.map_lines) - 1, grid_y + 1)

        # Set cursor to the new position (stays on map, not in legend)
        self.set_cursor_position(grid_x, grid_y)

    def on_key_down(self, event):
        """Handle keyboard navigation and accessibility features."""
        key_code = event.GetKeyCode()

        # Check for Tab (details)
        if key_code == ord("\t"):
            self.show_cursor_details()
            return

        # Check for Ctrl+S (summary)
        if event.ControlDown() and key_code == ord("S"):
            self.show_map_summary()
            return

        # Check for + or = (zoom in)
        if key_code in (ord("+"), ord("="), wx.WXK_ADD):
            self.zoom_in()
            return

        # Check for - (zoom out)
        if key_code in (ord("-"), wx.WXK_SUBTRACT):
            self.zoom_out()
            return

        # Check for RETURN (recenter map)
        if key_code == wx.WXK_RETURN:
            self.recenter_map()
            return

        # Handle arrow key navigation to prevent cursor landing in legend
        if key_code in (wx.WXK_UP, wx.WXK_DOWN):
            self._handle_arrow_navigation(key_code)
            return

        # Allow normal navigation for left/right arrows
        event.Skip()

    def show_cursor_details(self):
        """Show details about the position under the cursor."""
        if not self.network:
            wx.MessageBox("No map data available", "Details", wx.OK | wx.ICON_INFORMATION)
            return

        # Get cursor position
        cursor_pos = self.GetInsertionPoint()
        text = self.GetValue()

        # Convert cursor position to line/column
        lines_before_cursor = text[:cursor_pos].count('\n')
        line_start = text.rfind('\n', 0, cursor_pos)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1

        column = cursor_pos - line_start

        # Get grid coordinates
        grid_y = lines_before_cursor
        grid_x = column

        # Get cell details
        details = self.network.get_cell_details(grid_x, grid_y)

        # Send the details to the screen reader.
        SR.output(details)

    def show_map_summary(self):
        """Show a summary of the map."""
        if not self.network:
            wx.MessageBox("No map data available", "Summary", wx.OK | wx.ICON_INFORMATION)
            return

        from rendering.ascii_renderer import GridFormatter
        summary = GridFormatter.get_map_summary(self.network)
        wx.MessageBox(summary, "Map Summary", wx.OK | wx.ICON_INFORMATION)

    def set_cursor_position(self, grid_x: int, grid_y: int):
        """Set cursor to specific grid position."""
        if not self.map_lines or grid_y >= len(self.map_lines):
            return

        # Calculate text position
        text_pos = 0
        for i in range(grid_y):
            if i < len(self.map_lines):
                text_pos += len(self.map_lines[i]) + 1  # +1 for newline

        text_pos += min(grid_x, len(self.map_lines[grid_y]) if grid_y < len(self.map_lines) else 0)

        self.SetInsertionPoint(text_pos)
        self.SetFocus()

    def get_cursor_grid_position(self) -> tuple[int, int]:
        """Get the current cursor position as grid coordinates."""
        cursor_pos = self.GetInsertionPoint()
        text = self.GetValue()

        # Convert cursor position to line/column
        lines_before_cursor = text[:cursor_pos].count('\n')
        line_start = text.rfind('\n', 0, cursor_pos)
        if line_start == -1:
            line_start = 0
        else:
            line_start += 1

        column = cursor_pos - line_start

        # Grid coordinates
        grid_y = lines_before_cursor
        grid_x = column

        return grid_x, grid_y

    def zoom_in(self):
        """Zoom in on the map at the current cursor position."""
        if not self.network:
            SR.output("No map loaded")
            return

        grid_x, grid_y = self.get_cursor_grid_position()

        # Zoom factor of 0.8 means 25% zoom in (cell size decreases)
        success = self.network.zoom_at_cursor(grid_x, grid_y, zoom_factor=0.8)

        if success:
            # Invalidate cursor position to force tile info update after zoom
            self.invalidate_cursor_position()

            # Notify parent to re-render
            parent = self.GetParent()
            while parent and not hasattr(parent, 'on_zoom_changed'):
                parent = parent.GetParent()

            if parent and hasattr(parent, 'on_zoom_changed'):
                parent.on_zoom_changed()

            # Fallback: just announce the zoom level
            zoom_level = self.network.get_current_zoom_level()
            SR.output(f"Zoomed in. Scale: {zoom_level:.1f} meters per character")
        else:
            SR.output("Cannot zoom in further. Minimum zoom reached.")

    def zoom_out(self):
        """Zoom out on the map at the current cursor position."""
        if not self.network:
            SR.output("No map loaded")
            return

        grid_x, grid_y = self.get_cursor_grid_position()

        # Zoom factor of 1.25 means 25% zoom out (cell size increases)
        success = self.network.zoom_at_cursor(grid_x, grid_y, zoom_factor=1.25)

        if success:
            # Invalidate cursor position to force tile info update after zoom
            self.invalidate_cursor_position()

            # Notify parent to re-render
            parent = self.GetParent()
            while parent and not hasattr(parent, 'on_zoom_changed'):
                parent = parent.GetParent()

            if parent and hasattr(parent, 'on_zoom_changed'):
                parent.on_zoom_changed()

            zoom_level = self.network.get_current_zoom_level()
            SR.output(f"Zoomed out. Scale: {zoom_level:.1f} meters per character")
        else:
            SR.output("Cannot zoom out further. Maximum zoom reached.")

    def recenter_map(self):
        """Recenter the map on the cursor position."""
        if not self.network:
            SR.output("No map loaded")
            return

        grid_x, grid_y = self.get_cursor_grid_position()

        # Convert cursor position to lat/lon
        new_center_lat, new_center_lon = self.network.grid_to_latlon(grid_x, grid_y)

        # Check if we need to refetch data using MapCache
        needs_refetch = self.network.data_cache.needs_refetch(new_center_lat, new_center_lon)

        # Invalidate cursor position to force tile info update after recenter
        self.invalidate_cursor_position()

        # Notify parent to recenter
        parent = self.GetParent()
        while parent and not hasattr(parent, 'on_recenter_map'):
            parent = parent.GetParent()

        if parent and hasattr(parent, 'on_recenter_map'):
            parent.on_recenter_map(new_center_lat, new_center_lon, needs_refetch)
        else:
            SR.output("Cannot recenter map - parent window not found")
