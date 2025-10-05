import wx

import accessible_output3.outputs.auto

from jeevay.mapping.street_network import StreetNetwork

o = accessible_output3.outputs.auto.Auto()


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

        # Set up accessibility
        self.SetLabel("ASCII Map Display")

        # Use monospace font for proper alignment
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.SetFont(font)

        # Bind keyboard events
        self.Bind(wx.EVT_KEY_DOWN, self.on_key_down)

    def set_map_data(self, network: StreetNetwork, lines: list[str]):
        """Set the map data and display it."""
        self.network = network
        self.map_lines = lines

        # Display the map
        map_text = '\n'.join(lines)
        self.SetValue(map_text)

        # Set focus to beginning
        self.SetInsertionPoint(0)

    def on_key_down(self, event):
        """Handle keyboard navigation and accessibility features."""
        key_code = event.GetKeyCode()

        # Check for Ctrl+D (details)
        if key_code == ord('\t'):
            self.show_cursor_details()
            return

        # Check for Ctrl+S (summary)
        if event.ControlDown() and key_code == ord('S'):
            self.show_map_summary()
            return

        # Allow normal navigation
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
        o.speak(details)
        o.braille(details)

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
