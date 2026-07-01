class MFCController:
    def __init__(self, mock_mode=True):
        self.mock_mode = mock_mode
        self.connected = False
        self.flows = {}

        self.port_name = None
        self.serial_port = None
        self.connection = None
        self.devices = {}

    def connect(self, port=None, addresses=None):
        if self.mock_mode:
            self.connected = True
            print("MFC controller connected in MOCK mode.")
            return True

        if port is None:
            raise RuntimeError("No COM port selected.")

        if not addresses:
            raise RuntimeError("No MFC addresses provided.")

        try:
            from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
            from sensirion_shdlc_sfc5xxx import (
                Sfc5xxxShdlcDevice,
                Sfc5xxxScaling,
                Sfc5xxxMediumUnit,
                Sfc5xxxUnitPrefix,
                Sfc5xxxUnit,
                Sfc5xxxUnitTimeBase,
            )

            self.Sfc5xxxScaling = Sfc5xxxScaling

            self.serial_port = ShdlcSerialPort(port=port, baudrate=115200)
            self.connection = ShdlcConnection(self.serial_port)
            self.devices = {}

            unit = Sfc5xxxMediumUnit(
                Sfc5xxxUnitPrefix.MILLI,
                Sfc5xxxUnit.STANDARD_LITER,
                Sfc5xxxUnitTimeBase.MINUTE,
            )

            for address in addresses:
                device = Sfc5xxxShdlcDevice(
                    self.connection,
                    slave_address=int(address)
                )

                product_name = device.get_product_name()
                serial_number = device.get_serial_number()

                device.set_user_defined_medium_unit(unit)
                device.set_setpoint_persist(False)

                self.devices[int(address)] = device

                print(
                    f"Connected MFC address {address}: "
                    f"{product_name}, SN {serial_number}"
                )

            self.port_name = port
            self.connected = True
            return True

        except Exception:
            self.connected = False
            self.devices = {}

            if self.serial_port is not None:
                try:
                    self.serial_port.close()
                except Exception:
                    pass

            self.serial_port = None
            self.connection = None
            raise

    def disconnect(self):
        self.stop_all()

        if self.serial_port is not None:
            try:
                self.serial_port.close()
            except Exception:
                pass

        self.connected = False
        self.devices = {}
        self.serial_port = None
        self.connection = None
        print("MFC controller disconnected.")

    def set_flow(self, address, flow_lpm):
        if not self.connected:
            raise RuntimeError("MFC controller is not connected.")

        if flow_lpm < 0:
            raise ValueError("Flow cannot be negative.")

        address = int(address)
        self.flows[address] = flow_lpm

        if self.mock_mode:
            print(f"[MOCK] Address {address}: set flow to {flow_lpm:.3f} L/min")
            return

        if address not in self.devices:
            raise RuntimeError(f"No connected MFC at address {address}.")

        # App uses L/min. Sensirion user-defined unit here is sccm.
        flow_sccm = flow_lpm * 1000.0

        self.devices[address].set_setpoint(
            flow_sccm,
            self.Sfc5xxxScaling.USER_DEFINED
        )

    def read_flow(self, address):
        if not self.connected:
            raise RuntimeError("MFC controller is not connected.")

        address = int(address)

        if self.mock_mode:
            return self.flows.get(address, 0.0)

        if address not in self.devices:
            raise RuntimeError(f"No connected MFC at address {address}.")

        flow_sccm = self.devices[address].read_measured_value(
            self.Sfc5xxxScaling.USER_DEFINED
        )

        return flow_sccm / 1000.0

    def stop_all(self):
        if not self.connected:
            return

        if self.mock_mode:
            for address in list(self.flows.keys()):
                self.flows[address] = 0.0

            print("[MOCK] All MFC flows set to 0.")
            return

        for address, device in self.devices.items():
            try:
                device.set_setpoint(
                    0.0,
                    self.Sfc5xxxScaling.USER_DEFINED
                )
                self.flows[address] = 0.0
            except Exception as e:
                print(f"Failed to stop MFC address {address}: {e}")