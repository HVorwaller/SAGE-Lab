import pyqtgraph as pg


class GraphManager:
    def __init__(self):
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setBackground("w")
        self.graph_widget.setTitle("Live Gas Concentration Sequence")
        self.graph_widget.setLabel("left", "Concentration", units="%")
        self.graph_widget.setLabel("bottom", "Time", units="min")
        self.graph_widget.showGrid(x=True, y=True)
        self.graph_widget.addLegend()

        self.graph_widget.showAxis("right")
        self.graph_widget.setLabel("right", "Concentration", units="ppm")

        self.percent_plot = self.graph_widget.plotItem
        self.ppm_view = pg.ViewBox()
        self.percent_plot.scene().addItem(self.ppm_view)
        self.percent_plot.getAxis("right").linkToView(self.ppm_view)
        self.ppm_view.setXLink(self.percent_plot)
        self.percent_plot.vb.sigResized.connect(self.update_ppm_view)

        self.ppm_curves = []
        self.percent_curves = []

        self.current_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            movable=False,
            pen=pg.mkPen(width=2)
        )
        self.graph_widget.addItem(self.current_line)

    def update_ppm_view(self):
        self.ppm_view.setGeometry(self.percent_plot.vb.sceneBoundingRect())
        self.ppm_view.linkedViewChanged(
            self.percent_plot.vb,
            self.ppm_view.XAxis
        )

    def clear_curves(self):
        for curve in self.percent_curves:
            self.graph_widget.removeItem(curve)

        for curve in self.ppm_curves:
            self.ppm_view.removeItem(curve)

        self.percent_curves = []
        self.ppm_curves = []

        if self.graph_widget.plotItem.legend is not None:
            self.graph_widget.plotItem.legend.clear()

    def reset(self):
        self.clear_curves()
        self.current_line.setPos(0)
        self.graph_widget.autoRange()
        self.update_ppm_view()

    def set_current_time_seconds(self, current_time_seconds):
        self.current_line.setPos(current_time_seconds / 60)

    def plot_sequence(self, gas_data, percent_columns, ppm_columns):
        self.clear_curves()

        gas_colors = {
            "O2_%": "blue",
            "CO2_%": "red",
            "N2_%": "green",
            "CH4_ppm": "magenta",
        }

        for col in percent_columns:
            color = gas_colors.get(col, "black")

            curve = self.graph_widget.plot(
                gas_data[col]["time"],
                gas_data[col]["value"],
                pen=pg.mkPen(color=color, width=3),
                name=col
            )
            self.percent_curves.append(curve)

        for col in ppm_columns:
            color = gas_colors.get(col, "magenta")

            curve = pg.PlotCurveItem(
                gas_data[col]["time"],
                gas_data[col]["value"],
                pen=pg.mkPen(color=color, width=3)
            )
            self.ppm_view.addItem(curve)

            if self.graph_widget.plotItem.legend is not None:
                self.graph_widget.plotItem.legend.addItem(curve, col)

            self.ppm_curves.append(curve)

        self.current_line.setPos(0)
        self.graph_widget.autoRange()
        self.update_ppm_view()
