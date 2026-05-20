# -*- coding: utf-8 -*-
"""
residual_plot_window.py
-----------------------
Qt window that displays residual convergence data from .o files.

Two layout modes
  - Single axes  : all selected residuals on one shared axes
  - Matrix       : each residual in its own subplot

Interactive features (via PlotUtility):
  - Scroll-to-zoom
  - Crosshair overlay
  - Middle-click X reference points
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


class ResidualPlotWindow(QMainWindow):
    """
    Standalone window for plotting residual convergence histories.

    Parameters
    ----------
    x_label : str
        Name of the X-axis column (typically 'iter').
    """

    def __init__(self, x_label: str):
        super().__init__()
        self.setWindowTitle("Residual Plot Window")
        self.setGeometry(200, 200, 1200, 800)

        self.x_label = x_label
        self.legend_labels: list[str] = []

        self._init_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.plot_utility = PlotUtility()
        self.plot_utility.canvas = self.canvas
        self.plot_utility.mouse_coordinates_label = QLabel()
        self.plot_utility.stored_x_values_label = QLabel()
        self.plot_utility.vertical_line = None
        self.plot_utility.horizontal_line = None
        self.plot_utility.stored_x_values = []

        label_row = QHBoxLayout()
        label_row.addStretch()
        label_row.addWidget(self.plot_utility.mouse_coordinates_label)
        label_row.addWidget(self.plot_utility.stored_x_values_label)
        layout.addLayout(label_row)
        layout.setAlignment(label_row, Qt.AlignBottom)

        self.canvas.mpl_connect('scroll_event', self.plot_utility.on_scroll)
        self.canvas.mpl_connect('motion_notify_event', self.plot_utility.on_mouse_move)
        self.canvas.mpl_connect('button_press_event', self.plot_utility.on_mouse_click)

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot_residual_data(self, x_data, y_data_df, x_label: str, matrix_plot: bool = False):
        """
        Render residual data.

        Parameters
        ----------
        x_data : pd.Series
            Iteration column.
        y_data_df : pd.DataFrame
            One column per residual quantity to plot.
        x_label : str
            X-axis label.
        matrix_plot : bool
            True → subplot grid; False → shared axes.
        """
        self.figure.clear()
        self.legend_labels = y_data_df.columns.tolist()

        if matrix_plot:
            self._plot_matrix(x_data, y_data_df, x_label)
        else:
            self._plot_single(x_data, y_data_df, x_label)

        self.figure.set_size_inches(12, 7)
        self.canvas.draw()

    def _plot_single(self, x_data, y_data_df, x_label: str):
        ax = self.figure.add_subplot(111)
        for col in y_data_df.columns:
            ax.plot(x_data, y_data_df[col], label=col)
        ax.set_xlabel(x_label)
        ax.set_ylabel('Residual')
        ax.set_title("Residual Convergence")
        ax.legend()
        ax.grid(True)

    def _plot_matrix(self, x_data, y_data_df, x_label: str):
        n = len(y_data_df.columns)
        ncols = min(n, 4)
        nrows = (n + ncols - 1) // ncols
        for i, col in enumerate(y_data_df.columns):
            ax = self.figure.add_subplot(nrows, ncols, i + 1)
            ax.plot(x_data, y_data_df[col], label=col)
            ax.set_xlabel(x_label)
            ax.set_ylabel('Residual')
            ax.set_title(col)
            ax.legend()
            ax.grid(True)
        self.figure.tight_layout()

    # Convenience wrappers kept for backward compatibility
    def plot_residual(self, x_data, y_data_df, x_label: str):
        self.plot_residual_data(x_data, y_data_df, x_label, matrix_plot=False)

    def plot_residual_matrix(self, x_data, y_data_df, x_label: str):
        self.plot_residual_data(x_data, y_data_df, x_label, matrix_plot=True)

    def get_legend_labels(self) -> list[str]:
        return self.legend_labels

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        plt.close(self.figure)
        self.canvas.close()
        event.accept()
