"""
Interactive Python console for development.

This console runs in a separate thread and allows interactive interrogation
of the map and application state. Code is executed in the main thread to
ensure thread safety with wx.
"""

import sys
import threading
import traceback
import code
from typing import Any, Callable
import wx


class DevConsole:
    """Interactive Python console for development."""

    def __init__(self, main_window):
        """
        Initialize the development console.

        Args:
            main_window: The MainWindow instance to provide access to app state
        """
        self.main_window = main_window
        self.console_thread = None
        self.running = False
        self._local_namespace = {}

    def start(self):
        """Start the console in a separate thread."""
        if self.running:
            return

        self.running = True
        self.console_thread = threading.Thread(target=self._run_console, daemon=True)
        self.console_thread.start()

    def stop(self):
        """Stop the console."""
        self.running = False

    def _run_console(self):
        """Run the interactive console (in separate thread)."""
        try:
            # Set up the console with a custom InteractiveConsole
            console = MainThreadInteractiveConsole(
                self.main_window,
                locals=self._get_console_namespace()
            )

            # Print banner
            print("\n" + "="*60)
            print("Jeevay Development Console")
            print("="*60)
            print("Available variables:")
            print("  window     - Main window instance")
            print("  network    - Current street network")
            print("  address    - Current address")
            print("  display    - Map display widget")
            print("  geocoder   - Geocoding API")
            print("  overpass   - Overpass API")
            print("  renderer   - ASCII renderer")
            print("\nPress Ctrl+C to exit console")
            print("="*60 + "\n")

            # Start interactive loop
            console.interact(banner="", exitmsg="")

        except KeyboardInterrupt:
            print("\n\nConsole terminated.")
        except Exception as e:
            print(f"\nConsole error: {e}")
            traceback.print_exc()
        finally:
            self.running = False

    def _get_console_namespace(self):
        """Get the namespace dictionary for the console."""
        return {
            'window': self.main_window,
            'network': lambda: self.main_window.current_network,
            'address': lambda: self.main_window.current_address,
            'display': self.main_window.map_display,
            'geocoder': self.main_window.geocoder,
            'overpass': self.main_window.overpass,
            'renderer': self.main_window.renderer,
        }


class MainThreadInteractiveConsole(code.InteractiveConsole):
    """
    Interactive console that executes code in the main thread.

    This ensures thread safety when interacting with wx widgets and application state.
    """

    def __init__(self, main_window, locals=None):
        """
        Initialize the console.

        Args:
            main_window: MainWindow instance for executing code in main thread
            locals: Local namespace for the console
        """
        # Evaluate any lambda/callable values in locals
        if locals:
            locals = {k: v() if callable(v) else v for k, v in locals.items()}

        super().__init__(locals=locals)
        self.main_window = main_window

    def runcode(self, code_obj):
        """
        Execute a code object.

        This is executed in the main thread via wx.CallAfter to ensure
        thread safety with wx components.

        Args:
            code_obj: Compiled code object to execute
        """
        # Create event to wait for execution
        result_event = threading.Event()
        result_container = {'output': None, 'error': None}

        def execute_in_main_thread():
            """Execute the code in the main thread."""
            # Update namespace with current values
            self.locals['network'] = self.main_window.current_network
            self.locals['address'] = self.main_window.current_address

            # Capture stdout/stderr
            old_stdout = sys.stdout
            old_stderr = sys.stderr

            try:
                from io import StringIO
                sys.stdout = StringIO()
                sys.stderr = StringIO()

                # Execute the code
                exec(code_obj, self.locals)

                # Get output
                stdout_value = sys.stdout.getvalue()
                stderr_value = sys.stderr.getvalue()

                result_container['output'] = stdout_value
                if stderr_value:
                    result_container['error'] = stderr_value

            except SystemExit:
                raise
            except:
                # Capture exception
                result_container['error'] = traceback.format_exc()
            finally:
                # Restore stdout/stderr
                sys.stdout = old_stdout
                sys.stderr = old_stderr
                result_event.set()

        # Schedule execution in main thread
        wx.CallAfter(execute_in_main_thread)

        # Wait for completion
        result_event.wait()

        # Display results
        if result_container['output']:
            print(result_container['output'], end='')

        if result_container['error']:
            print(result_container['error'], end='', file=sys.stderr)
