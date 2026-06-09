import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load Excel file
df = pd.read_excel("ZAB diff currents.xlsx")

# Sort if needed
df = df.sort_values(by="TIMESTAMP")

# Extract data
x = df["O2"]

y1 = df["1 Hole"]
y2 = df["2 Holes"]
y3 = df["3 Holes"]

# --- Plot scatter + lines ---
plt.figure()

plt.scatter(x, y1, label="1 Hole", marker='^')
plt.scatter(x, y2, label="2 Holes", marker='v')
plt.scatter(x, y3, label="3 Holes", marker='>' )
#plt.plot(x, x, linestyle='--', color='red', label="Ideal (y = x)")

# plt.plot(x, y1)
# plt.plot(x, y2)
# plt.plot(x, y3)

# --- Trendlines (linear fit) ---
# 1 Hole
coeff1 = np.polyfit(x, y1, 1)
trend1 = np.polyval(coeff1, x)
plt.plot(x, trend1, linestyle='--', color='blue', label="_nolegend_")

# 2 Holes
coeff2 = np.polyfit(x, y2, 1)
trend2 = np.polyval(coeff2, x)
plt.plot(x, trend2, linestyle='--', color='orange', label="_nolegend_")

# 3 Holes
coeff3 = np.polyfit(x, y3, 1)
trend3 = np.polyval(coeff3, x)
plt.plot(x, trend3, linestyle='--', color='green', label="_nolegend_")

# Labels
plt.xlabel("O2 (%)")
plt.ylabel("ZAB Current (mA)")
plt.title("ZAB Current vs O2")

plt.legend()
plt.grid(True)

plt.show()