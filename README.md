# Week 9: W5500 Ethernet + Modbus TCP

Embedded Modbus TCP slaves on STM32F446RE with W5500 Ethernet modules.

## Hardware Configuration

### Board 1
- **MCU**: STM32 NUCLEO-F446RE
- **Ethernet**: W5500 SPI module
- **IP Address**: 10.10.10.100:502 (static)
- **Sensor**: SHT3x (I2C) - Temperature & Humidity
- **Display**: SSD1306 OLED 128x64 (I2C)

### Board 2
- **MCU**: STM32 NUCLEO-F446RE
- **Ethernet**: W5500 SPI module
- **IP Address**: 10.10.10.200:502 (static)
- **Sensor**: SHT3x (I2C) - Temperature & Humidity
- **Display**: SSD1306 OLED 128x64 (I2C)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Desktop PC (OPC-UA Server)                │
│                         10.10.10.1                           │
└─────────────────┬───────────────────────┬───────────────────┘
                  │ Modbus TCP Poll       │ Modbus TCP Poll
                  │                       │
        ┌─────────▼──────────┐  ┌────────▼──────────┐
        │   Board 1 (F446)   │  │   Board 2 (F446)  │
        │  10.10.10.100:502  │  │  10.10.10.200:502 │
        │                    │  │                   │
        │  ┌──────────────┐  │  │  ┌──────────────┐ │
        │  │ Modbus Slave │  │  │  │ Modbus Slave │ │
        │  │  FC03, FC04  │  │  │  │  FC03, FC04  │ │
        │  └──────────────┘  │  │  └──────────────┘ │
        │  ┌──────────────┐  │  │  ┌──────────────┐ │
        │  │   SHT3x      │  │  │  │   SHT3x      │ │
        │  │  (Sensor)    │  │  │  │  (Sensor)    │ │
        │  └──────────────┘  │  │  └──────────────┘ │
        │  ┌──────────────┐  │  │  ┌──────────────┐ │
        │  │   SSD1306    │  │  │  │   SSD1306    │ │
        │  │   (OLED)     │  │  │  │   (OLED)     │ │
        │  └──────────────┘  │  │  └──────────────┘ │
        └────────────────────┘  └───────────────────┘
```

## Modbus Register Map

| Address      | Type            | Size | Description                      |
|--------------|-----------------|------|----------------------------------|
| 40001-40002  | Holding (FC03)  | f32  | Temperature (°C)                 |
| 40003-40004  | Holding (FC03)  | f32  | Humidity (%RH)                   |
| 40005        | Holding (FC03)  | u16  | Device Status (0=OK, 1=Error)    |
| 40006-40007  | Holding (FC03)  | u32  | Uptime (seconds)                 |
| 40008-40010  | Holding (FC03)  | u16  | Reserved                         |

**Note**: Modbus uses 1-based addressing. Register 40001 = address 0 in protocol.

## Technology Stack

- **Framework**: Embassy (async/await)
- **Ethernet**: w5500 crate (SPI driver, static IP)
- **Protocol**: rmodbus (parsing/encoding) + custom TCP server
- **Sensor**: shtcx crate (SHT3x I2C driver)
- **Display**: ssd1306 crate (OLED I2C driver)
- **Graphics**: embedded-graphics (text rendering)
- **Logging**: defmt + probe-rs RTT

## Project Structure

```
wk9-opcua-modbus/
├── Cargo.toml           # Multiple binary targets
├── .cargo/config.toml   # Embedded target configuration
├── memory.x             # STM32F446RE linker script
├── build.rs             # Build script
├── TODO.md              # Task tracking
├── README.md            # This file
└── src/
    ├── modbus_1.rs      # Board 1 entry point (10.10.10.100)
    ├── modbus_2.rs      # Board 2 entry point (10.10.10.200)
    └── common.rs        # Shared code (W5500, Modbus, SHT3x, OLED)
```

## Building

Build for Board 1:
```bash
cargo build --release --bin modbus_1
```

Build for Board 2:
```bash
cargo build --release --bin modbus_2
```

## Flashing

Flash to Board 1:
```bash
probe-rs run --chip STM32F446RETx target/thumbv7em-none-eabihf/release/modbus_1
```

Flash to Board 2:
```bash
probe-rs run --chip STM32F446RETx target/thumbv7em-none-eabihf/release/modbus_2
```

## Testing

### Network Connectivity

Ping Board 1:
```bash
ping 10.10.10.100
```

Ping Board 2:
```bash
ping 10.10.10.200
```

TCP connection test:
```bash
nc 10.10.10.100 502
```

### Modbus Queries

Read temperature and humidity (FC03 - Read Holding Registers):
```bash
# Board 1
mbpoll -t 4 -r 1 -c 5 10.10.10.100

# Board 2
mbpoll -t 4 -r 1 -c 5 10.10.10.200
```

Read specific registers:
```bash
# Temperature only (registers 40001-40002)
mbpoll -t 4 -r 1 -c 2 10.10.10.100

# Humidity only (registers 40003-40004)
mbpoll -t 4 -r 3 -c 2 10.10.10.100
```

### OLED Display

The OLED (128x64) displays real-time status, updating every 2 seconds:

**Startup Screen:**
```
MODBUS_1
IP: 10.10.10.100
Initializing...
```

**Running Screen:**
```
MODBUS_1
10.10.10.100:502
T: 30.2C
H: 59.0%
LISTENING
```

When a Modbus client connects, the status changes to "CONNECTED".

## Pin Connections

### W5500 Ethernet Module (SPI)

| W5500 Pin | F446RE Pin | Connector  | Function    |
|-----------|------------|------------|-------------|
| MOSI      | PA7        | Morpho CN7 | SPI1_MOSI   |
| MISO      | PA6        | Morpho CN7 | SPI1_MISO   |
| SCK       | PA5        | Morpho CN7 | SPI1_SCK    |
| CS        | PB6        | Morpho CN7 | GPIO_OUT    |
| RST       | PC7        | Morpho CN5 | GPIO_OUT    |
| GND       | GND        | GND        | Ground      |
| VCC       | 3V3        | 3V3        | Power       |

**Note**: Using Morpho connector SPI1 default pins (PA5/PA6/PA7). Verified working with modbus_example.

### SHT3x Sensor (I2C)
| SHT3x Pin | F446RE Pin | Function    |
|-----------|------------|-------------|
| SDA       | PB9        | I2C1_SDA    |
| SCL       | PB8        | I2C1_SCL    |
| GND       | GND        | Ground      |
| VDD       | 3V3        | Power       |

### SSD1306 OLED (I2C - Shared Bus)
| OLED Pin  | F446RE Pin | Function    |
|-----------|------------|-------------|
| SDA       | PB9        | I2C1_SDA    |
| SCL       | PB8        | I2C1_SCL    |
| GND       | GND        | Ground      |
| VCC       | 3V3        | Power       |

**Note**: SHT3x and SSD1306 share the same I2C bus (I2C1).

## Network Configuration

- **Subnet**: 10.10.10.0/24
- **Gateway**: 10.10.10.1 (Desktop PC)
- **Board 1**: 10.10.10.100 (static)
- **Board 2**: 10.10.10.200 (static)
- **Modbus Port**: 502 (standard)
- **No DHCP**: Static IP configuration only

## Next Steps (Day 2-3)

1. Install OPC-UA server on desktop
2. Configure OPC-UA to poll both Modbus slaves
3. Map Modbus registers to OPC-UA variables
4. Test OPC-UA client (UaExpert)
5. Integrate with Phase 3 architecture

## References

- [Modbus TCP Specification](https://www.modbus.org/specs.php)
- [W5500 Datasheet](https://www.wiznet.io/product-item/w5500/)
- [Embassy Framework](https://embassy.dev/)
- [rmodbus Documentation](https://docs.rs/rmodbus/)
