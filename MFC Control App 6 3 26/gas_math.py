def parse_max_flow(max_flow_text):

    if max_flow_text in ["None", "N/A", ""]:
        raise ValueError("Invalid max flow selected.")

    return float(max_flow_text.replace("L/min", "").strip())


def concentration_to_fraction(gas_name, target_value):

    if gas_name == "CH4/N2 Mix":
        # Source gas is 1000 ppm CH4 in N2.
        # If user wants 100 ppm CH4:
        # required fraction = 100 / 1000 = 0.10
        return target_value / 1000

    # Normal pure gas percent.
    return target_value / 100


def calculate_mfc_flows(targets, mfc_config):

    required_fractions = {}

    for mfc in mfc_config:
        gas = mfc["gas"]

        if targets.get(gas) == "balance":
            continue

        if gas not in targets:
            raise ValueError(f"No target concentration provided for {gas}.")

        target_value = float(targets[gas])

        if target_value < 0:
            raise ValueError(f"{gas} target cannot be negative.")

        required_fractions[gas] = concentration_to_fraction(gas, target_value)

    used_fraction = sum(required_fractions.values())

    if used_fraction > 1:
        raise ValueError("Requested gas concentrations exceed 100%.")

    # Assign N2 balance if present.
    balance_gases = [
        gas for gas, value in targets.items()
        if value == "balance"
    ]

    if len(balance_gases) > 1:
        raise ValueError("Only one filler gas can be selected.")

    if balance_gases:
        balance_gas = balance_gases[0]
        required_fractions[balance_gas] = 1 - used_fraction
    elif used_fraction < 1:
        raise ValueError("No filler MFC selected to fill remaining balance gas.")

    # Find max possible total flow.
    total_flow_limits = []

    for mfc in mfc_config:
        gas = mfc["gas"]
        max_flow = float(mfc["max_flow_lpm"])

        if gas not in required_fractions:
            continue

        fraction = required_fractions[gas]

        if fraction == 0:
            continue

        total_flow_limits.append(max_flow / fraction)

    if not total_flow_limits:
        raise ValueError("No usable MFC flow limits found.")

    total_flow_lpm = min(total_flow_limits)

    flows = {}

    for mfc in mfc_config:
        gas = mfc["gas"]

        if gas in required_fractions:
            flow = total_flow_lpm * required_fractions[gas]
        else:
            flow = 0.0

        max_flow = float(mfc["max_flow_lpm"])

        if flow > max_flow + 1e-9:
            raise ValueError(
                f"{gas} requires {flow:.3f} L/min, "
                f"but max is {max_flow:.3f} L/min."
            )

        flows[mfc["mfc"]] = {
            "gas": gas,
            "flow_lpm": flow,
            "max_flow_lpm": max_flow,
            "fraction": required_fractions.get(gas, 0.0),
        }

    return {
        "total_flow_lpm": total_flow_lpm,
        "flows": flows,
        "fractions": required_fractions,
    }