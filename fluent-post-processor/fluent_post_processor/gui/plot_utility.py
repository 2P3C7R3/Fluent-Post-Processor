# -*- coding: utf-8 -*-
"""
plot_utility.py
---------------
Mixin class providing interactive plot behaviour:
  - Scroll-to-zoom (centred on cursor)
  - Crosshair overlay that tracks the mouse pointer
  - Middle-click to store up to two X reference points
  - Right-click to clear stored X points
"""

from matplotlib.backend_bases import MouseEvent


class PlotUtility:
    """
    Mixin that adds mouse-driven interactivity to a matplotlib canvas.

    Expected attributes set by the host window before use:
        self.plot_utility.canvas                  – FigureCanvas instance
        self.plot_utility.mouse_coordinates_label – QLabel for live coordinates
        self.plot_utility.stored_x_values_label   – QLabel for stored X values
        self.plot_utility.vertical_line           – initialise to None
        self.plot_utility.horizontal_line         – initialise to None
        self.plot_utility.stored_x_values         – initialise to []
    """

    def __init__(self):
        self.canvas = None

    # ------------------------------------------------------------------
    # Zoom
    # ------------------------------------------------------------------

    def on_scroll(self, event: MouseEvent):
        """Zoom in / out centred on the cursor position."""
        if self.canvas and event.inaxes is not None:
            ax = event.inaxes
            x_min, x_max = ax.get_xlim()
            y_min, y_max = ax.get_ylim()
            zoom_factor = 0.5

            if event.button == 'up':
                # Zoom in
                x_c, y_c = event.xdata, event.ydata
                ax.set_xlim(
                    x_min * zoom_factor + (1 - zoom_factor) * x_c,
                    x_max * zoom_factor + (1 - zoom_factor) * x_c,
                )
                ax.set_ylim(
                    y_min * zoom_factor + (1 - zoom_factor) * y_c,
                    y_max * zoom_factor + (1 - zoom_factor) * y_c,
                )
            elif event.button == 'down':
                # Zoom out
                x_c, y_c = event.xdata, event.ydata
                ax.set_xlim(
                    x_min / zoom_factor + (1 - 1 / zoom_factor) * x_c,
                    x_max / zoom_factor + (1 - 1 / zoom_factor) * x_c,
                )
                ax.set_ylim(
                    y_min / zoom_factor + (1 - 1 / zoom_factor) * y_c,
                    y_max / zoom_factor + (1 - 1 / zoom_factor) * y_c,
                )
            self.canvas.draw()

    # ------------------------------------------------------------------
    # Crosshair
    # ------------------------------------------------------------------

    def on_mouse_move(self, event: MouseEvent):
        """Draw a live crosshair and update the coordinate label."""
        if self.canvas and event.inaxes is not None:
            ax = event.inaxes
            x, y = event.xdata, event.ydata
            self.remove_crosshair_lines()
            self.vertical_line = ax.axvline(x, color='gray', linestyle='--', lw=1)
            self.horizontal_line = ax.axhline(y, color='gray', linestyle='--', lw=1)
            self.canvas.draw()
            self.mouse_coordinates_label.setText(
                f'Mouse Pointer: (x={x:.0f}, y={y:.6f})'
            )

    def remove_crosshair_lines(self):
        """Remove existing crosshair lines from the axes."""
        if self.canvas:
            if self.vertical_line is not None:
                self.vertical_line.remove()
                self.vertical_line = None
            if self.horizontal_line is not None:
                self.horizontal_line.remove()
                self.horizontal_line = None

    # ------------------------------------------------------------------
    # Click-to-store X values
    # ------------------------------------------------------------------

    def on_mouse_click(self, event: MouseEvent):
        """
        Middle-click: store up to two X reference values (for range stats).
        Right-click : clear stored values.
        """
        if self.canvas:
            if event.button == 2:  # Middle mouse button
                if len(self.stored_x_values) < 2 and event.inaxes is not None:
                    self.stored_x_values.append(event.xdata)
                    self.update_stored_x_values_label()
                    self.canvas.draw()
            elif event.button == 3:  # Right mouse button
                self.stored_x_values.clear()
                self.update_stored_x_values_label()
                self.canvas.draw()

    def update_stored_x_values_label(self):
        """Refresh the stored-X-values display label."""
        n = len(self.stored_x_values)
        if n == 1:
            self.stored_x_values_label.setText(
                f'Stored X-Values: ({self.stored_x_values[0]:.5f},)'
            )
        elif n == 2:
            self.stored_x_values_label.setText(
                f'Stored X-Values: ({self.stored_x_values[0]:.5f}, '
                f'{self.stored_x_values[1]:.5f})'
            )
        else:
            self.stored_x_values_label.setText('Stored X-Values:')
