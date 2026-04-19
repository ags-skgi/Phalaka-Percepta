# Phalaka Percepta

An intelligent electronics breadboard — the computer knows what components 
are placed on it. A 4-node proof-of-concept that automatically identifies 
resistors, capacitors, LEDs, and diodes by probing impedance and RC charge 
profiles. Includes a Claude-powered electronics teacher that explains the 
detected circuit in real time.

## What it does

- Probes each node pair using RC charge curves and forward/reverse voltage
- Classifies components: resistor, capacitor, LED, diode, short, open circuit
- Renders the detected circuit live on a visual canvas
- **Ask Teacher** — Claude AI explains what the student has built and guides 
  them to the next step

## Hardware

| Component | Role | Pins |
|-----------|------|------|
| 10kΩ resistors (×3) | Known reference resistors for voltage divider | — |
| Arduino (Uno/Nano) | Drives nodes, reads ADC, sends serial | — |
| Node 1 (D8) | VCC drive | D8 |
| Node 2 (D7) | Mid-point | D7 |
| Node 3 (D6) | GND series return | D6 |
| Node 4 (D5) | GND parallel return | D5 |

## Repository structure

        phalaka-percepta/
        ├── firmware/
        │   └── percep_rc_parr.ino      # Flash this to the Arduino
        ├── src/
        │   └── percep_4node_ui_v3.py   # Run this on your computer
        └── demo/
        └── (photos + video link)
        


### 2. Install Python dependencies

```bash
pip install pyserial anthropic
```

### 3. Add your Anthropic API key

Open `src/percep_4node_ui_v3.py` and paste your key:
```python
ANTHROPIC_API_KEY = "your-key-here"
```

### 4. Configure serial port

In the same file, update:
```python
PORT = "/dev/tty.usbmodem3101"  # Mac example
# Windows: "COM3"
# Linux:   "/dev/ttyUSB0"
```

### 5. Run

```bash
cd src
python percep_4node_ui_v3.py
```

## Usage

1. Place a component between any two nodes on the breadboard
2. The Arduino probes all node pairs automatically in a loop
3. The detected component appears on the canvas with its value
4. Click **Ask Teacher** to open the AI tutor window
5. Type a question — e.g. *"why is the LED brighter now?"* — and Claude 
   responds based on the current detected circuit

## Component detection logic

| Component | Detection method |
|-----------|-----------------|
| Resistor | Voltage divider ratio — steady V_fwd, symmetric V_rev |
| Capacitor | RC charge curve — t63 measured from charge profile |
| LED | High V_fwd (1.8–3.4V), strongly asymmetric fwd/rev ratio |
| Diode | V_fwd 0.4–0.9V, strongly asymmetric |
| Short | V_fwd < 0.05V |
| Open | V_fwd > 4.7V, V_rev < 0.05V |

## Traction

- 4-node POC demonstrated to Physics and Engineering Design faculty at IIT Madras
- Demoed to 10 BTech first-year students on campus
- In discussion with Keiretsu Forum investors (IITMRP) on pre-seed

## Status

POC complete — 4-node grid with real-time detection and AI tutor. 
Full 180-node breadboard design in progress.
