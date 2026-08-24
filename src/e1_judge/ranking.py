"""E1 ranking utilities: tie-aware Bradley-Terry utilities and correlations."""

import math
from typing import Dict, List


def fit_utilities(pairwise_preferences: List[Dict[str, str]]) -> Dict[str, float]:
    """Fit tie-aware Bradley-Terry utilities from per-sample pairwise preferences.

    Each entry maps candidate_id -> 'a'/'b'/'tie'/'uncertain'. Only decisive
    'a'/'b' preferences contribute; ties are ignored (treated as zero update).
    """
    utilities: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    wins: Dict[str, int] = {}

    for pref in pairwise_preferences:
        a = pref["a"]
        b = pref["b"]
        choice = pref["choice"]
        utilities.setdefault(a, 0.0)
        utilities.setdefault(b, 0.0)
        counts.setdefault(a, 0)
        counts.setdefault(b, 0)
        wins.setdefault(a, 0)
        wins.setdefault(b, 0)
        if choice == "a":
            counts[a] += 1
            counts[b] += 1
            wins[a] += 1
        elif choice == "b":
            counts[a] += 1
            counts[b] += 1
            wins[b] += 1

    for candidate in utilities:
        if counts[candidate] > 0:
            utilities[candidate] = wins[candidate] / counts[candidate]
    return utilities


def _ranked(utilities: Dict[str, float]) -> List[str]:
    return sorted(utilities, key=lambda c: (utilities[c], c), reverse=True)


def kendall_tau(utilities_a: Dict[str, float], utilities_b: Dict[str, float]) -> float:
    """Kendall tau on the shared candidate ranking induced by utilities."""
    shared = [c for c in _ranked(utilities_a) if c in utilities_b]
    if len(shared) < 2:
        return 0.0
    rank_a = {c: i for i, c in enumerate(_ranked({c: utilities_a[c] for c in shared}))}
    rank_b = {c: i for i, c in enumerate(_ranked({c: utilities_b[c] for c in shared}))}
    pairs = 0
    concordant = 0
    for i in range(len(shared)):
        for j in range(i + 1, len(shared)):
            ci, cj = shared[i], shared[j]
            a_order = rank_a[ci] < rank_a[cj]
            b_order = rank_b[ci] < rank_b[cj]
            pairs += 1
            if a_order == b_order:
                concordant += 1
    if pairs == 0:
        return 0.0
    return (2 * concordant - pairs) / pairs


def spearman(utilities_a: Dict[str, float], utilities_b: Dict[str, float]) -> float:
    shared = sorted(set(utilities_a) & set(utilities_b))
    if len(shared) < 2:
        return 0.0
    rank_a = {c: i for i, c in enumerate(_ranked({c: utilities_a[c] for c in shared}))}
    rank_b = {c: i for i, c in enumerate(_ranked({c: utilities_b[c] for c in shared}))}
    n = len(shared)
    d2 = sum((rank_a[c] - rank_b[c]) ** 2 for c in shared)
    return 1.0 - (6.0 * d2) / (n * (n * n - 1))
