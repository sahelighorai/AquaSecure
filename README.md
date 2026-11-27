# AquaSecure: A Security-Aware Digital Twin for Underwater Quantum Key Distribution

## 1. Project Overview

AquaSecure is a Python-based simulation project that demonstrates underwater quantum communication using the BB84 Quantum Key Distribution (QKD) protocol.

It studies how underwater environmental conditions affect secure quantum communication, focusing on water turbidity, photon loss, environmental noise, and eavesdropping attacks.

## 2. Problem Statement

Underwater quantum communication faces several challenges, including light absorption, scattering, photon loss, and environmental disturbances. These factors can affect communication reliability and security.

AquaSecure simulates these conditions to analyse their impact on quantum key generation and secure communication.

## 3. Project Objectives

- Implement the BB84 quantum key distribution protocol.
- Simulate underwater quantum communication.
- Analyse the effect of water turbidity.
- Study photon loss and environmental noise.
- Simulate eavesdropping attacks.
- Visualize simulation results using an interactive dashboard.

## 4. Key Features

- BB84 protocol simulation.
- Underwater turbidity analysis.
- Photon loss simulation.
- Environmental noise analysis.
- Eavesdropping attack simulation.
- Interactive result visualization.

## 5. Technologies Used

- Python
- NumPy
- Pandas
- Matplotlib
- Other libraries listed in requirements.txt

## 6. Project Structure

```text
AquaSecure/
│
├── aquasecure/          # Main project modules
├── report/              # Project reports and documents
├── app.py               # Main application
├── README.md            # Project documentation
├── JOURNAL_NOTES.md     # Project development notes
├── requirements.txt     # Required Python libraries
└── .gitignore           # Git ignored files
```

## 7. Installation and Execution

### Step 1: Clone the repository

```bash
git clone https://github.com/sahelighorai/AquaSecure.git
```

### Step 2: Enter the project directory

```bash
cd AquaSecure
```

### Step 3: Create a virtual environment (optional)

```bash
python -m venv venv
```

### Step 4: Activate the environment on Windows

```bash
venv\Scripts\activate
```

### Step 5: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Run the application

Check the application framework and instructions in app.py before choosing the appropriate run command.

## 8. Expected Results

- Simulation of quantum key generation using BB84.
- Analysis of underwater photon transmission.
- Observation of photon loss and environmental noise.
- Evaluation of eavesdropping effects.
- Graphical representation of simulation performance.

## 9. Future Scope

- Improve underwater quantum channel modelling.
- Explore more environmental conditions.
- Enhance security analysis.
- Extend the simulation to different underwater communication scenarios.

## 10. Project Information

**Project:** AquaSecure

**Domain:** Quantum Communication and Cybersecurity

**Protocol:** BB84 Quantum Key Distribution

**Language:** Python

**Project Type:** Academic Simulation Project
