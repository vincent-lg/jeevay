import wx


class ProgressDialog(wx.Dialog):
    """A dialog showing progress of multiple API operations."""

    def __init__(self, parent, title="Loading Map Data", max_steps=4):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)

        self.max_steps = max_steps
        self.current_step = 0

        self.setup_ui()
        self.CenterOnParent()

    def setup_ui(self):
        """Set up the dialog UI."""
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Status text
        self.status_label = wx.StaticText(panel, label="Preparing to load map data...")
        vbox.Add(self.status_label, 0, wx.ALL | wx.EXPAND, 10)

        # Progress bar
        self.progress_bar = wx.Gauge(panel, range=self.max_steps, size=(400, 25))
        vbox.Add(self.progress_bar, 0, wx.ALL | wx.EXPAND, 10)

        # Details text (smaller font)
        self.details_label = wx.StaticText(panel, label="")
        details_font = self.details_label.GetFont()
        details_font.SetPointSize(details_font.GetPointSize() - 1)
        self.details_label.SetFont(details_font)
        vbox.Add(self.details_label, 0, wx.ALL | wx.EXPAND, 10)

        panel.SetSizer(vbox)

        # Fit to content
        vbox.Fit(panel)
        self.Fit()

    def update_progress(self, step: int, status: str, details: str = ""):
        """Update the progress bar and status text.

        Args:
            step: Current step number (0 to max_steps)
            status: Main status message
            details: Optional detailed information
        """
        self.current_step = step
        self.progress_bar.SetValue(step)
        self.status_label.SetLabel(status)
        self.details_label.SetLabel(details)

        # Force UI update
        self.Update()
        wx.GetApp().Yield(True)

    def increment_progress(self, status: str, details: str = ""):
        """Increment progress by one step.

        Args:
            status: Main status message
            details: Optional detailed information
        """
        self.update_progress(self.current_step + 1, status, details)
