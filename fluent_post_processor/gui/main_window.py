# -*- coding: utf-8 -*-
"""
main_window.py
--------------
Main application window for the Fluent Post-Processor.

Two-tab layout
  Tab 1 – Monitor Plot  : load and visualise .out monitor files
  Tab 2 – Residual Data : load and visualise .o residual files

Auto-refresh
  A QTimer fires every 5 minutes to reload data from disk, so the tool
  can be left open during an active Fluent run and will pick up new data
  without manual intervention.  Open plot windows are automatically
  re-plotted with the refreshed data.
"""

import os

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from fluent_post_processor.data.monitor_dataframe import MonitorPlotDataFrame
from fluent_post_processor.data.residual_dataframe import ResidualDataFrame
from fluent_post_processor.gui.monitor_plot_window import MonitorPlotWindow
from fluent_post_processor.gui.residual_plot_window import ResidualPlotWindow
from fluent_post_processor.gui.stats_window import StatsWindow

_REFRESH_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes


class MainWindow(QMainWindow):
    """Top-level application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fluent Post-Processor v2.0")
        self.setGeometry(100, 100, 900, 700)

        self._plot_windows: list[QMainWindow] = []

        # Data models – populated in load methods
        self._monitor_data = MonitorPlotDataFrame(os.getcwd())
        self._residual_data = ResidualDataFrame()

        # Column button groups – populated after data load
        self._monitor_y_buttons: list[QPushButton] = []
        self._monitor_x_group: QButtonGroup | None = None
        self._residual_y_buttons: list[QPushButton] = []
        self._residual_x_group: QButtonGroup | None = None

        self._init_ui()
        self._load_all()

        # Auto-refresh timer
        self._timer = QTimer()
        self._timer.timeout.connect(self._load_all)
        self._timer.start(_REFRESH_INTERVAL_MS)

    # ==================================================================
    # UI construction
    # ==================================================================

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        tabs = QTabWidget(self)
        layout.addWidget(tabs)

        tab1 = QWidget()
        tab2 = QWidget()
        tabs.addTab(tab1, "Monitor Plot (.out)")
        tabs.addTab(tab2, "Residual Data (.o)")

        self._build_monitor_tab(tab1)
        self._build_residual_tab(tab2)

    # ------------------------------------------------------------------
    # Monitor tab
    # ------------------------------------------------------------------

    def _build_monitor_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)

        # Action buttons
        btn_row = QHBoxLayout()
        for label, slot in [
            ("Load Data",      self._load_monitor),
            ("Save to Excel",  self._save_monitor_excel),
            ("Open Stats",     self._open_monitor_stats),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        self._monitor_status = QLabel("Status: not loaded")
        layout.addWidget(self._monitor_status)

        # Y-axis buttons (populated dynamically)
        layout.addWidget(QLabel("Select columns to plot (Y):"))
        scroll_y = QScrollArea()
        scroll_y.setWidgetResizable(True)
        scroll_y.setMaximumHeight(160)
        self._monitor_y_container = QWidget()
        self._monitor_y_layout = QGridLayout(self._monitor_y_container)
        scroll_y.setWidget(self._monitor_y_container)
        layout.addWidget(scroll_y)

        # X-axis buttons (populated dynamically)
        layout.addWidget(QLabel("Select X axis:"))
        self._monitor_x_container = QWidget()
        self._monitor_x_layout = QGridLayout(self._monitor_x_container)
        layout.addWidget(self._monitor_x_container)
        self._monitor_x_group = QButtonGroup(self)
        self._monitor_x_group.setExclusive(True)

        # Plot mode buttons
        layout.addWidget(QLabel("Plot mode:"))
        mode_row = QHBoxLayout()
        for label, slot in [
            ("Plot (overlay)",   self._monitor_plot),
            ("Plot Together",    self._monitor_plot_together),
            ("Plot Separate",    self._monitor_plot_separate),
            ("Cancel Selection", self._monitor_cancel),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            mode_row.addWidget(btn)
        layout.addLayout(mode_row)

    # ------------------------------------------------------------------
    # Residual tab
    # ------------------------------------------------------------------

    def _build_residual_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)

        btn_row = QHBoxLayout()
        for label, slot in [
            ("Load Data",      self._load_residual),
            ("Save to Excel",  self._save_residual_excel),
            ("Open Stats",     self._open_residual_stats),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        self._residual_status = QLabel("Status: not loaded")
        layout.addWidget(self._residual_status)

        layout.addWidget(QLabel("Select residuals to plot (Y):"))
        scroll_y = QScrollArea()
        scroll_y.setWidgetResizable(True)
        scroll_y.setMaximumHeight(160)
        self._residual_y_container = QWidget()
        self._residual_y_layout = QGridLayout(self._residual_y_container)
        scroll_y.setWidget(self._residual_y_container)
        layout.addWidget(scroll_y)

        layout.addWidget(QLabel("X axis:"))
        self._residual_x_container = QWidget()
        self._residual_x_layout = QGridLayout(self._residual_x_container)
        layout.addWidget(self._residual_x_container)
        self._residual_x_group = QButtonGroup(self)
        self._residual_x_group.setExclusive(True)

        mode_row = QHBoxLayout()
        for label, slot in [
            ("Plot (overlay)",   self._residual_plot),
            ("Plot Together",    self._residual_plot_together),
            ("Plot Separate",    self._residual_plot_separate),
            ("Cancel Selection", self._residual_cancel),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            mode_row.addWidget(btn)
        layout.addLayout(mode_row)

    # ==================================================================
    # Data loading
    # ==================================================================

    def _load_all(self):
        self._load_monitor()
        self._load_residual()

    def _load_monitor(self):
        self._monitor_data = MonitorPlotDataFrame(os.getcwd())
        msg = self._monitor_data.merge_dataframes()
        self._monitor_data.sort_by_common_columns()
        self._monitor_data.replace_special_characters_in_columns()

        if msg:
            self._monitor_status.setText(f"Status: {msg}")
        else:
            self._monitor_status.setText("Status: Monitor data loaded")

        self._populate_monitor_buttons()
        self._refresh_open_monitor_windows()

    def _load_residual(self):
        self._residual_data = ResidualDataFrame()
        self._residual_data.load_files(os.getcwd())
        self._residual_data.load_data()
        self._residual_status.setText("Status: Residual data loaded")
        self._populate_residual_buttons()
        self._refresh_open_residual_windows()

    # ==================================================================
    # Dynamic button population
    # ==================================================================

    def _clear_layout(self, layout: QGridLayout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_monitor_buttons(self):
        if self._monitor_data.monitor_plot_out_file_df is None:
            return
        cols = list(self._monitor_data.monitor_plot_out_file_df.columns)

        # Y buttons
        self._clear_layout(self._monitor_y_layout)
        self._monitor_y_buttons = []
        for i, col in enumerate(cols):
            btn = QPushButton(col)
            btn.setCheckable(True)
            self._monitor_y_layout.addWidget(btn, i // 5, i % 5)
            self._monitor_y_buttons.append(btn)

        # X buttons (only time/iteration columns)
        self._clear_layout(self._monitor_x_layout)
        # Remove old buttons from group
        for b in self._monitor_x_group.buttons():
            self._monitor_x_group.removeButton(b)
        x_candidates = ['Iteration', 'Time Step', 'flow_time', 'flow-time']
        c = 0
        for col in x_candidates:
            if col in cols:
                btn = QPushButton(col)
                btn.setCheckable(True)
                self._monitor_x_layout.addWidget(btn, 0, c)
                self._monitor_x_group.addButton(btn)
                c += 1

    def _populate_residual_buttons(self):
        if self._residual_data.residual_df is None:
            return
        cols = list(self._residual_data.residual_df.columns)

        self._clear_layout(self._residual_y_layout)
        self._residual_y_buttons = []
        for i, col in enumerate(cols):
            btn = QPushButton(col)
            btn.setCheckable(True)
            self._residual_y_layout.addWidget(btn, i // 5, i % 5)
            self._residual_y_buttons.append(btn)

        self._clear_layout(self._residual_x_layout)
        for b in self._residual_x_group.buttons():
            self._residual_x_group.removeButton(b)
        if 'iter' in cols:
            btn = QPushButton('iter')
            btn.setCheckable(True)
            self._residual_x_layout.addWidget(btn, 0, 0)
            self._residual_x_group.addButton(btn)

    # ==================================================================
    # Plot helpers
    # ==================================================================

    def _selected_monitor_y(self) -> list[str]:
        return [b.text() for b in self._monitor_y_buttons if b.isChecked()]

    def _selected_monitor_x(self) -> str | None:
        checked = [b for b in self._monitor_x_group.buttons() if b.isChecked()]
        return checked[0].text() if checked else None

    def _selected_residual_y(self) -> list[str]:
        return [b.text() for b in self._residual_y_buttons if b.isChecked()]

    def _selected_residual_x(self) -> str | None:
        checked = [b for b in self._residual_x_group.buttons() if b.isChecked()]
        return checked[0].text() if checked else None

    # ------------------------------------------------------------------
    # Monitor plot actions
    # ------------------------------------------------------------------

    def _monitor_plot(self):
        self._do_monitor_plot(together=False)

    def _monitor_plot_together(self):
        self._do_monitor_plot(together=True)

    def _do_monitor_plot(self, together: bool):
        y_cols = self._selected_monitor_y()
        x_col = self._selected_monitor_x()
        if not y_cols or not x_col:
            self._monitor_status.setText("Status: select X and at least one Y column")
            return
        df = self._monitor_data.monitor_plot_out_file_df
        x_data = df[x_col]
        y_data_list = [(df[c], c) for c in y_cols]
        win = MonitorPlotWindow(x_col, y_data_list)
        win.plot_data(x_data, y_data_list, x_col, plot_together=together)
        win.show()
        self._plot_windows.append(win)
        self._monitor_cancel()
        self._monitor_status.setText(
            f"Status: plotted {', '.join(y_cols)} vs {x_col}"
        )

    def _monitor_plot_separate(self):
        y_cols = self._selected_monitor_y()
        x_col = self._selected_monitor_x()
        if not y_cols or not x_col:
            self._monitor_status.setText("Status: select X and at least one Y column")
            return
        df = self._monitor_data.monitor_plot_out_file_df
        x_data = df[x_col]
        for col in y_cols:
            win = MonitorPlotWindow(x_col, [(df[col], col)])
            win.plot_data(x_data, [(df[col], col)], x_col, plot_together=False)
            win.show()
            self._plot_windows.append(win)
        self._monitor_cancel()
        self._monitor_status.setText(
            f"Status: plotted {', '.join(y_cols)} vs {x_col} (separate)"
        )

    def _monitor_cancel(self):
        for b in self._monitor_y_buttons:
            b.setChecked(False)
        for b in self._monitor_x_group.buttons():
            b.setChecked(False)

    # ------------------------------------------------------------------
    # Residual plot actions
    # ------------------------------------------------------------------

    def _residual_plot(self):
        self._do_residual_plot(matrix=False)

    def _residual_plot_together(self):
        self._do_residual_plot(matrix=True)

    def _do_residual_plot(self, matrix: bool):
        y_cols = self._selected_residual_y()
        x_col = self._selected_residual_x()
        if not y_cols or not x_col:
            self._residual_status.setText("Status: select X and at least one Y column")
            return
        df = self._residual_data.residual_df
        win = ResidualPlotWindow(x_col)
        win.plot_residual_data(df[x_col], df[y_cols], x_col, matrix_plot=matrix)
        win.show()
        self._plot_windows.append(win)
        self._residual_cancel()
        self._residual_status.setText(
            f"Status: plotted {', '.join(y_cols)} vs {x_col}"
        )

    def _residual_plot_separate(self):
        y_cols = self._selected_residual_y()
        x_col = self._selected_residual_x()
        if not y_cols or not x_col:
            self._residual_status.setText("Status: select X and at least one Y column")
            return
        df = self._residual_data.residual_df
        for col in y_cols:
            win = ResidualPlotWindow(x_col)
            win.plot_residual_data(df[x_col], df[[col]], x_col)
            win.show()
            self._plot_windows.append(win)
        self._residual_cancel()

    def _residual_cancel(self):
        for b in self._residual_y_buttons:
            b.setChecked(False)
        for b in self._residual_x_group.buttons():
            b.setChecked(False)

    # ------------------------------------------------------------------
    # Excel export
    # ------------------------------------------------------------------

    def _save_monitor_excel(self):
        folder = os.path.join(os.getcwd(), "Fluent_Post_Processing_Files")
        os.makedirs(folder, exist_ok=True)
        self._monitor_data.save_to_excel(os.path.join(folder, "monitor_dataframe.xlsx"))
        self._monitor_status.setText("Status: saved monitor_dataframe.xlsx")

    def _save_residual_excel(self):
        folder = os.path.join(os.getcwd(), "Fluent_Post_Processing_Files")
        os.makedirs(folder, exist_ok=True)
        self._residual_data.save_to_excel(os.path.join(folder, "residual_dataframe.xlsx"))
        self._residual_status.setText("Status: saved residual_dataframe.xlsx")

    # ------------------------------------------------------------------
    # Stats windows
    # ------------------------------------------------------------------

    def _open_monitor_stats(self):
        if self._monitor_data.monitor_plot_out_file_df is not None:
            win = StatsWindow(self._monitor_data.monitor_plot_out_file_df)
            win.show()
            self._plot_windows.append(win)

    def _open_residual_stats(self):
        if self._residual_data.residual_df is not None:
            win = StatsWindow(self._residual_data.residual_df)
            win.show()
            self._plot_windows.append(win)

    # ------------------------------------------------------------------
    # Auto-refresh: replot open windows with updated data
    # ------------------------------------------------------------------

    def _refresh_open_monitor_windows(self):
        df = self._monitor_data.monitor_plot_out_file_df
        if df is None:
            return
        for win in self._plot_windows:
            if isinstance(win, MonitorPlotWindow) and not win.isHidden():
                y_data = [(df[col], col) for col in win.legend_labels if col in df.columns]
                if win.x_label in df.columns and y_data:
                    win.plot_data(df[win.x_label], y_data, win.x_label)

    def _refresh_open_residual_windows(self):
        df = self._residual_data.residual_df
        if df is None:
            return
        for win in self._plot_windows:
            if isinstance(win, ResidualPlotWindow) and not win.isHidden():
                labels = win.get_legend_labels()
                valid = [c for c in labels if c in df.columns]
                if win.x_label in df.columns and valid:
                    win.plot_residual_data(df[win.x_label], df[valid], win.x_label)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        for win in self._plot_windows:
            win.close()
        event.accept()
