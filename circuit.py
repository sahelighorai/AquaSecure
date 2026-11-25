"""Circuit-level BB84 cross-check (ported from the AquaSecure digital-twin
notebook). Two engines:

1. qiskit_qber(...)      — Qiskit Aer simulator, if qiskit-aer is importable.
2. statevector_qber(...) — pure NumPy statevector fallback implementing the
   identical circuit semantics (prepare → optional Eve intercept-resend →
   Ry(θ) error, sin²(θ/2) = e_opt → measure). Always available.

Both return sifted QBER over matched bases. This is a software-level
cross-check, NOT experimental validation.
"""

from __future__ import annotations
import math
import numpy as np


def _error_angle(e_opt: float) -> float:
    e = max(0.0, min(0.5, e_opt))
    return 2.0 * math.asin(math.sqrt(e))


def statevector_qber(n_circuits: int = 600, e_opt: float = 0.02,
                     p_noise_ratio: float = 0.01, eve_present: bool = False,
                     seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    alice_bits = rng.integers(0, 2, n_circuits)
    alice_bases = rng.integers(0, 2, n_circuits)   # 0 = Z, 1 = X
    bob_bases = rng.integers(0, 2, n_circuits)
    eve_bases = rng.integers(0, 2, n_circuits)

    theta = _error_angle(e_opt)
    ry = np.array([[math.cos(theta / 2), -math.sin(theta / 2)],
                   [math.sin(theta / 2),  math.cos(theta / 2)]], dtype=complex)
    H = (1 / math.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
    X = np.array([[0, 1], [1, 0]], dtype=complex)
    Z = np.array([[1, 0], [0, -1]], dtype=complex)

    sifted_alice, sifted_bob = [], []
    for i in range(n_circuits):
        if alice_bases[i] != bob_bases[i]:
            continue
        psi = np.array([1, 0], dtype=complex) if alice_bits[i] == 0 else np.array([0, 1], dtype=complex)
        if alice_bases[i] == 1:
            psi = H @ psi
        # Eve intercept-resend: measure in random basis, resend eigenstate
        if eve_present:
            if eve_bases[i] == 1:
                psi = H @ psi
            p = np.abs(psi) ** 2
            m = int(rng.random() < p[1])
            psi = np.array([1, 0], dtype=complex) if m == 0 else np.array([0, 1], dtype=complex)
            if eve_bases[i] == 1:
                psi = H @ psi
        # Channel/optical error rotation
        if e_opt > 0:
            psi = ry @ psi
        # Bob measurement in his basis
        if bob_bases[i] == 1:
            psi = H @ psi
        p = np.abs(psi) ** 2
        bit = int(rng.random() < p[1])
        if rng.random() < p_noise_ratio:
            bit = int(rng.integers(0, 2))
        sifted_alice.append(alice_bits[i]); sifted_bob.append(bit)

    sifted_alice = np.array(sifted_alice); sifted_bob = np.array(sifted_bob)
    qber = float(np.mean(sifted_alice != sifted_bob)) if len(sifted_alice) else float("nan")
    return {"engine": "numpy-statevector", "n_circuits": n_circuits,
            "sifted_bits": int(len(sifted_alice)), "qber": qber,
            "qber_percent": 100 * qber if len(sifted_alice) else float("nan"),
            "eve_present": eve_present}


def qiskit_qber(n_circuits: int = 600, e_opt: float = 0.02,
                p_noise_ratio: float = 0.01, eve_present: bool = False,
                seed: int = 42) -> dict:
    try:
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator
    except Exception as exc:  # pragma: no cover
        return {"engine": "qiskit-unavailable", "error": str(exc)}

    rng = np.random.default_rng(seed)
    simulator = AerSimulator()
    alice_bits = rng.integers(0, 2, n_circuits)
    alice_bases = rng.integers(0, 2, n_circuits)
    bob_bases = rng.integers(0, 2, n_circuits)
    eve_bases = rng.integers(0, 2, n_circuits)

    theta = _error_angle(e_opt)
    circuits, valid = [], []
    for i in range(n_circuits):
        if alice_bases[i] != bob_bases[i]:
            continue
        valid.append(i)
        qc = QuantumCircuit(1, 1)
        if alice_bits[i] == 1:
            qc.x(0)
        if alice_bases[i] == 1:
            qc.h(0)
        if eve_present:
            if eve_bases[i] == 1:
                qc.h(0)
            qc.measure(0, 0)
            if eve_bases[i] == 1:
                qc.h(0)
        if e_opt > 0:
            qc.ry(float(theta), 0)
        if bob_bases[i] == 1:
            qc.h(0)
        qc.measure(0, 0)
        circuits.append(qc)

    if not circuits:
        return {"engine": "qiskit-aer", "n_circuits": n_circuits,
                "sifted_bits": 0, "qber": float("nan"), "qber_percent": float("nan"),
                "eve_present": eve_present}

    job = simulator.run(circuits, shots=1, memory=True, seed_simulator=seed)
    result = job.result()
    try:
        memory = [result.results[k].data.memory[0] for k in range(len(circuits))]
    except Exception:
        try:
            memory = result.get_memory(circuits[0])
        except Exception:
            memory = result.get_memory(0)
    sifted_alice, sifted_bob = [], []
    for k, i in enumerate(valid):
        bit = int(str(memory[k]), 0)
        if rng.random() < p_noise_ratio:
            bit = int(rng.integers(0, 2))
        sifted_alice.append(alice_bits[i]); sifted_bob.append(bit)

    sifted_alice = np.array(sifted_alice); sifted_bob = np.array(sifted_bob)
    qber = float(np.mean(sifted_alice != sifted_bob))
    return {"engine": "qiskit-aer", "n_circuits": n_circuits,
            "sifted_bits": int(len(sifted_alice)), "qber": qber,
            "qber_percent": 100 * qber, "eve_present": eve_present}
