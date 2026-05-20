# -*- coding: utf-8 -*-
"""
monitor_dataframe.py
--------------------
Parses and merges ANSYS Fluent monitor-plot output files (.out).

.out file format
----------------
Line 0  : Fluent version / case header (ignored)
Line 1  : Description comment (ignored)
Line 2  : Column names in double-quoted tokens, e.g.
              ("Time Step" "flow-time" "drag-1" "lift-1")
Line 3+ : Space-separated numerical data rows

Multiple .out files from the same simulation (e.g. one per monitor)
are outer-merged on their shared columns (Iteration / Time Step /
flow-time) to produce a single combined DataFrame.
"""

import os
import re

import pandas as pd


class MonitorPlotDataFrame:
    """
    Load, merge, and expose data from all .out files in a directory.

    Parameters
    ----------
    directory_path : str
        Path to the folder containing .out files.

    Attributes
    ----------
    monitor_plot_out_file_df : pd.DataFrame or None
        Merged DataFrame of all successfully loaded .out files.
    common_cols : list[str] or None
        Column names used as the merge key across files.
    """

    def __init__(self, directory_path: str):
        self.directory_path = directory_path
        self.file_list: list[str] = self._get_file_list()
        self.dataframes: list[pd.DataFrame] = self._process_all_files()
        self.monitor_plot_out_file_df: pd.DataFrame | None = None
        self.common_cols: list[str] | None = None

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def _get_file_list(self) -> list[str]:
        """Return all .out filenames in the working directory."""
        return [f for f in os.listdir(self.directory_path) if f.endswith('.out')]

    # ------------------------------------------------------------------
    # Parsing a single .out file
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_quoted_tokens(line: str) -> list[str]:
        """Extract all double-quoted tokens from a header line."""
        return re.findall(r'"(.*?)"', line)

    def _parse_file(self, filename: str) -> pd.DataFrame | None:
        """
        Parse one .out file into a DataFrame.

        Returns None if the file has fewer than 4 lines or cannot be parsed.
        """
        path = os.path.join(self.directory_path, filename)
        with open(path, 'r') as fh:
            lines = fh.readlines()

        if len(lines) < 4:
            print(f"[MonitorPlotDataFrame] Skipping '{filename}': too few lines.")
            return None

        column_names = self._extract_quoted_tokens(lines[2].strip())
        data_rows = [line.strip().split() for line in lines[3:] if line.strip()]

        df = pd.DataFrame(data_rows, columns=column_names)
        df = df.apply(pd.to_numeric, errors='ignore')
        return df

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    def _process_all_files(self) -> list[pd.DataFrame]:
        """Parse every .out file; skip files that fail."""
        frames = []
        for filename in self.file_list:
            df = self._parse_file(filename)
            if df is not None:
                frames.append(df)
        return frames

    # ------------------------------------------------------------------
    # Merging
    # ------------------------------------------------------------------

    @staticmethod
    def _merge_two(df1: pd.DataFrame, df2: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """
        Outer-merge two DataFrames on their shared columns.

        Raises ValueError if no common columns are found.
        """
        common = [c for c in df2.columns if c in df1.columns]
        if not common:
            raise ValueError("No common columns to merge on.")
        merged = pd.merge(df1, df2, on=common, how='outer', suffixes=('_x', '_y'))
        return merged, common

    def merge_dataframes(self) -> str | None:
        """
        Merge all parsed DataFrames into ``self.monitor_plot_out_file_df``.

        Files with no columns in common with the growing result are skipped
        and reported in the returned status message.

        Returns
        -------
        str or None
            A human-readable warning listing ignored files, or None on success.
        """
        result = pd.DataFrame()
        ignored: list[str] = []
        common_cols: list[str] = []

        for filename, df in zip(self.file_list, self.dataframes):
            if result.empty:
                result = df.copy()
                common_cols = df.columns.tolist()
            else:
                try:
                    result, common_cols = self._merge_two(result, df)
                except ValueError:
                    ignored.append(filename)

        self.monitor_plot_out_file_df = result
        self.common_cols = common_cols

        if ignored:
            return f"Ignored files (no common columns): {', '.join(ignored)}"
        return None

    # ------------------------------------------------------------------
    # Post-merge helpers
    # ------------------------------------------------------------------

    def replace_special_characters_in_columns(self):
        """
        Sanitise column names by replacing characters outside
        ``[\\w\\s()\\-]`` with underscores.
        """
        if self.monitor_plot_out_file_df is not None:
            pattern = r'[^\w\s()\-]'
            self.monitor_plot_out_file_df.columns = [
                re.sub(pattern, '_', col)
                for col in self.monitor_plot_out_file_df.columns
            ]

    def sort_by_common_columns(self):
        """Sort the merged DataFrame by the merge-key columns."""
        if self.common_cols and self.monitor_plot_out_file_df is not None:
            self.monitor_plot_out_file_df.sort_values(
                by=self.common_cols, inplace=True
            )

    def save_to_excel(self, output_path: str):
        """Export the merged DataFrame to an Excel file."""
        if self.monitor_plot_out_file_df is not None:
            self.monitor_plot_out_file_df.to_excel(output_path, index=False)
        else:
            print("[MonitorPlotDataFrame] No data loaded — nothing to save.")
