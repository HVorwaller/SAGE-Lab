
def clamp(value, low, high):
    return max(low, min(high, value))


def calculate_open_loop_humidity_flows(target_rh, humidifier_rh, total_flow_lpm):
    """Calculate wet/dry flows from an assumed humidifier output RH."""
    target_rh = float(target_rh)
    humidifier_rh = float(humidifier_rh)
    total_flow_lpm = float(total_flow_lpm)

    if target_rh < 0 or target_rh > 100:
        raise ValueError("Target RH must be between 0 and 100%.")

    if humidifier_rh <= 0 or humidifier_rh > 100:
        raise ValueError("Humidifier output RH must be greater than 0 and no more than 100%.")

    if total_flow_lpm < 0:
        raise ValueError("Total humidity flow cannot be negative.")

    if target_rh > humidifier_rh:
        raise ValueError("Target RH cannot exceed humidifier output RH.")

    wet_fraction = target_rh / humidifier_rh
    dry_fraction = 1.0 - wet_fraction

    return {
        "wet_flow_lpm": total_flow_lpm * wet_fraction,
        "dry_flow_lpm": total_flow_lpm * dry_fraction,
        "wet_fraction": wet_fraction,
        "dry_fraction": dry_fraction,
    }


def calculate_feedback_humidity_flows(
    target_rh,
    measured_rh,
    total_flow_lpm,
    current_wet_fraction,
    kp,
):
    """Simple proportional RH feedback.

    Positive error means RH is too low, so wet fraction increases.
    Negative error means RH is too high, so wet fraction decreases.
    """
    target_rh = float(target_rh)
    measured_rh = float(measured_rh)
    total_flow_lpm = float(total_flow_lpm)
    current_wet_fraction = float(current_wet_fraction)
    kp = float(kp)

    if target_rh < 0 or target_rh > 100:
        raise ValueError("Target RH must be between 0 and 100%.")

    if measured_rh < 0 or measured_rh > 100:
        raise ValueError("Measured RH must be between 0 and 100%.")

    if total_flow_lpm < 0:
        raise ValueError("Total humidity flow cannot be negative.")

    if kp < 0:
        raise ValueError("Kp cannot be negative.")

    error = target_rh - measured_rh
    wet_fraction = clamp(current_wet_fraction + (kp * error), 0.0, 1.0)
    dry_fraction = 1.0 - wet_fraction

    return {
        "wet_flow_lpm": total_flow_lpm * wet_fraction,
        "dry_flow_lpm": total_flow_lpm * dry_fraction,
        "wet_fraction": wet_fraction,
        "dry_fraction": dry_fraction,
        "error": error,
    }
