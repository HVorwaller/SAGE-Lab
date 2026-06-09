import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from openpyxl import load_workbook
from openpyxl.drawing.image import Image as XLImage

# =============================
# USER SETTINGS
# =============================

# Set this to True if you want to include Apogee .dat data.
# Set this to False if you only want to use the Excel/CSV file.
UseApogee = False

Datfile = "73025_3Jars_3seconds.dat"
CSVfile = "2PLYH.CSV"

RoomO2ApogeeVoltage = 11.03
TimeOffset = -0   # offsets the ZAB data. negative moves left, positive moves right

StartTime = "2026-05-26 11:55:00"
StopTime = "2026-05-26 15:30:00"

output_image = "plots.png"
output_excel = "plots_and_data.xlsx"

# Choose which ZAB channels to plot.
# Options are: "CH1", "CH2", "CH3"
PlotZABs = ["CH1", "CH2"]

# =============================
# COLUMN NAMES
# =============================

Ch1 = "CH1 (mA)"
Ch2 = "CH2 (mA)"
Ch3 = "CH3 (mA)"
Avoltage = "DiffVolt(1)"
TimeStamp = "Timestamp"
o2_1 = "O2_CH1 (%)"
o2_2 = "O2_CH2 (%)"
o2_3 = "O2_CH3 (%)"

ZAB_Temp = "ZAB SHT Temp (C)"
ZAB_Humidity = "ZAB SHT Humidity (%RH)"
ENV_Temp = "Environment SHT Temp (C)"
ENV_Humidity = "Environment SHT Humidity (%RH)"

zab_info = {
    "CH1": {"current_col": Ch1, "o2_col": o2_1, "label": "ZAB CH1", "color": "purple", "linestyle": "--"},
    "CH2": {"current_col": Ch2, "o2_col": o2_2, "label": "ZAB CH2", "color": "teal", "linestyle": ":"},
    "CH3": {"current_col": Ch3, "o2_col": o2_3, "label": "ZAB CH3", "color": "blue", "linestyle": "-."},
}

selected_zabs = [zab for zab in PlotZABs if zab in zab_info]
if not selected_zabs:
    raise ValueError("PlotZABs must include at least one of these options: 'CH1', 'CH2', 'CH3'")

# =============================
# READ CSV / EXCEL DATA
# =============================

# This reads a CSV file. If your file is .xlsx, use pd.read_excel(CSVfile) instead.
dataframeCSV = pd.read_csv(CSVfile, skipinitialspace=True)
dataframeCSV.columns = dataframeCSV.columns.str.strip()

needed_csv_cols = ["Date", "Clock", ZAB_Temp, ZAB_Humidity, ENV_Temp, ENV_Humidity]
for zab in selected_zabs:
    needed_csv_cols.append(zab_info[zab]["current_col"])
    needed_csv_cols.append(zab_info[zab]["o2_col"])

missing_cols = [col for col in needed_csv_cols if col not in dataframeCSV.columns]
if missing_cols:
    raise KeyError(f"These columns are missing from the CSV/Excel file: {missing_cols}")

# Main ZAB current dataframe
dfcsv = dataframeCSV[["Date", "Clock"] + [zab_info[zab]["current_col"] for zab in selected_zabs]].copy()
dfcsv[TimeStamp] = pd.to_datetime(dfcsv["Date"].astype(str) + " " + dfcsv["Clock"].astype(str), errors="coerce")
dfcsv[TimeStamp] = dfcsv[TimeStamp] + pd.Timedelta(seconds=TimeOffset)

for zab in selected_zabs:
    col = zab_info[zab]["current_col"]
    dfcsv[col] = pd.to_numeric(dfcsv[col], errors="coerce")

dfcsv = dfcsv[(dfcsv[TimeStamp] >= StartTime) & (dfcsv[TimeStamp] <= StopTime)]

# ZAB-calculated O2 dataframe
dfcsvO2 = dataframeCSV[["Date", "Clock"] + [zab_info[zab]["o2_col"] for zab in selected_zabs]].copy()
dfcsvO2[TimeStamp] = pd.to_datetime(dfcsvO2["Date"].astype(str) + " " + dfcsvO2["Clock"].astype(str), errors="coerce")
dfcsvO2[TimeStamp] = dfcsvO2[TimeStamp] + pd.Timedelta(seconds=TimeOffset)

for zab in selected_zabs:
    col = zab_info[zab]["o2_col"]
    dfcsvO2[col] = pd.to_numeric(dfcsvO2[col], errors="coerce")

dfcsvO2 = dfcsvO2[(dfcsvO2[TimeStamp] >= StartTime) & (dfcsvO2[TimeStamp] <= StopTime)]

# SHT dataframe
dfcsvTemp = dataframeCSV[["Date", "Clock", ZAB_Temp, ZAB_Humidity, ENV_Temp, ENV_Humidity]].copy()
dfcsvTemp[TimeStamp] = pd.to_datetime(dfcsvTemp["Date"].astype(str) + " " + dfcsvTemp["Clock"].astype(str), errors="coerce")
dfcsvTemp[TimeStamp] = dfcsvTemp[TimeStamp] + pd.Timedelta(seconds=TimeOffset)

for col in [ZAB_Temp, ZAB_Humidity, ENV_Temp, ENV_Humidity]:
    dfcsvTemp[col] = pd.to_numeric(dfcsvTemp[col], errors="coerce")

dfcsvTemp[ZAB_Humidity] = dfcsvTemp[ZAB_Humidity].replace(0, np.nan)
dfcsvTemp[ENV_Humidity] = dfcsvTemp[ENV_Humidity].replace(0, np.nan)
dfcsvTemp = dfcsvTemp[(dfcsvTemp[TimeStamp] >= StartTime) & (dfcsvTemp[TimeStamp] <= StopTime)]

# =============================
# OPTIONAL APOGEE DATA
# =============================

dfdat = None
fit_data = {}

if UseApogee:
    dataframedat = pd.read_csv(Datfile, delimiter=',', skiprows=[0, 2, 3], low_memory=False)
    dataframedat.columns = dataframedat.columns.str.strip()

    dfdat = dataframedat[["TIMESTAMP", Avoltage]].copy()
    dfdat[TimeStamp] = pd.to_datetime(dfdat["TIMESTAMP"], format="%Y-%m-%d %H:%M:%S", errors="coerce")
    dfdat[Avoltage] = pd.to_numeric(dfdat[Avoltage], errors="coerce") * 20.95 / RoomO2ApogeeVoltage
    dfdat = dfdat[(dfdat[TimeStamp] >= StartTime) & (dfdat[TimeStamp] <= StopTime)]

    dfdat_sorted = dfdat[[TimeStamp, Avoltage]].sort_values(TimeStamp)

    for zab in selected_zabs:
        current_col = zab_info[zab]["current_col"]
        dfcsv_sorted = dfcsv[[TimeStamp, current_col]].sort_values(TimeStamp)

        merged = pd.merge_asof(
            dfdat_sorted,
            dfcsv_sorted,
            on=TimeStamp,
            direction="nearest",
            tolerance=pd.Timedelta(seconds=5)
        )
        merged = merged.dropna(subset=[current_col, Avoltage])

        if len(merged) >= 2:
            x = merged[current_col]
            y = merged[Avoltage]
            m, b = np.polyfit(x, y, 1)
            x_line = np.linspace(x.min(), x.max(), 100)
            y_line = m * x_line + b

            fit_data[zab] = {
                "x": x,
                "y": y,
                "m": m,
                "b": b,
                "x_line": x_line,
                "y_line": y_line,
            }

# =============================
# PLOTS
# =============================

fig, axs = plt.subplots(2, 2, figsize=(14, 9))

# Figure 1: ZAB current vs time, with optional Apogee on a second axis
for zab in selected_zabs:
    info = zab_info[zab]
    axs[0, 0].plot(
        dfcsv[TimeStamp],
        dfcsv[info["current_col"]],
        linestyle=info["linestyle"],
        color=info["color"],
        label=f'{info["label"]} Current'
    )

axs[0, 0].set_xlabel("Clock")
axs[0, 0].set_ylabel("ZAB Current (mA)")
axs[0, 0].set_title("ZAB Current vs. Time")
axs[0, 0].grid()

if UseApogee and dfdat is not None:
    ax_apogee = axs[0, 0].twinx()
    ax_apogee.plot(dfdat[TimeStamp], dfdat[Avoltage], linestyle='-', color='black', label="Apogee O2")
    ax_apogee.set_ylabel("Apogee O2 Concentration (%)")

    lines1, labels1 = axs[0, 0].get_legend_handles_labels()
    lines2, labels2 = ax_apogee.get_legend_handles_labels()
    axs[0, 0].legend(lines1 + lines2, labels1 + labels2, loc="best")
else:
    axs[0, 0].legend()

# Figure 2: Apogee scatter if Apogee is enabled, otherwise leave a note
if UseApogee and fit_data:
    for zab in selected_zabs:
        if zab not in fit_data:
            continue
        info = zab_info[zab]
        fd = fit_data[zab]
        axs[0, 1].scatter(
            fd["x"], fd["y"],
            color=info["color"], alpha=0.2, s=10,
            label=f'{info["label"]} (m={fd["m"]:.3f})'
        )
        axs[0, 1].plot(fd["x_line"], fd["y_line"], color=info["color"], linestyle=info["linestyle"])

    axs[0, 1].set_xlabel("ZAB Current (mA)")
    axs[0, 1].set_ylabel("Apogee O2 Concentration (%)")
    axs[0, 1].set_title("Apogee O2 vs. ZAB Current")
    axs[0, 1].legend()
    axs[0, 1].grid()
else:
    axs[0, 1].axis("off")
    axs[0, 1].text(
        0.5, 0.5,
        "Apogee comparison disabled\nSet UseApogee = True to enable this plot",
        ha="center", va="center", fontsize=12
    )

# Figure 3: ZAB calculated O2 vs time, with optional Apogee
for zab in selected_zabs:
    info = zab_info[zab]
    axs[1, 0].plot(
        dfcsvO2[TimeStamp],
        dfcsvO2[info["o2_col"]],
        label=info["o2_col"],
        color=info["color"],
        linestyle=info["linestyle"]
    )

if UseApogee and dfdat is not None:
    axs[1, 0].plot(dfdat[TimeStamp], dfdat[Avoltage], label="Apogee O2", color='black', linestyle='-')

axs[1, 0].set_xlabel("Clock")
axs[1, 0].set_ylabel("O2 Concentration (%)")
axs[1, 0].set_title("ZAB O2 vs. Time" if not UseApogee else "ZAB and Apogee O2 vs. Time")
axs[1, 0].legend()
axs[1, 0].grid()

# Figure 4: both SHT sensors
axs[1, 1].plot(dfcsvTemp[TimeStamp], dfcsvTemp[ZAB_Temp], color='red', linestyle='-', label="ZAB SHT Temp (°C)")
axs[1, 1].plot(dfcsvTemp[TimeStamp], dfcsvTemp[ENV_Temp], color='orange', linestyle='--', label="Environment SHT Temp (°C)")
axs[1, 1].set_xlabel("Clock")
axs[1, 1].set_ylabel("Temperature (°C)", color='red')
axs[1, 1].tick_params(axis='y', labelcolor='red')

ax2 = axs[1, 1].twinx()
ax2.plot(dfcsvTemp[TimeStamp], dfcsvTemp[ZAB_Humidity], color='blue', linestyle='-', label="ZAB SHT Humidity (%RH)")
ax2.plot(dfcsvTemp[TimeStamp], dfcsvTemp[ENV_Humidity], color='cyan', linestyle='--', label="Environment SHT Humidity (%RH)")
ax2.set_ylabel("Humidity (%RH)", color='blue')
ax2.tick_params(axis='y', labelcolor='blue')

axs[1, 1].set_title("Both SHT Sensors: Temperature and Humidity vs. Time")
lines1, labels1 = axs[1, 1].get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
axs[1, 1].legend(lines1 + lines2, labels1 + labels2, loc='center right')
axs[1, 1].grid()

plt.tight_layout()
fig.savefig(output_image, dpi=300, bbox_inches="tight")
plt.show()

# =============================
# EXPORT DATA TO EXCEL
# =============================

# Figure 1 data
fig1_parts = [
    dfcsv[[TimeStamp] + [zab_info[zab]["current_col"] for zab in selected_zabs]].reset_index(drop=True)
]
fig1_df = pd.concat(fig1_parts, axis=1)
fig1_df = fig1_df.rename(columns={TimeStamp: "ZAB_Time"})

if UseApogee and dfdat is not None:
    apogee_df = dfdat[[TimeStamp, Avoltage]].reset_index(drop=True).rename(columns={
        TimeStamp: "Apogee_Time",
        Avoltage: "Apogee_O2"
    })
    fig1_df = pd.concat([apogee_df, fig1_df], axis=1)

# Figure 2 data
fig2_parts = []
if UseApogee and fit_data:
    for zab in selected_zabs:
        if zab not in fit_data:
            continue
        fd = fit_data[zab]
        fig2_parts.extend([
            fd["x"].reset_index(drop=True).rename(f"{zab}_x"),
            fd["y"].reset_index(drop=True).rename(f"{zab}_y"),
            pd.Series(fd["x_line"], name=f"{zab}_fit_x"),
            pd.Series(fd["y_line"], name=f"{zab}_fit_y"),
        ])

fig2_df = pd.concat(fig2_parts, axis=1) if fig2_parts else pd.DataFrame({"Message": ["Apogee disabled; no scatter fit data generated."]})

# Figure 3 data
fig3_df = dfcsvO2[[TimeStamp] + [zab_info[zab]["o2_col"] for zab in selected_zabs]].copy()
fig3_df = fig3_df.rename(columns={TimeStamp: "Clock"})

if UseApogee and dfdat is not None:
    apogee_o2_df = dfdat[[TimeStamp, Avoltage]].reset_index(drop=True).rename(columns={
        TimeStamp: "Apogee_Time",
        Avoltage: "Apogee_O2"
    })
    fig3_df = pd.concat([fig3_df.reset_index(drop=True), apogee_o2_df], axis=1)

# Figure 4 data
fig4_df = dfcsvTemp[[TimeStamp, ZAB_Temp, ZAB_Humidity, ENV_Temp, ENV_Humidity]].copy()
fig4_df.columns = [
    "Clock",
    "ZAB_SHT_Temp_C",
    "ZAB_SHT_Humidity_RH",
    "Environment_SHT_Temp_C",
    "Environment_SHT_Humidity_RH"
]

with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
    fig1_df.to_excel(writer, sheet_name="Figure1_Data", index=False)
    fig2_df.to_excel(writer, sheet_name="Figure2_Data", index=False)
    fig3_df.to_excel(writer, sheet_name="Figure3_Data", index=False)
    fig4_df.to_excel(writer, sheet_name="Figure4_Data", index=False)

    pd.DataFrame({"Plot Image": ["See embedded image below"]}).to_excel(
        writer, sheet_name="Figure_Image", index=False
    )

wb = load_workbook(output_excel)
ws = wb["Figure_Image"]
img = XLImage(output_image)
ws.add_image(img, "A3")
wb.save(output_excel)

print(f"Saved image: {output_image}")
print(f"Saved Excel file: {output_excel}")
print(f"UseApogee = {UseApogee}")
print(f"Plotted ZAB channels: {selected_zabs}")
