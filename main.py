#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
main.py
-------
Entry point for the Fluent Post-Processor.

Run from the directory that contains your .out and .o<n> simulation files:

    python main.py

Or, if you built a standalone executable with PyInstaller:

    FluentPostProcessor.exe          (Windows)
    ./FluentPostProcessor            (Linux / macOS)
"""

import sys

from PyQt5.QtWidgets import QApplication

from fluent_post_processor.gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Fluent Post-Processor")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
