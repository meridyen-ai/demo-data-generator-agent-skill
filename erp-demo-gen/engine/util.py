"""Deterministic helpers: seeded RNG, date math, money rounding.

Everything that introduces randomness must go through an Rng instance seeded
from the run's master seed so a given (spec, seeds, seed) regenerates an
identical database.
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta


class Rng:
    """Thin deterministic wrapper around random.Random with domain helpers.

    Use sub-streams (``rng.stream("sales")``) so adding rows in one domain does
    not shift the random sequence consumed by another domain.
    """

    def __init__(self, seed: int):
        self.seed = int(seed)
        self._r = random.Random(self.seed)

    def stream(self, name: str) -> "Rng":
        # Derive a stable child seed from the name so streams are independent
        # yet fully reproducible.
        h = 1469598103934665603
        for ch in name:
            h ^= ord(ch)
            h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
        return Rng((self.seed ^ h) & 0x7FFFFFFF)

    # --- primitives ---
    def rand(self) -> float:
        return self._r.random()

    def randint(self, lo: int, hi: int) -> int:
        return self._r.randint(lo, hi)

    def choice(self, seq):
        return self._r.choice(seq)

    def sample(self, seq, k):
        k = max(0, min(k, len(seq)))
        return self._r.sample(list(seq), k)

    def shuffle(self, seq):
        self._r.shuffle(seq)
        return seq

    def weighted(self, items, weights):
        return self._r.choices(items, weights=weights, k=1)[0]

    def chance(self, p: float) -> bool:
        return self._r.random() < p

    # --- distributions ---
    def lognormal(self, mean: float, sigma: float = 0.5) -> float:
        """Lognormal value whose *median* is ``mean`` (mu = ln mean)."""
        mu = math.log(max(mean, 1e-9))
        return math.exp(self._r.gauss(mu, sigma))

    def lognormal_mean(self, mean: float, sigma: float = 0.5) -> float:
        """Lognormal value whose *expected value* is ``mean`` (corrects the
        exp(sigma^2/2) bias). Use for order/PO values that must average to a
        target so annual totals land on the requested revenue."""
        mu = math.log(max(mean, 1e-9)) - 0.5 * sigma * sigma
        return math.exp(self._r.gauss(mu, sigma))

    def poisson(self, lam: float) -> int:
        """Knuth's algorithm; fine for the lambdas we use."""
        if lam <= 0:
            return 0
        if lam > 500:  # normal approximation for large lambda (cheap + stable)
            return max(0, int(round(self._r.gauss(lam, math.sqrt(lam)))))
        L = math.exp(-lam)
        k = 0
        p = 1.0
        while True:
            k += 1
            p *= self._r.random()
            if p <= L:
                return k - 1

    def jitter(self, value: float, pct: float = 0.15) -> float:
        return value * (1.0 + self._r.uniform(-pct, pct))


# --- date helpers (stdlib only) ---
def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    last_day = days_in_month(y, m)
    return date(y, m, min(d.day, last_day))


def days_in_month(y: int, m: int) -> int:
    if m == 12:
        nxt = date(y + 1, 1, 1)
    else:
        nxt = date(y, m + 1, 1)
    return (nxt - date(y, m, 1)).days


def random_date_in_month(rng: Rng, y: int, m: int) -> date:
    return date(y, m, rng.randint(1, days_in_month(y, m)))


def add_days(d: date, days: int) -> date:
    return d + timedelta(days=days)


def money(x: float) -> float:
    """Round to cents, avoiding float noise in totals."""
    return float(int(round(x * 100))) / 100.0
