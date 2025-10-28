import sys
import threading
import traceback

import wx

from jeevay.api.geocoding import NominatimGeocoder
from jeevay.api.street_data import OverpassAPI
from jeevay.api.models import Address
from jeevay.mapping.street_network import StreetNetwork
from jeevay.mapping.viewport import ViewportConfig
from jeevay.rendering.ascii_renderer import ASCIIRenderer, GridFormatter
from jeevay.ui.address_input import AddressInputDialog, AddressSelectionDialog
from jeevay.ui.map_display import AccessibleMapDisplay
from jeevay.ui.progress_dialog import ProgressDialog


class MainWindow(wx.Frame):
    """Main application window."""

    def __init__(self):
        super().__init__(None, title="Jeevay - Accessible Geographic Demonstration", size=(1200, 800))

        # Initialize APIs
        self.geocoder = NominatimGeocoder()
        self.overpass = OverpassAPI()
        self.renderer = ASCIIRenderer()

        # Current data
        self.current_address: Address | None = None
        self.current_network: StreetNetwork | None = None

        # Development console
        self.dev_console = None

        self.setup_ui()
        self.setup_menu()
        self.Center()
        self.setup_dev_console()

        # Bind close event
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def setup_ui(self):
        """Set up the main UI."""
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Status bar
        self.CreateStatusBar()
        self.SetStatusText("Ready - Press Ctrl+N to enter a new address")

        # Instructions
        instructions = wx.StaticText(
            panel,
            label="Instructions:\n"
                  "• Ctrl+N: Enter new address\n"
                  "• Tab: Get details at cursor position\n"
                  "• Ctrl+S: Get map summary\n"
                  "• +/-: Zoom in/out\n"
                  "• Return: Recenter map at cursor\n"
                  "• Arrow keys: Navigate the map"
        )

        # Map display
        self.map_display = AccessibleMapDisplay(panel)

        # Layout
        vbox.Add(instructions, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(wx.StaticLine(panel), 0, wx.ALL | wx.EXPAND, 5)
        vbox.Add(self.map_display, 1, wx.ALL | wx.EXPAND, 10)

        panel.SetSizer(vbox)

        # Set initial focus
        self.map_display.SetFocus()

    def setup_menu(self):
        """Set up the application menu."""
        menubar = wx.MenuBar()

        # File menu
        file_menu = wx.Menu()
        new_address_item = file_menu.Append(wx.ID_NEW, "&New Address\tCtrl+N", "Enter a new address")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_EXIT, "E&xit\tCtrl+Q", "Exit the application")

        # Help menu
        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "&About", "About Jeevay")

        menubar.Append(file_menu, "&File")
        menubar.Append(help_menu, "&Help")

        self.SetMenuBar(menubar)

        # Bind menu events
        self.Bind(wx.EVT_MENU, self.on_new_address, new_address_item)
        self.Bind(wx.EVT_MENU, self.on_exit, exit_item)
        self.Bind(wx.EVT_MENU, self.on_about, about_item)

        # Bind keyboard shortcuts
        accel_tbl = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord('N'), wx.ID_NEW),
            (wx.ACCEL_CTRL, ord('Q'), wx.ID_EXIT)
        ])
        self.SetAcceleratorTable(accel_tbl)

    def on_new_address(self, event):
        """Handle new address menu item."""
        dialog = AddressInputDialog(self)

        if dialog.ShowModal() == wx.ID_OK:
            address_query = dialog.get_address()
            if address_query:
                self.search_address(address_query)

        dialog.Destroy()

    def on_exit(self, event):
        """Handle exit menu item."""
        self.Close()

    def on_about(self, event):
        """Handle about menu item."""
        info = wx.adv.AboutDialogInfo()
        info.SetName("Jeevay")
        info.SetVersion("1.0")
        info.SetDescription("Accessible Geographic Demonstration\n\n"
                           "Converts neighborhood maps into accessible ASCII format "
                           "for use with Braille displays and screen readers.")
        info.AddDeveloper("Created with Claude Code")

        wx.adv.AboutBox(info)

    def search_address(self, query: str):
        """Search for an address and display results."""
        self.SetStatusText("Searching for address...")

        # Run search in background thread
        thread = threading.Thread(target=self._search_address_worker, args=(query,))
        thread.daemon = True
        thread.start()

    def _search_address_worker(self, query: str):
        """Worker thread for address search."""
        try:
            # Search for addresses
            addresses = self.geocoder.search_address(query)

            # Update UI in main thread
            wx.CallAfter(self._on_address_search_complete, addresses)

        except Exception as e:
            wx.CallAfter(self._on_search_error, str(e))

    def _on_address_search_complete(self, addresses):
        """Handle address search completion."""
        if not addresses:
            self.SetStatusText("No addresses found")
            wx.MessageBox("No addresses found for the given query.", "Search Results", wx.OK | wx.ICON_INFORMATION)
            return

        # Select address
        selected_address = None
        if len(addresses) == 1:
            selected_address = addresses[0]
        else:
            dialog = AddressSelectionDialog(self, addresses)
            if dialog.ShowModal() == wx.ID_OK:
                selected_address = dialog.get_selected_address()
            dialog.Destroy()

        if selected_address:
            self.current_address = selected_address
            self.load_map_data(selected_address)

    def load_map_data(self, address: Address, refetch_center_lat: float = None, refetch_center_lon: float = None):
        """Load map data for the selected address or refetch at new center.

        Args:
            address: Address to load map for
            refetch_center_lat: If provided, refetch data centered at this latitude
            refetch_center_lon: If provided, refetch data centered at this longitude
        """
        self.SetStatusText("Loading map data...")

        # Determine center coordinates
        center_lat = refetch_center_lat if refetch_center_lat is not None else address.lat
        center_lon = refetch_center_lon if refetch_center_lon is not None else address.lon

        # Show progress dialog
        progress_dialog = ProgressDialog(self, title="Loading Map Data", max_steps=4)
        progress_dialog.Show()

        # Run map loading in background thread
        thread = threading.Thread(
            target=self._load_map_worker,
            args=(address, center_lat, center_lon, progress_dialog)
        )
        thread.daemon = True
        thread.start()

    def _load_map_worker(self, address: Address, center_lat: float, center_lon: float, progress_dialog: ProgressDialog):
        """Worker thread for map data loading."""
        # Step 0: Initialize
        wx.CallAfter(progress_dialog.update_progress, 0, "Initializing...", "")

        # Create viewport config and network to determine required radius
        viewport_config = ViewportConfig()  # 40x40 grid at 25m/cell
        network = StreetNetwork(viewport_config)
        required_radius = network.get_required_radius()

        # Track what succeeded/failed
        errors = []

        # Step 1: Fetch streets
        wx.CallAfter(progress_dialog.increment_progress, "Fetching streets...", f"Radius: {required_radius}m")
        try:
            streets = self.overpass.get_streets_around(center_lat, center_lon, radius=required_radius)
        except Exception as e:
            print(f"Street fetch failed: {e}")
            streets = []
            errors.append("streets")

        # Step 2: Fetch intersections and paths
        wx.CallAfter(progress_dialog.increment_progress, "Fetching intersections and paths...",
                     f"Found {len(streets)} streets" if not errors else "Streets failed, continuing...")
        try:
            intersections = self.overpass.get_intersections_around(center_lat, center_lon, radius=required_radius)
        except Exception as e:
            print(f"Intersection fetch failed: {e}")
            intersections = []
            errors.append("intersections")

        try:
            pedestrian_paths = self.overpass.get_pedestrian_paths_around(center_lat, center_lon, radius=required_radius)
        except Exception as e:
            print(f"Pedestrian path fetch failed: {e}")
            pedestrian_paths = []
            errors.append("paths")

        # Step 3: Fetch buildings
        wx.CallAfter(progress_dialog.increment_progress, "Fetching buildings...",
                     f"Found {len(intersections)} intersections, {len(pedestrian_paths)} paths")
        try:
            buildings = self.overpass.get_buildings_around(center_lat, center_lon, radius=required_radius)
        except Exception as e:
            print(f"Building fetch failed: {e}")
            buildings = []
            errors.append("buildings")

        # Step 4: Build grid and render
        detail_msg = f"Found {len(buildings)} buildings"
        if errors:
            detail_msg += f" (Failed: {', '.join(errors)})"
        wx.CallAfter(progress_dialog.increment_progress, "Building map grid...", detail_msg)

        try:
            # Build network with viewport system centered on the specified coordinates
            network.add_streets(streets)
            network.add_intersections(intersections)
            network.add_pedestrian_paths(pedestrian_paths)
            network.add_buildings(buildings)
            network.build_grid(center_lat, center_lon)

            # Update cache with new data
            network.data_cache.set_data(
                streets, intersections, pedestrian_paths, buildings,
                center_lat, center_lon, required_radius
            )

            # Render map
            map_lines = self.renderer.render_map(network)

            # Update UI in main thread
            wx.CallAfter(self._on_map_load_complete, network, map_lines, progress_dialog, errors)

        except Exception as e:
            print(traceback.format_exc())
            wx.CallAfter(self._on_search_error, str(e), progress_dialog)

    def _on_map_load_complete(self, network: StreetNetwork, map_lines, progress_dialog: ProgressDialog, errors: list):
        """Handle map loading completion."""
        self.current_network = network
        self.map_display.set_map_data(network, map_lines)

        # Center cursor on the map
        center_x = network.grid_width // 2
        center_y = network.grid_height // 2
        self.map_display.set_cursor_position(center_x, center_y)

        # Close progress dialog
        progress_dialog.Close()

        # Update status
        if self.current_address:
            status = f"Loaded map for: {self.current_address.display_name}"
            if errors:
                status += f" (partial data - {', '.join(errors)} unavailable)"
            self.SetStatusText(status)
        else:
            self.SetStatusText("Map loaded successfully")

        # Show summary
        summary = GridFormatter.get_map_summary(network)
        if errors:
            summary += f"\n\nNote: Some data could not be fetched:\n{', '.join(errors)}"
        wx.MessageBox(summary, "Map Loaded", wx.OK | wx.ICON_INFORMATION)

    def _on_search_error(self, error_message: str, progress_dialog: ProgressDialog = None):
        """Handle critical search/loading errors (when grid build fails)."""
        if progress_dialog:
            progress_dialog.Close()

        self.SetStatusText("Error occurred")
        wx.MessageBox(f"An error occurred: {error_message}", "Error", wx.OK | wx.ICON_ERROR)

    def setup_dev_console(self):
        """Set up the development console (only when running from Python)."""
        # Only start console if running from Python interpreter (not frozen/compiled)
        if getattr(sys, 'frozen', False):
            # Running as frozen executable (e.g., Nuitka, PyInstaller)
            return

        try:
            from jeevay.ui.dev import DevConsole
            self.dev_console = DevConsole(self)
            self.dev_console.start()
        except ImportError:
            # Dev console not available
            pass

    def on_zoom_changed(self):
        """Handle zoom changes from the map display."""
        if not self.current_network:
            return

        # Re-render the map with the new zoom level
        map_lines = self.renderer.render_map(self.current_network)

        # Get current cursor position before updating
        grid_x, grid_y = self.map_display.get_cursor_grid_position()

        # Update the display
        self.map_display.set_map_data(self.current_network, map_lines)

        # Restore cursor position (same grid coordinates)
        self.map_display.set_cursor_position(grid_x, grid_y)

        # Update status bar with zoom level
        zoom_level = self.current_network.get_current_zoom_level()
        if self.current_address:
            self.SetStatusText(
                f"{self.current_address.display_name} - "
                f"Scale: {zoom_level:.1f}m/char"
            )
        else:
            self.SetStatusText(f"Scale: {zoom_level:.1f} meters per character")

    def on_recenter_map(self, new_center_lat: float, new_center_lon: float, needs_refetch: bool):
        """Handle map recentering request from the map display.

        Args:
            new_center_lat: New center latitude
            new_center_lon: New center longitude
            needs_refetch: Whether new data needs to be fetched from API
        """
        if not self.current_network or not self.current_address:
            return

        if needs_refetch:
            # Fetch new data from API with progress dialog
            from jeevay.screen_reader import ScreenReader as SR
            SR.output("Recentering map - fetching new data from API")
            self.load_map_data(self.current_address, new_center_lat, new_center_lon)
        else:
            # Just rebuild the grid with cached data
            from jeevay.screen_reader import ScreenReader as SR
            SR.output("Recentering map using cached data")

            # Rebuild grid at new center
            self.current_network.rebuild_grid(new_center_lat, new_center_lon)

            # Re-render the map
            map_lines = self.renderer.render_map(self.current_network)

            # Update the display
            self.map_display.set_map_data(self.current_network, map_lines)

            # Center cursor on the new center
            center_x = self.current_network.grid_width // 2
            center_y = self.current_network.grid_height // 2
            self.map_display.set_cursor_position(center_x, center_y)

            # Update status
            self.SetStatusText(f"Map recentered at ({new_center_lat:.6f}, {new_center_lon:.6f})")

    def on_close(self, event):
        """Handle window close event."""
        # Stop dev console if running
        if self.dev_console:
            self.dev_console.stop()

        # Destroy the window
        self.Destroy()


class JeevayApp(wx.App):
    """Main application class."""

    def OnInit(self):
        """Initialize the application."""
        frame = MainWindow()
        frame.Show()
        return True
