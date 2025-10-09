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


class MainWindow(wx.Frame):
    """Main application window."""

    def __init__(self):
        super().__init__(None, title="Jeevay - Accessible Geographic Demonstration", size=(800, 600))

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

    def load_map_data(self, address: Address):
        """Load map data for the selected address."""
        self.SetStatusText("Loading map data...")

        # Run map loading in background thread
        thread = threading.Thread(target=self._load_map_worker, args=(address,))
        thread.daemon = True
        thread.start()

    def _load_map_worker(self, address: Address):
        """Worker thread for map data loading."""
        try:
            # Create viewport config and network to determine required radius
            viewport_config = ViewportConfig()  # 40x40 grid at 10m/cell
            network = StreetNetwork(viewport_config)
            required_radius = network.get_required_radius()

            # Get all map data using calculated radius for complete coverage
            streets = self.overpass.get_streets_around(address.lat, address.lon, radius=required_radius)
            intersections = self.overpass.get_intersections_around(address.lat, address.lon, radius=required_radius)
            pedestrian_paths = self.overpass.get_pedestrian_paths_around(address.lat, address.lon, radius=required_radius)
            buildings = self.overpass.get_buildings_around(address.lat, address.lon, radius=required_radius)

            # Build network with viewport system centered on the address
            network.add_streets(streets)
            network.add_intersections(intersections)
            network.add_pedestrian_paths(pedestrian_paths)
            network.add_buildings(buildings)
            network.build_grid(address.lat, address.lon)

            # Render map
            map_lines = self.renderer.render_map(network)

            # Update UI in main thread
            wx.CallAfter(self._on_map_load_complete, network, map_lines)

        except Exception as e:
            print(traceback.format_exc())
            wx.CallAfter(self._on_search_error, str(e))

    def _on_map_load_complete(self, network: StreetNetwork, map_lines):
        """Handle map loading completion."""
        self.current_network = network
        self.map_display.set_map_data(network, map_lines)

        # Update status
        if self.current_address:
            self.SetStatusText(f"Loaded map for: {self.current_address.display_name}")
        else:
            self.SetStatusText("Map loaded successfully")

        # Show summary
        summary = GridFormatter.get_map_summary(network)
        wx.MessageBox(summary, "Map Loaded", wx.OK | wx.ICON_INFORMATION)

    def _on_search_error(self, error_message: str):
        """Handle search/loading errors."""
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
