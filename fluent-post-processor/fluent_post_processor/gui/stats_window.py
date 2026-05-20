# -*- coding: utf-8 -*-
"""
stats_window.py
---------------
Qt window for computing range-bounded descriptive statistics
(mean, min, max) on any column of a loaded DataFrame.

Usage
-----
  1. Select the reference column and enter a lower / upper bound.
  2. Click "Calculate Statistics" — the tool filters rows where the
     reference column value lies in [lower, upper] and computes
     mean / min / max for every column in that subset.
  3. Click "Save Results" to export to Excel.

One group box per column is created in a scrollable grid.  Each group
box holds a table that accumulates results across multiple calculations,
allowing easy comparison of different X ranges.
"""

import os

import pandas as pd
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QGridLayout,
)


_STATS_COLS = ("Reference Col", "Lower Bound", "Upper Bound", "Mean", "Min", "Max")


class StatsWindow(QMainWindow):
    """
    Statistics window for a pandas DataFrame.

    Parameters
    ----------
    dataframe : pd.DataFrame
        The data to analyse — typically the monitor or residual DataFrame.
    """

    def __init__(self, dataframe: pd.DataFrame):
        super().__init__()
        self.dataframe = dataframe
        self.setWindowTitle("Statistics Window")
        self.setGeometry(300, 200, 900, 650)

        # {column_name: current_row_index} – tracks insertion point per table
        self._row_index: dict[str, int] = {}
        # [(QGroupBox, QTableWidget)] – one entry per DataFrame column
        self._group_boxes: list[tuple] = []

        self._init_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _init_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        # Scrollable area for the per-column group boxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        scroll_content = QWidget()
        scroll.setWidget(scroll_content)
        grid = QGridLayout(scroll_content)

        # Build one group box + table per column
        for idx, col in enumerate(self.dataframe.columns):
            row_pos, col_pos = divmod(idx, 2)
            group = QGroupBox(f"Column: {col}")
            group_layout = QVBoxLayout(group)

            table = QTableWidget(0, len(_STATS_COLS))
            table.setHorizontalHeaderLabels(list(_STATS_COLS))
            table.horizontalHeader().setStretchLastSection(True)
            group_layout.addWidget(table)

            grid.addWidget(group, row_pos, col_pos)
            self._group_boxes.append((group, table))
            self._row_index[col] = 0

        # Controls — reference column selector + range inputs
        controls = QHBoxLayout()
        outer.addLayout(controls)

        controls.addWidget(QLabel("Reference column:"))
        self.column_selector = QComboBox()
        self.column_selector.addItems(self.dataframe.columns.tolist())
        controls.addWidget(self.column_selector)

        controls.addWidget(QLabel("Lower bound:"))
        self.lower_input = QLineEdit()
        self.lower_input.setFixedWidth(100)
        controls.addWidget(self.lower_input)

        controls.addWidget(QLabel("Upper bound:"))
        self.upper_input = QLineEdit()
        self.upper_input.setFixedWidth(100)
        controls.addWidget(self.upper_input)

        calc_btn = QPushButton("Calculate Statistics")
        calc_btn.clicked.connect(self._calculate)
        outer.addWidget(calc_btn)

        save_btn = QPushButton("Save Results")
        save_btn.clicked.connect(self._on_save)
        outer.addWidget(save_btn)

    # ------------------------------------------------------------------
    # Statistics logic
    # ------------------------------------------------------------------

    def _calculate(self):
        """Filter by range and insert mean/min/max rows into each table."""
        ref_col = self.column_selector.currentText()
        try:
            lower = float(self.lower_input.text())
            upper = float(self.upper_input.text())
        except ValueError:
            return  # Silently ignore invalid input

        mask = (self.dataframe[ref_col] >= lower) & (self.dataframe[ref_col] <= upper)
        subset = self.dataframe[mask]

        for col in self.dataframe.columns:
            table = self._get_table(col)
            if table is None:
                continue
            row = self._row_index.get(col, 0)
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(ref_col))
            table.setItem(row, 1, QTableWidgetItem(str(lower)))
            table.setItem(row, 2, QTableWidgetItem(str(upper)))
            table.setItem(row, 3, QTableWidgetItem(str(subset[col].mean())))
            table.setItem(row, 4, QTableWidgetItem(str(subset[col].min())))
            table.setItem(row, 5, QTableWidgetItem(str(subset[col].max())))
            self._row_index[col] = row + 1

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _on_save(self):
        save_dir = os.path.join(os.getcwd(), "Fluent_Post_Processing_Files")
        os.makedirs(save_dir, exist_ok=True)

        name, ok = QInputDialog.getText(self, "Save Results", "File name (no extension):")
        if not ok or not name:
            return

        rows = []
        for group, table in self._group_boxes:
            col_name = group.title().split("Column:", 1)[1].strip()
            for r in range(table.rowCount()):
                rows.append({
                    "Reference Col":  table.item(r, 0).text(),
                    "Lower Bound":    float(table.item(r, 1).text()),
                    "Upper Bound":    float(table.item(r, 2).text()),
                    "Column":         col_name,
                    "Mean":           float(table.item(r, 3).text()),
                    "Min":            float(table.item(r, 4).text()),
                    "Max":            float(table.item(r, 5).text()),
                })

        pd.DataFrame(rows).to_excel(
            os.path.join(save_dir, f"{name}.xlsx"), index=False
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_table(self, col_name: str) -> QTableWidget | None:
        for group, table in self._group_boxes:
            if group.title().split("Column:", 1)[1].strip() == col_name:
                return table
        return None
