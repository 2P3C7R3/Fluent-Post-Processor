# -*- coding: utf-8 -*-
"""
residual_dataframe.py
---------------------
Parses ANSYS Fluent residual output files (.o<n>).

.o file format
--------------
The file mixes Fluent console output with the residual table.  The
parser looks for two kinds of lines:

  Header line  – starts with '  iter' followed by column names,
                 e.g.  '  iter  continuity  x-velocity  y-velocity  ...'
                 The last token on this line is discarded (wall-clock
                 label).

  Data rows    – lines whose first 5+ whitespace-delimited tokens are
                 all parseable as floats.  The last two tokens of each
                 row are trimmed (they carry time and wall-clock values
                 that aren't part of the residual vector).

Filename convention
-------------------
ANSYS Fluent names residual files as ``<case>.o<n>`` where <n> is an
integer, e.g. ``nozzle.o1``.  The loader scans the working directory
for the first file matching this pattern.
"""

import os

import pandas as pd


class ResidualDataFrame:
    """
    Load and expose residual convergence data from a Fluent .o file.

    Attributes
    ----------
    residual_df : pd.DataFrame or None
        Parsed residual data; columns mirror the Fluent residual table
        (iter, continuity, x-velocity, …).
    """

    def __init__(self):
        self.file_list: list[str] = []
        self.iter_columns: list[str] = []
        self.residual_df: pd.DataFrame | None = None

    # ------------------------------------------------------------------
    # File discovery
    # ------------------------------------------------------------------

    def load_files(self, directory_path: str):
        """
        Find the first .o<n> file in *directory_path* and store its path.

        Only the first matching file is used; Fluent writes one residual
        file per run (overwriting on restart).
        """
        for filename in os.listdir(directory_path):
            base, _, suffix = filename.partition('.o')
            if suffix.isdigit():
                self.file_list.append(os.path.join(directory_path, filename))
                break

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_lines(filepath: str) -> list[str]:
        with open(filepath, 'r') as fh:
            return fh.readlines()

    @staticmethod
    def _find_header_line(lines: list[str]) -> str:
        """
        Return the first line that starts with '  iter'.

        This is the column-name header of the residual table.
        """
        for line in lines:
            if line.startswith('  iter'):
                return line
        raise ValueError("No residual header line ('  iter ...') found in file.")

    @staticmethod
    def _extract_numerical_lines(lines: list[str]) -> list[str]:
        """
        Return lines whose first ≥5 tokens are all valid floats.

        These are the actual residual data rows (as opposed to Fluent
        console messages interspersed in the file).
        """
        numerical = []
        for line in lines:
            if not line.strip():
                continue
            tokens = line.split()
            count = 0
            for token in tokens:
                try:
                    float(token)
                    count += 1
                except ValueError:
                    break
            if count >= 5:
                numerical.append(line)
        return numerical

    # ------------------------------------------------------------------
    # Public loader
    # ------------------------------------------------------------------

    def load_data(self):
        """
        Parse the discovered .o file and populate ``self.residual_df``.

        Column names are taken from the '  iter ...' header; the last
        column (wall-clock) is dropped.  Data rows likewise have their
        final two tokens trimmed before being stored.
        """
        if not self.file_list:
            print("[ResidualDataFrame] No .o file found — call load_files() first.")
            return

        filepath = self.file_list[0]
        lines = self._read_lines(filepath)

        # --- column names ---
        header_line = self._find_header_line(lines)
        self.iter_columns = header_line.strip().split()[:-1]  # drop last token

        # --- data rows ---
        numerical_lines = self._extract_numerical_lines(lines)
        parsed_rows = []
        for line in numerical_lines:
            tokens = line.strip().split()[:-2]  # drop last two tokens
            if len(tokens) == len(self.iter_columns):
                parsed_rows.append(list(map(float, tokens)))

        self.residual_df = pd.DataFrame(parsed_rows, columns=self.iter_columns)
        self.residual_df['iter'] = self.residual_df['iter'].astype(int)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def save_to_excel(self, output_path: str):
        """Write the residual DataFrame to an Excel file."""
        if self.residual_df is not None:
            self.residual_df.to_excel(output_path, index=False)
        else:
            print("[ResidualDataFrame] No data loaded — nothing to save.")
