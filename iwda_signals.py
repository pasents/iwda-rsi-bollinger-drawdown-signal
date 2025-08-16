import os
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf

# -----------------------
# Config
# -----------------------
TICKER = "IWDA.AS"
START_DATE = "2015-01-01"
RSI_WINDOW = 14
BB_WINDOW = 20
BB_STD = 2
DRAWDOWN_THRESHOLD = -0.20  # -20%

# Output paths
IMG_DIR = "images"
IMG_PATH = os.path.join(IMG_DIR, "iwda_chart.png")
CSV_PATH = os.path.join(IMG_DIR, "buy_signals_tail10.csv")
os.makedirs(IMG_DIR, exist_ok=True)

# -----------------------
# Download data
# -----------------------
data = yf.download(TICKER, start=START_DATE, progress=False)
if data.empty:
    raise RuntimeError(f"No data returned for {TICKER}. Check ticker/symbol or internet connection.")

price_col = "Adj Close" if "Adj Close" in data.columns else "Close"
data["Price"] = data[price_col]
data = data[["Price"]].dropna()

# -----------------------
# RSI (simple rolling mean version)
# -----------------------
delta = data["Price"].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

avg_gain = gain.rolling(window=RSI_WINDOW, min_periods=RSI_WINDOW).mean()
avg_loss = loss.rolling(window=RSI_WINDOW, min_periods=RSI_WINDOW).mean()

# Avoid division by zero
rs = avg_gain / avg_loss.replace(0, pd.NA)
rsi = 100 - (100 / (1 + rs))
data["RSI"] = rsi

# -----------------------
# Bollinger Bands
# -----------------------
data["SMA_20"] = data["Price"].rolling(window=BB_WINDOW, min_periods=BB_WINDOW).mean()
rolling_std = data["Price"].rolling(window=BB_WINDOW, min_periods=BB_WINDOW).std()
data["BB_Upper"] = data["SMA_20"] + BB_STD * rolling_std
data["BB_Lower"] = data["SMA_20"] - BB_STD * rolling_std

# -----------------------
# Drawdown
# -----------------------
data["Rolling_Max"] = data["Price"].cummax()
data["Drawdown"] = (data["Price"] - data["Rolling_Max"]) / data["Rolling_Max"]

# -----------------------
# Buy signal
# -----------------------
data["Buy_Signal"] = (
    (data["RSI"] < 30) &
    (data["Price"] < data["BB_Lower"]) &
    (data["Drawdown"] < DRAWDOWN_THRESHOLD)
).astype(int)

# -----------------------
# Plot (and SAVE to images/iwda_chart.png)
# -----------------------
plt.figure(figsize=(14, 6))
plt.plot(data.index, data["Price"], label="Price")
plt.plot(data.index, data["BB_Upper"], linestyle="--", alpha=0.5, label="Bollinger Upper")
plt.plot(data.index, data["BB_Lower"], linestyle="--", alpha=0.5, label="Bollinger Lower")

buy_idx = data.index[data["Buy_Signal"] == 1]
plt.scatter(
    buy_idx,
    data.loc[buy_idx, "Price"],
    marker="^",
    s=100,
    color="green",       # Green marker
    edgecolor="black",   # Black outline
    label="Buy Signal",
    zorder=3
)

plt.title("IWDA Price with RSI + Bollinger + Drawdown Buy Signals")
plt.xlabel("Date")
plt.ylabel("Price (€)")
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save instead of only showing
plt.savefig(IMG_PATH, dpi=300, bbox_inches="tight")
plt.close()
print(f"\nSaved chart: {IMG_PATH}")

# -----------------------
# Output last signals
# -----------------------
cols = ["Price", "RSI", "BB_Lower", "Drawdown"]
signals = data.loc[data["Buy_Signal"] == 1, cols].tail(10)

print("\nLast 10 buy signals:")
print(signals.to_string())

# Also export to CSV (under images/ for easy README linking)
signals.to_csv(CSV_PATH)
print(f"\nSaved CSV: {CSV_PATH}")
