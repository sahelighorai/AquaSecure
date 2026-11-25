"""Live Secure Chat support (merged from the single-file AquaSecure version).

The main AquaSecure engine reports aggregate metrics (QBER, gains, rates),
not raw Alice/Bob bit strings. This module therefore runs a SEPARATE,
explicitly educational BB84 bit-exchange simulation parameterised by the
verified engine outputs of the current scenario:

  pulses -> detections (p_click from the engine) -> basis sifting ->
  QBER sample (20% sacrificed) -> idealised reconciliation with an
  error-correction leakage estimate -> 256-bit Toeplitz privacy
  amplification -> AES-256-GCM message encryption.

It is a software demonstration, NOT a composable/finite-key QKD
implementation and NOT a production security proof. Keys are only issued
when the verified engine verdict for the current scenario is Secure.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import secrets
import uuid

import numpy as np

OUT_BITS = 256  # AES-256


def _h2(q: float) -> float:
    q = float(min(max(q, 1e-12), 1.0 - 1e-12))
    return float(-q * math.log2(q) - (1.0 - q) * math.log2(1.0 - q))


def click_probabilities(ch: dict, ev: dict, cfg) -> tuple[float, float, float]:
    """(p_signal, p_noise, p_click) per pulse, from verified engine outputs."""
    y0 = float(ch["y0"])
    q_mu = float(ev["q_mu"])
    p_noise = y0
    p_signal = max(0.0, q_mu - y0)
    p_click = p_signal + p_noise - p_signal * p_noise
    return p_signal, p_noise, min(1.0, p_click)


def generate_chat_key(ch: dict, ev: dict, cfg, qber_threshold: float = 0.11) -> dict:
    """Simulate a BB84 exchange and derive a 256-bit AES key.

    Raises ValueError with a user-readable reason whenever a key must not
    be issued (non-Secure verdict, excessive sampled QBER, too few sifted
    bits, or insufficient estimated entropy)."""
    if str(ev.get("security_status")) != "Secure" or float(ev.get("secure_rate_bps", 0.0)) <= 0:
        raise ValueError(
            "The current scenario is not Secure (status: "
            f"{ev.get('security_status')}). Chat key generation is disabled — "
            "fix the link (shorter distance, lower NTU, night operation, Eve off) first.")
    qber_model = float(min(max(ev["e_mu"], 0.0), 0.5))
    if qber_model >= qber_threshold:
        raise ValueError("Modelled QBER is at or above the abort threshold; no chat key issued.")

    _, _, p_click = click_probabilities(ch, ev, cfg)
    if p_click <= 0:
        raise ValueError("Detection probability is zero; no key can be generated.")

    # Target ~4,000 detections so the sifted sample is statistically usable,
    # with a hard cap to stay interactive on poor links.
    n_pulses = int(np.clip(max(20_000, math.ceil(4000 / p_click)), 20_000, 1_000_000))
    rng = np.random.default_rng(secrets.randbits(32))

    alice_bits = np.unpackbits(
        np.frombuffer(secrets.token_bytes((n_pulses + 7) // 8), dtype=np.uint8))[:n_pulses].copy()
    alice_bases = rng.integers(0, 2, size=n_pulses, dtype=np.uint8)
    bob_bases = rng.integers(0, 2, size=n_pulses, dtype=np.uint8)
    detections = rng.random(n_pulses) < p_click
    sifted_idx = np.flatnonzero(detections & (alice_bases == bob_bases))
    if sifted_idx.size < 1200:
        raise ValueError(
            f"Only {sifted_idx.size} sifted detections simulated. Improve the link "
            "(shorter/clearer) before generating a chat key.")

    bob_bits = alice_bits.copy()
    bob_bits[rng.random(n_pulses) < qber_model] ^= 1
    alice_sifted = alice_bits[sifted_idx]
    bob_sifted = bob_bits[sifted_idx]

    perm = rng.permutation(sifted_idx.size)
    sample_n = max(200, int(0.20 * sifted_idx.size))
    sample_idx, key_idx = perm[:sample_n], perm[sample_n:]
    qber_sample = float(np.mean(alice_sifted[sample_idx] != bob_sifted[sample_idx]))
    if qber_sample >= qber_threshold:
        raise ValueError(
            f"Sampled QBER {qber_sample:.2%} exceeds the {qber_threshold:.0%} abort "
            "threshold. No chat key was created.")

    alice_key = alice_sifted[key_idx].astype(np.uint8)
    n_key = int(alice_key.size)
    f_ec = float(getattr(cfg, "f_ec", 1.16))
    p_multi = float(min(max(ev.get("qd_p_multi") or 0.0, 0.0), 0.5))
    leakage = int(math.ceil(f_ec * n_key * _h2(qber_sample)))
    est_secure = int(max(0, math.floor(n_key * (1.0 - p_multi) - leakage)))
    if est_secure < OUT_BITS:
        raise ValueError(
            f"Estimated remaining entropy is only {est_secure} bits; {OUT_BITS} are "
            "needed for AES-256. Improve the link and retry.")

    # Idealised reconciliation (demonstrator): Bob's key is aligned to
    # Alice's after charging the leakage budget above. A real system must
    # exchange and verify error-correction syndromes.
    reconciled = alice_key.copy()

    # Toeplitz universal hashing (pedagogical privacy amplification).
    seed_len = n_key + OUT_BITS - 1
    tseed = np.unpackbits(np.frombuffer(
        secrets.token_bytes((seed_len + 7) // 8), dtype=np.uint8))[:seed_len].astype(np.uint8)
    rows = np.arange(OUT_BITS, dtype=np.int64)[:, None]
    cols = np.arange(n_key, dtype=np.int64)[None, :]
    matrix = tseed[rows - cols + n_key - 1]
    key_bits = (matrix @ reconciled) % 2
    aes_key = np.packbits(key_bits.astype(np.uint8)).tobytes()
    assert len(aes_key) == 32

    return {
        "key": aes_key,
        "key_fingerprint": hashlib.sha256(aes_key).hexdigest()[:16],
        "n_pulses": n_pulses,
        "detected": int(detections.sum()),
        "sifted": int(sifted_idx.size),
        "sampled": int(sample_n),
        "key_bits_before_pa": n_key,
        "qber_sample": qber_sample,
        "estimated_ec_leakage_bits": leakage,
        "estimated_secure_bits": est_secure,
        "multiphoton_penalty": p_multi,
        "status": "SIMULATED KEY ESTABLISHED",
    }


def encrypt_chat_packet(message: str, sender: str, aes_key: bytes,
                        packet_loss: float = 0.0, corruption: float = 0.0,
                        latency_ms: int = 40) -> dict:
    """Encrypt with AES-256-GCM, simulate transit, authenticate + decrypt."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.exceptions import InvalidTag

    packet_id = uuid.uuid4().hex[:12]
    receiver = "Bob" if sender == "Alice" else "Alice"
    aad = f"AquaSecure|v1|{packet_id}|{sender}->{receiver}".encode()
    nonce = secrets.token_bytes(12)  # fresh 96-bit GCM nonce per packet
    ct = AESGCM(aes_key).encrypt(nonce, message.encode(), aad)
    packet = {
        "packet_id": packet_id, "sender": sender, "receiver": receiver,
        "nonce_b64": base64.b64encode(nonce).decode(),
        "ciphertext_and_tag_b64": base64.b64encode(ct).decode(),
        "aad": aad.decode(), "simulated_latency_ms": int(latency_ms),
        "simulated_corruption": False,
    }
    if secrets.randbelow(1_000_000) < int(packet_loss * 1_000_000):
        packet.update(delivered=False, status="PACKET DROPPED", received_text=None)
        return packet
    received = bytearray(ct)
    if received and secrets.randbelow(1_000_000) < int(corruption * 1_000_000):
        received[secrets.randbelow(len(received))] ^= 1 << secrets.randbelow(8)
        packet["simulated_corruption"] = True
    try:
        text = AESGCM(aes_key).decrypt(nonce, bytes(received), aad).decode()
        packet.update(delivered=True, status="AUTHENTICATED & DECRYPTED", received_text=text)
    except Exception:
        packet.update(delivered=False, status="AUTHENTICATION FAILED", received_text=None)
    return packet


def aes_gcm_integrity_tests(aes_key: bytes) -> list[dict]:
    """Deterministic tamper tests: untouched / cipher flip / tag flip / wrong key."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    msg = b"AquaSecure deterministic integrity test"
    aad = b"AquaSecure|v1|integrity-test|Alice->Bob"
    nonce = secrets.token_bytes(12)
    good = AESGCM(aes_key).encrypt(nonce, msg, aad)
    out = []

    def attempt(key, data):
        try:
            return AESGCM(key).decrypt(nonce, data, aad) == msg
        except Exception:
            return False

    ok = attempt(aes_key, good)
    out.append({"Test": "Untouched packet", "Expected": "Decrypt successfully",
                "Observed": "Decrypted original plaintext" if ok else "Rejected valid packet",
                "Result": "PASS" if ok else "FAIL"})
    for name, mutated in (("Ciphertext bit-flip", bytes([good[0] ^ 1]) + good[1:]),
                          ("Authentication-tag bit-flip", good[:-1] + bytes([good[-1] ^ 1]))):
        rejected = not attempt(aes_key, mutated)
        out.append({"Test": name, "Expected": "Reject packet",
                    "Observed": "Rejected: authentication tag mismatch" if rejected else "Incorrectly accepted",
                    "Result": "PASS" if rejected else "FAIL"})
    rejected = not attempt(secrets.token_bytes(32), good)
    out.append({"Test": "Incorrect AES key", "Expected": "Reject packet",
                "Observed": "Rejected: authentication tag mismatch" if rejected else "Incorrectly accepted",
                "Result": "PASS" if rejected else "FAIL"})
    return out


def packet_log_json(messages: list[dict]) -> bytes:
    return json.dumps(messages, indent=2, ensure_ascii=False).encode()
