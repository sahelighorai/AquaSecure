"""Water-type optical parameter tables for the underwater channel model.

Absorption (a) and scattering (b) coefficients at ~532 nm (green window).
Values are *typical literature values* for oceanic water types used in
underwater optical wireless communication (UOWC) studies, e.g. in the
tradition of Mobley, *Light and Water* (1994) and the UOWC review literature.
They are order-of-magnitude representative, NOT site measurements.

IMPORTANT (claim boundary): before citing any of these numbers in a journal
submission, verify them against the primary source and state the wavelength
and water-type convention explicitly. See README.md.
"""

WATER_TYPES = {
    "Clear ocean": {
        "absorption": 0.114,   # a, m^-1
        "scattering": 0.037,   # b, m^-1
        "typical_ntu": "< 5",
        "description": "Type I open ocean. Low attenuation; the best-case underwater optical link.",
        "color": "#0e6f8e",
    },
    "Coastal ocean": {
        "absorption": 0.179,   # a, m^-1
        "scattering": 0.219,   # b, m^-1
        "typical_ntu": "5 – 20",
        "description": "Type II coastal water. Noticeable scattering from suspended particulate.",
        "color": "#1d8fb5",
    },
    "Harbor": {
        "absorption": 0.295,   # a, m^-1
        "scattering": 1.05,    # b, m^-1
        "typical_ntu": "20 – 50",
        "description": "Type III harbor / estuarine water. Strong scattering; port and harbour links.",
        "color": "#2ea3a0",
    },
    "Turbid harbor": {
        "absorption": 0.366,   # a, m^-1
        "scattering": 2.19,    # b, m^-1
        "typical_ntu": "50 – 100+",
        "description": "High-turbidity harbour / river mouth. Usually the limiting case for UQKD.",
        "color": "#c2691e",
    },
}

BACKGROUND_LEVELS = {
    "Night (moonless)": 1.0e3,        # background detections per second at the receiver
    "Artificial lighting": 1.0e5,
    "Daylight": 1.0e7,
}

BACKGROUND_DESCRIPTIONS = {
    "Night (moonless)": "Moonless night, deep or well-covered water column.",
    "Artificial lighting": "Dock / harbour lighting, e.g. LEDs or sodium lamps.",
    "Daylight": "Daytime operation, sunlit water, shallow depth.",
}


def total_base_attenuation(water_type: str) -> tuple[float, float]:
    """Return (a, b) in m^-1 for the selected water type."""
    w = WATER_TYPES[water_type]
    return w["absorption"], w["scattering"]
