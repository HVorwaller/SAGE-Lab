from gas_math import parse_max_flow


def update_manual_max_flow_labels(window):
    if not hasattr(window, "manual_rows"):
        return

    for index, manual_row in enumerate(window.manual_rows):
        max_flow_label = manual_row[1]
        mfc = window.mfc_config_widgets[index]
        selected_max_flow = mfc["max_flow_rate"].currentText()
        max_flow_label.setText(selected_max_flow)


def update_visible_mfcs(window):
    selected_count = window.mfc_selector.currentIndex() + 1

    for index, row_widgets in enumerate(window.mfc_rows):
        should_show = index < selected_count
        for widget in row_widgets:
            widget.setVisible(should_show)

    if hasattr(window, "manual_rows"):
        for index, row_widgets in enumerate(window.manual_rows):
            should_show = index < selected_count
            for widget in row_widgets:
                widget.setVisible(should_show)

    if hasattr(window, "filler_selector"):
        window.filler_selector.clear()
        for i in range(1, selected_count + 1):
            window.filler_selector.addItem(f"MFC {i}")
        window.update_filler_display()


def update_filler_display(window):
    if not hasattr(window, "manual_rows"):
        return

    filler_index = window.filler_selector.currentIndex()
    filler_message = "this gas will fill the remaining percentage"

    for index, row_widgets in enumerate(window.manual_rows):
        percent_widget = row_widgets[2]

        if index == filler_index:
            percent_widget.setText(filler_message)
            percent_widget.setReadOnly(True)
        else:
            # Only clear the old filler message. Do not wipe real user-entered values
            # when the filler MFC selection changes.
            if percent_widget.text() == filler_message:
                percent_widget.clear()

            percent_widget.setReadOnly(False)


def validate_mfc_setup(window):
    selected_count = window.mfc_selector.currentIndex() + 1
    used_addresses = set()
    used_gases = set()

    for i in range(selected_count):
        mfc = window.mfc_config_widgets[i]

        gas = mfc["gas"].currentText()
        max_flow = mfc["max_flow_rate"].currentText()
        address = mfc["address"].currentText()

        if gas == "None":
            window.instruction_label.setText(f"MFC {i + 1} needs a gas selected.")
            window.log_text.append(f"Cannot start: MFC {i + 1} needs a gas selected.")
            return False

        if gas in used_gases:
            window.instruction_label.setText(f"Duplicate gas selected: {gas}")
            window.log_text.append(
                f"Cannot start: duplicate gas selected ({gas}). "
                "Use only one MFC per gas for now."
            )
            return False

        used_gases.add(gas)

        if max_flow == "None":
            window.instruction_label.setText(f"MFC {i + 1} needs a max flow selected.")
            window.log_text.append(f"Cannot start: MFC {i + 1} needs a max flow selected.")
            return False

        if address == "N/A":
            window.instruction_label.setText(f"MFC {i + 1} needs an address selected.")
            window.log_text.append(f"Cannot start: MFC {i + 1} needs an address selected.")
            return False

        if address in used_addresses:
            window.instruction_label.setText(f"Duplicate address detected: {address}")
            window.log_text.append(f"Cannot start: duplicate MFC address detected ({address}).")
            return False

        used_addresses.add(address)

    return True


def build_mfc_config(window):
    selected_count = window.mfc_selector.currentIndex() + 1
    mfc_config = []

    for i in range(selected_count):
        mfc = window.mfc_config_widgets[i]

        gas = mfc["gas"].currentText()
        max_flow = mfc["max_flow_rate"].currentText()

        mfc_config.append({
            "mfc": i + 1,
            "gas": gas,
            "max_flow_lpm": parse_max_flow(max_flow)
        })

    return mfc_config


def build_manual_targets(window):
    selected_count = window.mfc_selector.currentIndex() + 1
    filler_index = window.filler_selector.currentIndex()

    targets = {}

    for i in range(selected_count):
        mfc = window.mfc_config_widgets[i]
        gas = mfc["gas"].currentText()

        if i == filler_index:
            targets[gas] = "balance"
            continue

        percent_input = window.manual_rows[i][2]
        value_text = percent_input.text().strip()

        if value_text == "":
            raise ValueError(f"MFC {i + 1} needs a manual target value.")

        targets[gas] = float(value_text)

    return targets


def reset_mfc_flow_labels(window):
    for mfc in window.mfc_config_widgets:
        mfc["current_flow"].setText("0.000 L/min")
