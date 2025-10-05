import wx

from jeevay.api.models import Address


class AddressInputDialog(wx.Dialog):
    """Dialog for entering street addresses."""

    def __init__(self, parent):
        super().__init__(parent, title="Enter Address", size=(400, 150))

        self.address = None
        self.setup_ui()
        self.Center()

    def setup_ui(self):
        """Set up the dialog UI."""
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Address input
        label = wx.StaticText(panel, label="Enter street address:")
        self.address_text = wx.TextCtrl(panel, size=(350, -1), style=wx.TE_PROCESS_ENTER)
        self.address_text.SetFocus()

        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(panel, wx.ID_OK, "Search")
        cancel_button = wx.Button(panel, wx.ID_CANCEL, "Cancel")

        button_sizer.Add(ok_button, 0, wx.ALL, 5)
        button_sizer.Add(cancel_button, 0, wx.ALL, 5)

        # Layout
        vbox.Add(label, 0, wx.ALL, 10)
        vbox.Add(self.address_text, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(button_sizer, 0, wx.ALL | wx.CENTER, 10)

        panel.SetSizer(vbox)

        # Bind events
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        self.address_text.Bind(wx.EVT_TEXT_ENTER, self.on_ok)

    def on_ok(self, event):
        """Handle OK button click."""
        self.address = self.address_text.GetValue().strip()
        if self.address:
            self.EndModal(wx.ID_OK)
        else:
            wx.MessageBox("Please enter an address", "Error", wx.OK | wx.ICON_WARNING)

    def get_address(self) -> str:
        """Get the entered address."""
        return self.address or ""


class AddressSelectionDialog(wx.Dialog):
    """Dialog for selecting from multiple address matches."""

    def __init__(self, parent, addresses: list[Address]):
        super().__init__(parent, title="Select Address", size=(600, 400))

        self.addresses = addresses
        self.selected_address = None
        self.setup_ui()
        self.Center()

    def setup_ui(self):
        """Set up the dialog UI."""
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Instruction label
        label = wx.StaticText(panel, label="Multiple addresses found. Please select one:")

        # Address list
        choices = [addr.display_name for addr in self.addresses]
        self.address_list = wx.ListBox(panel, choices=choices, style=wx.LB_SINGLE)

        if choices:
            self.address_list.SetSelection(0)

        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        ok_button = wx.Button(panel, wx.ID_OK, "Select")
        cancel_button = wx.Button(panel, wx.ID_CANCEL, "Cancel")

        button_sizer.Add(ok_button, 0, wx.ALL, 5)
        button_sizer.Add(cancel_button, 0, wx.ALL, 5)

        # Layout
        vbox.Add(label, 0, wx.ALL, 10)
        vbox.Add(self.address_list, 1, wx.ALL | wx.EXPAND, 10)
        vbox.Add(button_sizer, 0, wx.ALL | wx.CENTER, 10)

        panel.SetSizer(vbox)

        # Bind events
        ok_button.Bind(wx.EVT_BUTTON, self.on_ok)
        self.address_list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_ok)

    def on_ok(self, event):
        """Handle OK button click."""
        selection = self.address_list.GetSelection()
        if selection != wx.NOT_FOUND:
            self.selected_address = self.addresses[selection]
            self.EndModal(wx.ID_OK)
        else:
            wx.MessageBox("Please select an address", "Error", wx.OK | wx.ICON_WARNING)

    def get_selected_address(self) -> Address | None:
        """Get the selected address."""
        return self.selected_address