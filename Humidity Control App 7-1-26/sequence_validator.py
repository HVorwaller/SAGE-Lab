from gas_math import calculate_mfc_flows


def gas_column_to_mfc_gas(gas_column):
    gas_name = gas_column.replace("_%", "").replace("_ppm", "")

    if gas_name == "CH4":
        return "CH4/N2 Mix"

    return gas_name


def build_targets_from_step(step):
    targets = {}

    for gas_column, value in step["gases"].items():
        gas_name = gas_column_to_mfc_gas(gas_column)

        if gas_name == "N2":
            targets["N2"] = "balance"
        else:
            targets[gas_name] = value

    targets["N2"] = "balance"

    return targets


def validate_sequence_preflight(sequence_steps, mfc_config):
    if not sequence_steps:
        raise ValueError("No Excel sequence has been loaded.")

    configured_gases = {mfc["gas"] for mfc in mfc_config}

    for step in sequence_steps:
        targets = build_targets_from_step(step)

        for gas in targets:
            if gas == "N2":
                continue

            if gas not in configured_gases:
                raise ValueError(
                    f"Step {step['step']} requires {gas}, but no MFC is assigned to {gas}."
                )

        if "N2" not in configured_gases:
            raise ValueError("Excel sequence requires N2 balance, but no MFC is assigned to N2.")

        calculate_mfc_flows(targets, mfc_config)

    return True