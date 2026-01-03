# Week 9: W5500 Ethernet + Modbus TCP - TODO

## Project Status
- **Start Date**: Week 9 (Phase 3)
- **Hardware**: 2x STM32 NUCLEO-F446RE with W5500 Ethernet modules
- **Sensors**: SHT31-D (I2C) - Temperature & Humidity
- **Display**: SSD1306 OLED 128x64 (I2C)
- **Network**: Static IPs - 10.10.10.100 (MODBUS_1), 10.10.10.200 (MODBUS_2)
- **Status**: ✅ **DAY 1 COMPLETE - FULLY OPERATIONAL**

## Hardware Setup
- [x] W5500 modules wired to both F446RE boards
- [x] Static IP addresses tested (10.10.10.100, 10.10.10.200)
- [x] SHT31-D sensors connected on I2C1 (PB8/PB9)
- [x] OLED displays connected on I2C1 (PB8/PB9 - shared bus)
- [x] Document W5500 SPI pin connections
- [x] Document SHT31-D I2C pin connections
- [x] Document OLED I2C pin connections

## Day 1: Project Setup & Build Verification
- [x] Create project structure (wk9-opcua-modbus)
- [x] Copy config files from wk7 (.cargo/config.toml, memory.x, build.rs)
- [x] Create Cargo.toml with dependencies
- [x] Create TODO.md for task tracking
- [x] Create README.md with architecture overview
- [x] Create source files (modbus_1.rs, modbus_2.rs, common.rs)
- [x] Test build compiles: `cargo build --bin modbus_1`
- [x] Test build compiles: `cargo build --bin modbus_2`
- [x] Flash and test Board 1 (MODBUS_1)

## Implementation: W5500 Ethernet (common.rs)
- [x] Initialize SPI1 peripheral (PA5/PA6/PA7)
- [x] Configure W5500 CS (PB6), RESET (PC7) pins
- [x] Set static IP address (10.10.10.x)
- [x] Set subnet mask (255.255.255.0)
- [x] Set gateway (10.10.10.1)
- [x] Configure MAC address
- [x] Open TCP socket on port 502
- [x] Test socket listening and accepting connections
- [x] Implement socket reconnection handling

## Implementation: Modbus TCP Protocol (common.rs)
- [x] Define register map (40001-40010 holding registers)
  - [x] 40001-40002: Temperature (2 registers, f32)
  - [x] 40003-40004: Humidity (2 registers, f32)
  - [x] 40005: Device status (1 register, u16)
  - [x] 40006-40007: Uptime seconds (2 registers, u32)
  - [x] 40008-40010: Reserved (3 registers)
- [x] Implement MBAP header parsing
- [x] Implement FC03 handler (Read Holding Registers)
- [x] Implement exception response codes (0x02 - Illegal Address)
- [x] Create TCP server loop (accept, read, parse, respond)
- [x] Add Modbus frame logging (defmt)
- [x] Handle socket state machine (CLOSED, LISTEN, ESTABLISHED, CLOSE_WAIT)

## Implementation: SHT31-D Sensor (common.rs)
- [x] Initialize I2C1 peripheral (PB8/PB9)
- [x] Configure I2C with DMA (DMA1_CH6/DMA1_CH0)
- [x] Implement soft reset command
- [x] Implement sensor reading (high repeatability mode)
- [x] Poll sensor every 2 seconds in main loop
- [x] Convert raw values to temperature (°C) and humidity (%)
- [x] Add sensor error handling
- [x] Log sensor readings via defmt

## Implementation: OLED Display (common.rs)
- [x] Initialize I2C1 for OLED (shared bus with SHT31-D)
- [x] Solve I2C bus sharing between async DMA (sensor) and blocking (OLED)
- [x] Initialize SSD1306 driver (128x64)
- [x] Create display layout:
  - [x] Line 1: Board ID ("MODBUS_1" / "MODBUS_2")
  - [x] Line 2: IP address and port (10.10.10.100:502)
  - [x] Line 3: Temperature (T: XX.XC)
  - [x] Line 4: Humidity (H: XX.X%)
  - [x] Line 5: Connection status ("LISTENING" / "CONNECTED")
- [x] Update OLED every 2 seconds
- [x] Display startup banner
- [x] Implement graceful error handling (system works without OLED)

## Board-Specific Configuration
- [x] modbus_1.rs: Set BOARD_ID = "MODBUS_1"
- [x] modbus_1.rs: Set IP_ADDRESS = [10, 10, 10, 100]
- [x] modbus_2.rs: Set BOARD_ID = "MODBUS_2"
- [x] modbus_2.rs: Set IP_ADDRESS = [10, 10, 10, 200]
- [x] Initialize Embassy executor
- [x] Call common::init_hardware()
- [x] Implement main Modbus server loop

## Testing: Modbus Queries
- [x] Test Board 1 FC03: `mbpoll -a 1 -r 40001 -c 4 -t 4 -1 10.10.10.100`
- [x] Verify temperature and humidity readings
- [x] Test reading all registers (0-6)
- [x] Test invalid register range (returns exception 0x02)
- [x] Test IEEE 754 float decoding
- [ ] Test Board 2 (pending hardware setup)
- [ ] Test simultaneous queries to both boards

## Testing: Network Connectivity
- [x] Ping test: `ping 10.10.10.100`
- [x] TCP connection test with Python socket
- [x] Verify W5500 version register (0x04)
- [x] Verify socket status transitions
- [ ] Ping test: `ping 10.10.10.200`
- [ ] Check ARP table: `arp -a`

## Documentation
- [x] Document register map in README.md
- [x] Document pin connections in README.md
- [x] Document build/flash commands in README.md
- [x] Add example mbpoll commands in README.md
- [x] Document network setup in README.md
- [x] Document OLED display format in README.md
- [x] Update TODO.md with completion status

## Technical Achievements

### I2C Bus Sharing Solution
Successfully implemented shared I2C1 bus between:
- **SHT31-D sensor**: Async I2C with DMA (DMA1_CH6/DMA1_CH0)
- **SSD1306 OLED**: Blocking I2C without DMA (NoDma/NoDma)

Method: Steal I2C1 peripheral twice with different configurations. Works because devices are accessed sequentially in the main loop, never simultaneously.

### W5500 Socket State Machine
Implemented robust socket handling:
- **0x00 (CLOSED)**: Reopen socket
- **0x13 (INIT)**: Send LISTEN command
- **0x14 (LISTEN)**: Wait for client connection
- **0x17 (ESTABLISHED)**: Process Modbus requests
- **0x1C (CLOSE_WAIT)**: Close and reopen socket

### Modbus Register Encoding
- Temperature/Humidity: IEEE 754 float32 big-endian (2 registers each)
- Status: u16 (1 register)
- Uptime: u32 big-endian (2 registers)
- 0-based addressing internally, 1-based (40001+) in Modbus protocol

## Day 2-3: OPC-UA Integration (Desktop)
- [ ] Install open62541 or opcua crate
- [ ] Create OPC-UA server on desktop
- [ ] Poll both Modbus slaves (10.10.10.100, 10.10.10.200)
- [ ] Expose OPC-UA variables for each sensor
- [ ] Test OPC-UA client (UaExpert)

## Stretch Goals
- [ ] Add Modbus FC06 (Write Single Register) support
- [ ] Add configuration register (sample rate)
- [ ] Add multiple sensor support per board
- [ ] Add SNMP support for monitoring
- [ ] Add web server for diagnostics

## Notes
- Embassy async/await framework for consistency
- Custom W5500 SPI driver (direct register access, no DHCP)
- Custom Modbus TCP implementation (no external TCP stack)
- Static IPs configured (no DHCP needed)
- Both boards share common.rs to avoid code duplication
- OLED shows real-time sensor data and connection status
- System works gracefully without OLED (failsafe design)
