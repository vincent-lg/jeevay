#!/usr/bin/env python3
"""
Jeevay - Accessible Geographic Demonstration

A proof-of-concept application that converts neighborhood maps into
accessible ASCII format for use with Braille displays and screen readers.
"""

import sys
import os

import wx

from jeevay.screen_reader import ScreenReader as SR
from jeevay.ui.main_window import JeevayApp


def main():
    """Main application entry point."""
    try:
        SR.setup()
        app = JeevayApp()
        app.MainLoop()
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
