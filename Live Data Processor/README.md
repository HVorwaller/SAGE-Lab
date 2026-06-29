# ZAB Sensor Dashboard

This is the sensor/readout counterpart to the MFC control project.

## Current features

- PySide6 GUI
- Mock mode for development without hardware
- Waveshare ADC hardware hook
- SHT sensor hardware hook
- Live readouts for:
  - 3 ZAB voltage/current channels
  - 3 calculated ZAB O2 values
  - Apogee voltage and calculated O2
  - 2 SHT temperature/humidity sensors
- Live graph with selectable X-axis:
  - Time
  - Apogee calculated O2
- Graph checkboxes for:
  - ZAB currents
  - Calculated ZAB O2
  - Apogee O2
  - SHT temperature
  - SHT humidity
- Continuous CSV logging
- Editable ZAB load resistor
- Editable Apogee calibration voltage
- 5-minute ZAB average calibration button

## ZAB current formula

```python
current_mA = (5000 - voltage_mV) / load_resistor_ohms
```

## Apogee O2 formula

```python
apogee_o2_percent = 20.95 / apogee_calibration_voltage * current_apogee_voltage
```

## ZAB calculated O2 formula

```python
zab_o2_percent = (-0.8966 + sqrt(
    0.80389156 + 0.0232 * (0.1873 + ((20.95 / zab_avg_mA) * zab_current_mA))
)) / 0.011595
```

## ZAB average calibration

Click:

```text
Collect ZAB Avg
```

The GUI starts a 5-minute timer and collects the current from each ZAB channel. At the end, it stores:

```text
ZAB 1 avg
ZAB 2 avg
ZAB 3 avg
```

Those averages are then used in the calculated ZAB O2 equation.

## Running the app

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run:

```bash
python Main.py
```

## Expected ADC channel map

```text
ADC CH0 -> ZAB 1 voltage
ADC CH1 -> ZAB 2 voltage
ADC CH2 -> ZAB 3 voltage
ADC CH3 -> Apogee voltage
```
