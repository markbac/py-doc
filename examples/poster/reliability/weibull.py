"""Weibull fit of SN-100 cell failures by median-rank regression."""
import math

# Field-equivalent age at failure, in hours
hours = [9100, 14800, 19300, 22600, 26100,
         29400, 31800, 35200, 38900]
n = 120  # cells on test; the rest still ran

# Bernard's median ranks, then a straight line
ranks = [(i - 0.3) / (n + 0.4)
         for i in range(1, len(hours) + 1)]
x = [math.log(t) for t in hours]
y = [math.log(-math.log(1 - f)) for f in ranks]
mx, my = sum(x) / len(x), sum(y) / len(y)
sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
beta = sxy / sum((a - mx) ** 2 for a in x)
eta = math.exp(mx - my / beta)
b10 = eta * (-math.log(0.9)) ** (1 / beta)

years = 8766  # hours in a year
print(f"beta {beta:.2f}, eta {eta / years:.1f} y,"
      f" B10 {b10 / years:.1f} y")
