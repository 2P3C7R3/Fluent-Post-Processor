# -*- coding: utf-8 -*-
"""
monitor_plot_window.py
----------------------
Qt window that displays monitor-plot data from .out files.

Supports three layout modes
  - Individual  : all selected Y columns on a single axes
  - Together    : each Y column in its own subplot arranged in a matrix
  - Separate    : each Y column in its own top-level window
                  (handled by MainWindow, not this class)

Interactive features (via PlotUtility):
  - Scroll-to-zoom
  - Crosshair overlay
  - Middle-click to store X reference points
"""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from fluent_post_processor.gui.plot_utility import PlotUtility


class MonitorPlotWindow(QMainWindow):
    """
    Standalone window for plotting one or more monitor quantities
    against a chosen X axis (Iteration / Time Step / flow-time).

    Parameters
    ----------
    x_label : str
        Name of the X-axis column.
    y_data_list : list of (pd.Series, str)
        Each element is a ``(series, column_name)`` pair.
    """

    def __init__(self, x_label: str, y_data_list: list):
        super().__init__()
        self.setWindowTitle("Monitor Plot Window")
        self.setGeometry(200, 200, 1200, 800)

        self.x_label = x_label
        self.y_data_list = y_data_list
        self.legend_labels = [label for _, label in y_data_list]

        self._init_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # --- Matplotlib figure ---
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # --- PlotUtility (interactivity) ---
        self.plot_utility = PlotUtility()
        self.plot_utility.canvas = self.canvas
        self.plot_utility.mouse_coordinates_label = QLabel()
        self.plot_utility.stored_x_values_label = QLabel()
        self.plot_utility.vertical_line = None
        self.plot_utility.horizontal_line = None
        self.plot_utility.stored_x_values = []

        # --- Coordinate labels (bottom-right) ---
        label_row = QHBoxLayout()
        label_row.addStretch()
        label_row.addWidget(self.plot_utility.mouse_coordinates_label)
        label_row.addWidget(self.plot_utility.stored_x_values_label)
        layout.addLayout(label_row)
        layout.setAlignment(label_row, Qt.AlignBottom)

        # --- Connect events ---
        self.canvas.mpl_connect('scroll_event', self.plot_utility.on_scroll)
        self.canvas.mpl_connect('motion_notify_event', self.plot_utility.on_mouse_move)
        self.canvas.mpl_connect('button_press_event', self.plot_utility.on_mouse_click)

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot_data(self, x_data, y_data_list: list, x_label: str, plot_together: bool = False):
        """
        Render data onto the figure.

        Parameters
        ----------
        x_data : pd.Series
            X-axis values.
        y_data_list : list of (pd.Series, str)
            Y data and column labels.
        x_label : str
            X-axis label string.
        plot_together : bool
            If True, each Y column gets its own subplot (matrix layout).
            If False, all Y columns share one axes.
        """
        self.figure.clear()
        if plot_together:
            self._plot_matrix(x_data, y_data_list, x_label)
        else:
            self._plot_single(x_data, y_data_list, x_label)
        self.figure.tight_layout()
        self.canvas.draw()

    def _plot_single(self, x_data, y_data_list: list, x_label: str):
        """All Y series on one shared axes."""
        ax = self.figure.add_subplot(111)
        for data, column in y_data_list:
            ax.plot(x_data, data, label=column)
        ax.set_xlabel(x_label)
        ax.set_ylabel('Value')
        ax.set_title("Monitor Plot")
        ax.legend()
        ax.grid(True)
        self.figure.set_size_inches(12, 7)

    def _plot_matrix(self, x_data, y_data_list: list, x_label: str):
        """One subplot per Y series, arranged in a grid."""
        n = len(y_data_list)
        if n <= 3:
            ncols = n
        elif n == 4:
            ncols = 2
        elif n <= 6:
            ncols = 3
        else:
            ncols = 4
        nrows = (n + ncols - 1) // ncols

        axes = self.figure.subplots(nrows, ncols, squeeze=False).flatten()
        for i, (data, column) in enumerate(y_data_list):
            ax = axes[i]
            ax.plot(x_data, data, label=column)
            ax.set_xlabel(x_label)
            ax.set_ylabel('Value')
            ax.set_title(column)
            ax.legend()
            ax.grid(True)

        # Hide any unused subplot axes
        for j in range(n, len(axes)):
            axes[j].set_visible(False)

        self.figure.set_size_inches(12, 8)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        plt.close(self.figure)
        self.canvas.close()
        event.accept()
