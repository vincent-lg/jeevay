import distutils
import opcode
import os
import shutil

from cx_Freeze import setup, Executable

client = Executable(
    script="jeevay/__main__.py",
    base="Win32GUI",
)

includefiles = [
    "accessible_output3",
]

setup(
    name = "Jeevay client",
    version = "0.1",
    description = "The Jeevay client.",
    options = {'build_exe': {
            "include_files": includefiles,
            "excludes": ["_gtkagg", "_tkagg", "bsddb", "distutils", "curses",
                    "pywin.debugger", "pywin.debugger.dbgcon",
                    "pywin.dialogs", "tcl", "Tkconstants", "Tkinter"],
            #"packages": ["accesspanel", "redminelib.resources", "_cffi_backend", "idna.idnadata", "pubsub.pub"],
            #"namespace_packages": ["zope.interface"],
    }},
    executables = [client]
)
