# Week 9: Modbus TCP + OPC-UA User Guide

**Last Updated**: 2026-01-03
**Status**: Day 2 Complete - OPC-UA Gateway Operational

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [System Overview](#system-overview)
3. [Hardware Setup](#hardware-setup)
4. [Firmware Operations](#firmware-operations)
5. [Testing Modbus TCP](#testing-modbus-tcp)
6. [OPC-UA Gateway](#opc-ua-gateway)
7. [Monitoring and Debugging](#monitoring-and-debugging)
8. [Troubleshooting](#troubleshooting)
9. [Next Steps](#next-steps)

---

## Quick Start

### What You Have Right Now

**Working Systems**:
- ✅ MODBUS_1 board at 10.10.10.100:502 (fully operational)
- ✅ OPC-UA gateway server polling MODBUS_1
- ⏳ MODBUS_2 board firmware ready (not flashed yet)

**Quick Test Commands**:

```bash
# Verify Board 1 is online
ping 10.10.10.100

# Test Modbus TCP directly
mbpoll -t 4 -r 1 -c 4 -1 10.10.10.100

# Start OPC-UA gateway (if not running)
python3 opcua_modbus_gateway.py

# Test OPC-UA client
python3 test_opcua_client.py
```

---

## System Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop PC (OPC-UA Server)                │
│                         10.10.10.1                           │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         opcua_modbus_gateway.py                       │  │
│  │         opc.tcp://0.0.0.0:4840/freeopcua/server/     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────┬───────────────────────┬───────────────────┘
                  │ Modbus TCP Poll       │ Modbus TCP Poll
                  │ Every 2 seconds       │ Every 2 seconds
                  │                       │
        ┌─────────▼──────────┐  ┌────────▼──────────┐
        │   Board 1 (F446)   │  │   Board 2 (F446)  │
        │  10.10.10.100:502  │  │  10.10.10.200:502 │
        │     MODBUS_1       │  │     MODBUS_2      │
        │                    │  │                   │
        │  ┌──────────────┐  │  │  ┌──────────────┐ │
        │  │ W5500 SPI    │  │  │  │ W5500 SPI    │ │
        │  │ Ethernet     │  │  │  │ Ethernet     │ │
        │  └──────────────┘  │  │  └──────────────┘ │
        │  ┌──────────────┐  │  │  ┌──────────────┐ │
        │  │ SHT31-D I2C  │  │  │  │ SHT31-D I2C  │ │
        │  │ Temp/Hum     │  │  │  │ Temp/Hum     │ │
        │  └──────────────┘  │  │  └──────────────┘ │
        │  ┌──────────────┐  │  │  ┌──────────────┐ │
        │  │ SSD1306 OLED │  │  │  │ SSD1306 OLED │ │
        │  │ 128x64       │  │  │  │ 128x64       │ │
        │  └──────────────┘  │  │  └──────────────┘ │
        └────────────────────┘  └───────────────────┘
```

### Data Flow

1. **STM32 Boards**: Read SHT31-D sensor every 2 seconds
2. **Modbus TCP**: Expose sensor data as holding registers
3. **OPC-UA Gateway**: Poll Modbus devices every 2 seconds
4. **OPC-UA Clients**: Read data from gateway (UaExpert, Python, SCADA)

---

## Hardware Setup

### Board Configuration

Both boards have identical hardware:

| Component       | Model/Connection                  | Details                          |
|-----------------|-----------------------------------|----------------------------------|
| MCU             | STM32 NUCLEO-F446RE               | ARM Cortex-M4F @ 180MHz          |
| Ethernet        | W5500 SPI module                  | Static IP, no DHCP               |
| Sensor          | SHT31-D I2C                       | Temperature & Humidity           |
| Display         | SSD1306 128x64 OLED               | Real-time status display         |
| Network         | 10.10.10.0/24 subnet              | Gateway: 10.10.10.1              |

### Pin Connections

**W5500 Ethernet Module (SPI1)**:
```
W5500        F446RE        Morpho Connector
────────────────────────────────────────────
MOSI    →    PA7          CN7 pin 14
MISO    →    PA6          CN7 pin 12
SCK     →    PA5          CN7 pin 10
CS      →    PB6          CN7 pin 16
RST     →    PC7          CN5 pin 19
VCC     →    3.3V         CN7 pin 12/16
GND     →    GND          CN7 pin 8
```

**SHT31-D + SSD1306 OLED (I2C1 - Shared Bus)**:
```
Device       F446RE        Arduino Header
─────────────────────────────────────────
SDA     →    PB9          D14
SCL     →    PB8          D15
VCC     →    3.3V         3V3
GND     →    GND          GND
```

### Network Configuration

| Board    | IP Address     | MAC Address         | Modbus Port |
|----------|----------------|---------------------|-------------|
| MODBUS_1 | 10.10.10.100   | 02:00:00:00:00:10   | 502         |
| MODBUS_2 | 10.10.10.200   | 02:00:00:00:00:20   | 502         |
| Desktop  | 10.10.10.1     | (your desktop MAC)  | N/A         |

**Subnet**: 255.255.255.0 (10.10.10.0/24)
**Gateway**: 10.10.10.1 (Desktop PC)

---

## Firmware Operations

### Building Firmware

**Build Board 1 firmware**:
```bash
cd /home/tony/dev/4-month-plan/wk9-opcua-modbus
cargo build --release --bin modbus_1
```

**Build Board 2 firmware**:
```bash
cargo build --release --bin modbus_2
```

**Build both (parallel)**:
```bash
cargo build --release --bin modbus_1 && cargo build --release --bin modbus_2
```

### Flashing Boards

**Identify which probe is connected**:
```bash
probe-rs list
```

Expected output:
```
The following debug probes were found:
[0]: STLink V2-1 (VID: 0483, PID: 374b, Serial: 0671FF3833554B3043164817)
[1]: STLink V2-1 (VID: 0483, PID: 374b, Serial: 066DFF3833584B3043115433)
```

**Flash Board 1 (probe serial ending in ...4817)**:
```bash
probe-rs run --probe 0483:374b:0671FF3833554B3043164817 \
  --chip STM32F446RETx \
  target/thumbv7em-none-eabihf/release/modbus_1
```

**Flash Board 2 (probe serial ending in ...5433)**:
```bash
probe-rs run --probe 0483:374b:066DFF3833584B3043115433 \
  --chip STM32F446RETx \
  target/thumbv7em-none-eabihf/release/modbus_2
```

### Monitoring RTT Logs

When you flash with `probe-rs run`, you'll see real-time debug logs:

```
[INFO ] Initializing Board 1
[INFO ] Configuring W5500 Ethernet...
[INFO ] W5500 version: 0x04
[INFO ] Configuring network: IP=10.10.10.100, Gateway=10.10.10.1
[INFO ] Socket 0 LISTENING on port 502 (status: 0x14) ✓
[INFO ] TCP server ready on port 502!
[INFO ] Initializing SSD1306 OLED display on I2C1 (shared bus)
[INFO ] OLED display initialized successfully
[INFO ] Hardware initialization complete for MODBUS_1
```

### OLED Display Interpretation

**Startup Screen**:
```
MODBUS_1
IP: 10.10.10.100
Initializing...
```

**Normal Operation**:
```
MODBUS_1              ← Board identifier
10.10.10.100:502      ← IP address and Modbus port
T: 30.2C              ← Temperature in Celsius
H: 59.0%              ← Relative humidity
LISTENING             ← Connection status
```

**Status Values**:
- `LISTENING`: Socket open, waiting for connections
- `CONNECTED`: Modbus client actively connected

---

## Testing Modbus TCP

### Network Connectivity Tests

**1. Ping test (verify Ethernet working)**:
```bash
ping -c 4 10.10.10.100
```

Expected output:
```
64 bytes from 10.10.10.100: icmp_seq=1 ttl=128 time=0.090 ms
64 bytes from 10.10.10.100: icmp_seq=2 ttl=128 time=0.089 ms
```

**2. TCP port test (verify socket listening)**:
```bash
nc -zv 10.10.10.100 502
```

Expected output:
```
Connection to 10.10.10.100 502 port [tcp/*] succeeded!
```

### Modbus Register Map

| Modbus Address | Internal Addr | Type    | Size | Description                   |
|----------------|---------------|---------|------|-------------------------------|
| 40001-40002    | 0-1           | float32 | 2    | Temperature (°C)              |
| 40003-40004    | 2-3           | float32 | 2    | Humidity (%RH)                |
| 40005          | 4             | uint16  | 1    | Device Status (0=OK, 1=Error) |
| 40006-40007    | 5-6           | uint32  | 2    | Uptime (seconds)              |
| 40008-40010    | 7-9           | uint16  | 3    | Reserved                      |

**Note**: Modbus uses 1-based addressing (40001+), but protocol uses 0-based internally.

### Modbus Query Examples

**Read all sensor data (temperature, humidity, status, uptime)**:
```bash
mbpoll -a 1 -r 1 -c 7 -t 4 -1 10.10.10.100
```

Example output:
```
[1]:    16882       ← Temperature register 1 (MSB)
[2]:    22328       ← Temperature register 2 (LSB)
[3]:    17002       ← Humidity register 1 (MSB)
[4]:    50810       ← Humidity register 2 (LSB)
[5]:    0           ← Device status (0 = OK)
[6]:    0           ← Uptime MSB
[7]:    3329        ← Uptime LSB (3329 seconds)
```

**Decode float32 values**:
```python
import struct

# Temperature from registers [1] and [2]
temp_bytes = struct.pack('>HH', 16882, 22328)
temperature = struct.unpack('>f', temp_bytes)[0]
print(f"Temperature: {temperature:.1f}°C")  # Output: 30.3°C

# Humidity from registers [3] and [4]
hum_bytes = struct.pack('>HH', 17002, 50810)
humidity = struct.unpack('>f', hum_bytes)[0]
print(f"Humidity: {humidity:.1f}%")  # Output: 58.7%
```

**Read only temperature (2 registers)**:
```bash
mbpoll -a 1 -r 1 -c 2 -t 4 -1 10.10.10.100
```

**Read only humidity (2 registers)**:
```bash
mbpoll -a 1 -r 3 -c 2 -t 4 -1 10.10.10.100
```

**Read device status (1 register)**:
```bash
mbpoll -a 1 -r 5 -c 1 -t 4 -1 10.10.10.100
```

### mbpoll Parameters Explained

```bash
mbpoll -a 1 -r 1 -c 7 -t 4 -1 10.10.10.100
       │   │   │   │   │  └─ IP address
       │   │   │   │   └──── One-shot mode (exit after read)
       │   │   │   └──────── Type: 4=Holding registers
       │   │   └──────────── Count: Number of registers to read
       │   └──────────────── Register: Starting register (1-based)
       └──────────────────── Address: Modbus device ID
```

---

## OPC-UA Gateway

### Starting the Gateway Server

**Terminal 1 - Start OPC-UA server**:
```bash
cd /home/tony/dev/4-month-plan/wk9-opcua-modbus
python3 opcua_modbus_gateway.py
```

Expected output:
```
INFO:__main__:Starting OPC-UA to Modbus TCP Gateway
INFO:__main__:Creating OPC-UA namespace for MODBUS_1
INFO:__main__:Creating OPC-UA namespace for MODBUS_2
INFO:__main__:OPC-UA server starting on opc.tcp://0.0.0.0:4840/freeopcua/server/
INFO:__main__:OPC-UA server is running
INFO:__main__:[MODBUS_1] T=30.3°C, H=58.7%, Status=0, Uptime=3329s
ERROR:__main__:[MODBUS_2] Failed to connect to 10.10.10.200:502
```

Leave this running in the background.

### Testing with Python Client

**Terminal 2 - Test OPC-UA client**:
```bash
python3 test_opcua_client.py
```

Expected output:
```
Connecting to OPC-UA server at opc.tcp://localhost:4840/freeopcua/server/
Connected!

Root node: i=84
Objects node: i=85

ModbusDevices node: ns=2;i=1

MODBUS_1 node: ns=2;i=2

=== MODBUS_1 Current Values ===
Temperature: 30.319290161132812°C
Humidity: 58.675514221191406%
Device Status: 0
Uptime: 3329s
Connection Status: CONNECTED

MODBUS_2 Connection Status: DISCONNECTED
```

### OPC-UA Namespace Structure

```
opc.tcp://0.0.0.0:4840/freeopcua/server/
│
└── Objects (i=85)
    └── ModbusDevices (ns=2;i=1)
        ├── MODBUS_1 (ns=2;i=2)
        │   ├── Temperature (Float) - e.g., 30.3
        │   ├── Humidity (Float) - e.g., 58.7
        │   ├── DeviceStatus (UInt16) - e.g., 0
        │   ├── Uptime (UInt32) - e.g., 3329
        │   └── ConnectionStatus (String) - "CONNECTED"
        │
        └── MODBUS_2 (ns=2;i=3)
            ├── Temperature (Float) - e.g., 0.0
            ├── Humidity (Float) - e.g., 0.0
            ├── DeviceStatus (UInt16) - e.g., 0
            ├── Uptime (UInt32) - e.g., 0
            └── ConnectionStatus (String) - "DISCONNECTED"
```

### Using UaExpert (Professional OPC-UA Client)

**Download and Installation**:
1. Download from: https://www.unified-automation.com/products/development-tools/uaexpert.html
2. Install on Windows/Linux desktop
3. Launch UaExpert

**Connecting to Gateway**:
1. Click **Server** → **Add** → **Double-click "Custom Discovery"**
2. Enter endpoint: `opc.tcp://10.10.10.1:4840/freeopcua/server/`
   - Replace `10.10.10.1` with your desktop's IP if accessing from another machine
3. Right-click server → **Connect**
4. Browse **Address Space** → **Objects** → **ModbusDevices**
5. Expand **MODBUS_1** to see variables
6. Drag variables to **Data Access View** for live monitoring

**Live Monitoring**:
- Variables update every 2 seconds (gateway poll interval)
- Temperature and humidity show real-time sensor data
- ConnectionStatus shows "CONNECTED" or "DISCONNECTED"
- Uptime increments every poll

---

## Monitoring and Debugging

### Real-Time Monitoring Options

**1. OLED Display (on each board)**:
- Physical display on STM32 board
- Updates every 2 seconds
- Shows: Board ID, IP, Temperature, Humidity, Status

**2. RTT Logs (via probe-rs)**:
```bash
probe-rs run --probe <serial> --chip STM32F446RETx target/thumbv7em-none-eabihf/release/modbus_1
```

**3. OPC-UA Gateway Logs**:
```bash
python3 opcua_modbus_gateway.py
# Watch for polling messages every 2 seconds
```

**4. mbpoll (Direct Modbus queries)**:
```bash
# Continuous polling (every 1000ms)
mbpoll -a 1 -r 1 -c 7 -t 4 10.10.10.100
```

**5. Python OPC-UA Client**:
```bash
python3 test_opcua_client.py
# One-shot read of all variables
```

**6. UaExpert**:
- Best for long-term monitoring
- Graphical trend display
- Historical data view

### Log Interpretation

**RTT Log Levels**:
- `[INFO]` - Normal operation
- `[WARN]` - Warning (e.g., OLED not connected)
- `[ERROR]` - Error condition (needs attention)

**Common RTT Messages**:
```
[INFO ] Socket 0 status: 0x14 (LISTEN) ← Waiting for connections
[INFO ] Socket 0 status: 0x17 (ESTABLISHED) ← Client connected
[INFO ] Modbus request received (9 bytes) ← Processing request
[INFO ] Sending Modbus response (17 bytes) ← Response sent
[INFO ] Socket closed by peer ← Client disconnected
```

**OPC-UA Gateway Messages**:
```
INFO:__main__:[MODBUS_1] T=30.3°C, H=58.7%, Status=0, Uptime=3329s
  ↑ Successful poll

ERROR:__main__:[MODBUS_2] Failed to connect to 10.10.10.200:502
  ↑ Board offline or unreachable
```

---

## Troubleshooting

### Board Won't Boot

**Symptom**: No RTT logs, OLED blank, no network response

**Checks**:
1. Verify power LED on Nucleo board is lit
2. Check USB cable connection
3. Try erasing and reflashing:
   ```bash
   probe-rs erase --probe <serial> --chip STM32F446RETx
   probe-rs run --probe <serial> --chip STM32F446RETx target/.../modbus_1
   ```

### Network Unreachable

**Symptom**: `ping 10.10.10.100` fails

**Checks**:
1. Verify desktop IP is 10.10.10.1:
   ```bash
   ip addr show
   # Look for 10.10.10.1/24 on ethernet interface
   ```

2. Check W5500 connections (SPI pins, power, reset)

3. Check RTT logs for W5500 version check:
   ```
   [INFO ] W5500 version: 0x04  ← Should be 0x04
   ```

4. Verify Ethernet cable connected to W5500 module

5. Check if desktop firewall blocking 10.10.10.0/24 subnet

### Modbus Queries Fail

**Symptom**: `mbpoll` returns timeout or connection refused

**Checks**:
1. Verify TCP port 502 is listening:
   ```bash
   nc -zv 10.10.10.100 502
   ```

2. Check RTT logs for socket status:
   ```
   [INFO ] Socket 0 status: 0x14 (LISTEN)  ← Should be 0x14 or 0x17
   ```

3. Try connecting with netcat:
   ```bash
   nc 10.10.10.100 502
   # Should connect (cursor hangs = connected)
   ```

4. Check OLED display shows "LISTENING" status

### OLED Display Blank

**Symptom**: OLED shows nothing, but Modbus works

**This is normal** - System designed to work without OLED

**If you want to debug**:
1. Check I2C wiring (PB8/SCL, PB9/SDA, 3.3V, GND)
2. Verify OLED address is 0x3C (most common)
3. Check RTT logs for:
   ```
   [WARN ] Failed to initialize OLED display
   [WARN ] Check wiring: SCL=PB8 (D15), SDA=PB9 (D14), VCC=3.3V, GND=GND
   ```

### OPC-UA Gateway Can't Connect

**Symptom**: `ERROR:__main__:[MODBUS_1] Failed to connect`

**Checks**:
1. Verify board is online:
   ```bash
   ping 10.10.10.100
   ```

2. Test Modbus directly:
   ```bash
   mbpoll -a 1 -r 1 -c 2 -t 4 -1 10.10.10.100
   ```

3. Check firewall isn't blocking port 502

4. Restart gateway server (Ctrl+C, then rerun)

### Temperature/Humidity Reads Zero

**Symptom**: Modbus returns 0.0 for temperature/humidity

**Checks**:
1. Check SHT31-D I2C wiring (PB8/SCL, PB9/SDA)
2. Check RTT logs for sensor initialization:
   ```
   [INFO ] SHT31-D sensor initialized successfully
   [INFO ] Sensor reading: temp=30.3°C, hum=58.7%
   ```
3. Verify sensor has stable 3.3V power
4. Check for I2C address conflict (should be 0x44)

---

## Next Steps

### Immediate (Day 2 Complete, Day 3 Options)

**Option 1: Flash Board 2 (MODBUS_2)**
```bash
# Build and flash MODBUS_2 firmware
cargo build --release --bin modbus_2
probe-rs run --probe 0483:374b:066DFF3833584B3043115433 \
  --chip STM32F446RETx \
  target/thumbv7em-none-eabihf/release/modbus_2

# Verify both boards accessible
ping 10.10.10.100
ping 10.10.10.200

# OPC-UA gateway will automatically poll both devices
# Watch gateway logs for both boards reporting data
```

**Option 2: Test with UaExpert**
- Download and install UaExpert
- Connect to `opc.tcp://10.10.10.1:4840/freeopcua/server/`
- Monitor live data from MODBUS_1
- Create data trends and historical views

**Option 3: Add Data Logging**
- Modify `opcua_modbus_gateway.py` to write CSV files
- Log temperature/humidity with timestamps
- Create graphs with matplotlib or Grafana

### Future Enhancements

**Software**:
- [ ] Add Modbus FC06 (Write Single Register) support
- [ ] Add configuration registers (poll interval, thresholds)
- [ ] Web server on desktop for browser-based monitoring
- [ ] MQTT publishing for IoT cloud integration
- [ ] InfluxDB + Grafana dashboard
- [ ] Email/SMS alerts on threshold violations

**Hardware**:
- [ ] Add more sensors (pressure, VOC, CO2)
- [ ] Add relay outputs for control
- [ ] Add SD card for local data logging
- [ ] Battery backup with RTC for timestamps

**Integration**:
- [ ] Connect to Phase 3 monitoring architecture
- [ ] SCADA system integration
- [ ] Building automation system (BACnet)
- [ ] AWS IoT / Azure IoT Hub

---

## File Reference

### Key Project Files

| File                        | Purpose                                    |
|-----------------------------|--------------------------------------------|
| `src/modbus_1.rs`           | Board 1 firmware entry point              |
| `src/modbus_2.rs`           | Board 2 firmware entry point              |
| `src/common.rs`             | Shared hardware/protocol code             |
| `opcua_modbus_gateway.py`   | OPC-UA server polling Modbus devices      |
| `test_opcua_client.py`      | Python OPC-UA client test script          |
| `Cargo.toml`                | Rust project configuration                |
| `README.md`                 | Project overview and architecture         |
| `TODO.md`                   | Task tracking and completion status       |
| `NOTES.md`                  | Development session log                   |
| `USERGUIDE.md`              | **This file - operational instructions**  |

### Build Artifacts

```
target/thumbv7em-none-eabihf/release/
├── modbus_1        ← Board 1 firmware binary
└── modbus_2        ← Board 2 firmware binary
```

### Configuration Constants

**In `src/modbus_1.rs`**:
```rust
const BOARD_ID: &str = "MODBUS_1";
const IP_ADDRESS: [u8; 4] = [10, 10, 10, 100];
const MAC_ADDRESS: [u8; 6] = [0x02, 0x00, 0x00, 0x00, 0x00, 0x10];
```

**In `src/modbus_2.rs`**:
```rust
const BOARD_ID: &str = "MODBUS_2";
const IP_ADDRESS: [u8; 4] = [10, 10, 10, 200];
const MAC_ADDRESS: [u8; 6] = [0x02, 0x00, 0x00, 0x00, 0x00, 0x20];
```

**In `opcua_modbus_gateway.py`**:
```python
MODBUS_DEVICES = [
    {"name": "MODBUS_1", "ip": "10.10.10.100", "port": 502, "unit_id": 1},
    {"name": "MODBUS_2", "ip": "10.10.10.200", "port": 502, "unit_id": 1},
]

POLL_INTERVAL = 2.0  # seconds
```

---

## Quick Command Reference

### Build & Flash
```bash
# Build both firmwares
cargo build --release --bin modbus_1 --bin modbus_2

# Flash Board 1
probe-rs run --probe 0483:374b:0671FF3833554B3043164817 \
  --chip STM32F446RETx target/thumbv7em-none-eabihf/release/modbus_1

# Flash Board 2
probe-rs run --probe 0483:374b:066DFF3833584B3043115433 \
  --chip STM32F446RETx target/thumbv7em-none-eabihf/release/modbus_2
```

### Network Testing
```bash
# Ping boards
ping -c 4 10.10.10.100
ping -c 4 10.10.10.200

# Test TCP ports
nc -zv 10.10.10.100 502
nc -zv 10.10.10.200 502
```

### Modbus Testing
```bash
# Read all data (Board 1)
mbpoll -a 1 -r 1 -c 7 -t 4 -1 10.10.10.100

# Read all data (Board 2)
mbpoll -a 1 -r 1 -c 7 -t 4 -1 10.10.10.200

# Continuous monitoring
mbpoll -a 1 -r 1 -c 7 -t 4 10.10.10.100
```

### OPC-UA Operations
```bash
# Start gateway server
python3 opcua_modbus_gateway.py

# Test with Python client
python3 test_opcua_client.py
```

---

**End of User Guide**

For development notes and troubleshooting details, see:
- [README.md](README.md) - Project overview
- [TODO.md](TODO.md) - Task tracking
- [NOTES.md](NOTES.md) - Development session log
