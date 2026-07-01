import pandas as pd


def load_sequence_from_excel(file_path):
    """
    Reads an Excel step sequence and returns data ready for graphing/execution.

    Required columns:
        Step
        Duration_min

    Gas columns:
        Any column ending in _% is treated as percent concentration, except RH_%.
        Any column ending in _ppm is treated as ppm concentration.

    Humidity column:
        RH_% is treated as a humidity target, not a gas concentration.

    N2_% is automatically added as the balance gas if missing.
    """
    df = pd.read_excel(file_path)
    df = df.dropna(how="all")
    df = df.dropna(subset=["Step", "Duration_min"])

    required_columns = ["Step", "Duration_min"]
    for column in required_columns:
        if column not in df.columns:
            raise ValueError(f"Missing required column: {column}")

    has_humidity_column = "RH_%" in df.columns

    percent_columns = [
        col for col in df.columns
        if col.endswith("_%") and col != "RH_%"
    ]
    ppm_columns = [col for col in df.columns if col.endswith("_ppm")]

    if not percent_columns and not ppm_columns:
        raise ValueError("No gas columns found. Use columns like O2_%, CO2_%, or CH4_ppm.")

    added_balance_n2 = False

    if "N2_%" not in df.columns:
        percent_sum = df[percent_columns].sum(axis=1)

        ppm_as_percent = 0
        for col in ppm_columns:
            ppm_as_percent += df[col] / 10000

        df["N2_%"] = 100 - percent_sum - ppm_as_percent
        percent_columns.append("N2_%")
        added_balance_n2 = True

    detected_gas_count = len(percent_columns) + len(ppm_columns)

    if detected_gas_count > 4:
        raise ValueError(f"Detected {detected_gas_count} gas columns, but only 4 are allowed.")

    gas_data = {}
    sequence_steps = []
    current_time = 0

    for col in percent_columns + ppm_columns:
        gas_data[col] = {
            "time": [],
            "value": []
        }

    if has_humidity_column:
        gas_data["RH_%"] = {
            "time": [],
            "value": []
        }

    for _, row in df.iterrows():
        step = int(row["Step"])
        duration_min = float(row["Duration_min"])
        duration = duration_min * 60

        start_time = current_time
        end_time = current_time + duration

        step_info = {
            "step": step,
            "start_time": start_time,
            "end_time": end_time,
            "duration": duration,
            "gases": {},
            "humidity_target_rh": None
        }

        if has_humidity_column:
            step_info["humidity_target_rh"] = (
                float(row["RH_%"]) if not pd.isna(row["RH_%"]) else None
            )

            rh_value = step_info["humidity_target_rh"]
            if rh_value is not None:
                gas_data["RH_%"]["time"].extend([start_time / 60, end_time / 60])
                gas_data["RH_%"]["value"].extend([rh_value, rh_value])

        for col in percent_columns + ppm_columns:
            value = float(row[col]) if not pd.isna(row[col]) else 0.0

            # Graph displays minutes, runtime uses seconds.
            gas_data[col]["time"].extend([start_time / 60, end_time / 60])
            gas_data[col]["value"].extend([value, value])

            step_info["gases"][col] = value

        sequence_steps.append(step_info)
        current_time = end_time

    return {
        "percent_columns": percent_columns,
        "ppm_columns": ppm_columns,
        "detected_gas_count": detected_gas_count,
        "gas_data": gas_data,
        "sequence_steps": sequence_steps,
        "total_duration_seconds": current_time,
        "added_balance_n2": added_balance_n2,
        "has_humidity_column": has_humidity_column,
        "row_count": len(df),
    }
