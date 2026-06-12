class SHTController:
    """Small wrapper for an SHT humidity sensor.

    Mock mode is safe for development. Real mode first tries Adafruit's
    SHT31D library, which is common on Raspberry Pi. If your exact SHT model
    uses another library, only this file should need to change.
    """

    def __init__(self, mock_mode=True):
        self.mock_mode = mock_mode
        self.connected = False
        self.mock_rh = 50.0
        self.mock_temp_c = 22.0
        self.sensor = None

    def connect(self, i2c_address="0x44"):
        if self.mock_mode:
            self.connected = True
            return True

        try:
            import board

            address = int(str(i2c_address), 16) if str(i2c_address).startswith("0x") else int(i2c_address)
            i2c = board.I2C()

            try:
                import adafruit_sht31d
                self.sensor = adafruit_sht31d.SHT31D(i2c, address=address)
            except Exception:
                import adafruit_sht4x
                self.sensor = adafruit_sht4x.SHT4x(i2c, address=address)

            self.connected = True
            return True

        except Exception:
            self.connected = False
            self.sensor = None
            raise

    def disconnect(self):
        self.connected = False
        self.sensor = None

    def read(self):
        if not self.connected:
            raise RuntimeError("SHT sensor is not connected.")

        if self.mock_mode:
            return {
                "rh": self.mock_rh,
                "temperature_c": self.mock_temp_c,
            }

        return {
            "rh": float(self.sensor.relative_humidity),
            "temperature_c": float(self.sensor.temperature),
        }
