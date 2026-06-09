import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_excel("3ply Ultrex, 3hole wet, dry, 3hole membrane wet.xlsx")

print("Columns as read:")
for i, col in enumerate(df.columns):
    print(i, repr(col))

# --- Left block ---
x_wet_raw = pd.to_numeric(df.iloc[:, 0], errors="coerce")
y_without_mem_wet_raw = pd.to_numeric(df.iloc[:, 1], errors="coerce")
y_with_mem_wet_raw    = pd.to_numeric(df.iloc[:, 2], errors="coerce")

# --- Right block ---
x_dry_raw = pd.to_numeric(df.iloc[:, 4], errors="coerce")
y_without_mem_dry_raw = pd.to_numeric(df.iloc[:, 5], errors="coerce")

# Valid masks
mask_without_mem_wet = np.isfinite(x_wet_raw) & np.isfinite(y_without_mem_wet_raw)
mask_with_mem_wet    = np.isfinite(x_wet_raw) & np.isfinite(y_with_mem_wet_raw)
mask_without_mem_dry = np.isfinite(x_dry_raw) & np.isfinite(y_without_mem_dry_raw)

# Clean arrays
x_without_mem_wet = x_wet_raw[mask_without_mem_wet].to_numpy()
y_without_mem_wet = y_without_mem_wet_raw[mask_without_mem_wet].to_numpy()

x_with_mem_wet = x_wet_raw[mask_with_mem_wet].to_numpy()
y_with_mem_wet = y_with_mem_wet_raw[mask_with_mem_wet].to_numpy()

x_without_mem_dry = x_dry_raw[mask_without_mem_dry].to_numpy()
y_without_mem_dry = y_without_mem_dry_raw[mask_without_mem_dry].to_numpy()

print("Without membrane wet points:", len(x_without_mem_wet))
print("With membrane wet points:", len(x_with_mem_wet))
print("Without membrane dry points:", len(x_without_mem_dry))

plt.figure(figsize=(10, 6))

# Scatter points
plt.scatter(x_without_mem_wet, y_without_mem_wet, marker='<', s=100, label="Without Membrane Wet Samples")
plt.scatter(x_with_mem_wet, y_with_mem_wet, marker='>', s=100, label="With Membrane Wet Samples")
plt.scatter(x_without_mem_dry, y_without_mem_dry, marker='^', s=100, label="Without Membrane Dry Samples")

# Trendline helper
def add_trendline(x, y, label):
    if len(x) >= 2:
        coef = np.polyfit(x, y, 1)
        trend = np.poly1d(coef)
        x_line = np.linspace(x.min(), x.max(), 200)
        plt.plot(x_line, trend(x_line), linewidth=2, label="_nolegend_")

add_trendline(x_without_mem_wet, y_without_mem_wet, "Without Membrane Wet Trend")
add_trendline(x_with_mem_wet, y_with_mem_wet, "With Membrane Wet Trend")
add_trendline(x_without_mem_dry, y_without_mem_dry, "Without Membrane Dry Trend")

plt.xlabel("Datalogger O2 (%)")
plt.ylabel("ZAB Current (mA)")
plt.title("Wet and Dry Comparison")
plt.legend()
plt.grid(True)
plt.show()