# Week 9: Modbus TCP Implementation Notes

**Date Started**: 2026-01-02
**Hardware**: 2x NUCLEO-F446RE + W5500 Ethernet modules
**Framework**: Embassy async/await

---

## Development Session Log

### Session 1: 2026-01-02 - Project Setup & SPI Initialization

**Objectives**:
- Set up multi-binary Cargo project structure
- Initialize SPI peripheral for W5500 communication
- Verify hardware connectivity

**Achievements**:
1. ✅ Created project with multiple binary targets (`modbus_1`, `modbus_2`, `common`)
2. ✅ Configured all dependencies (Embassy, w5500, rmodbus, sensors, OLED)
3. ✅ Successfully flashed both boards - probe connectivity verified
4. ✅ Implemented SPI initialization with Embassy
5. ✅ Added W5500 reset sequence (100ms pulse)
6. ✅ Implemented W5500 register read function
7. ✅ **Fixed critical pin mapping issue** (see Troubleshooting)

**Key Learnings**:

1. **Pin Configuration Discovery**:
   - Initial attempt used Arduino connector pins (PB3/PB4/PB5)
   - **Actual hardware uses Morpho connector** (PA5/PA6/PA7)
   - Always check working example code first!
   - W5500 wiring document was misleading about pin usage

2. **Embassy SPI Configuration**:
   ```rust
   let spi = Spi::new(
       p.SPI1,
       p.PA5,  // SCK
       p.PA7,  // MOSI
       p.PA6,  // MISO
       p.DMA2_CH3, // TX DMA
       p.DMA2_CH2, // RX DMA
       spi_config,
   );
   ```

3. **W5500 SPI Protocol**:
   - Frame format: `[AddrH] [AddrL] [Control] [Data]`
   - Control byte: `[BSB(5)][RWB(1)][OM(2)]`
   - Version register at 0x0039, should read 0x04
   - CS active low, deselect between transactions

4. **RTT Debugging**:
   - `defmt` logging works perfectly with `probe-rs run`
   - Added TX/RX buffer logging for SPI debugging
   - Very helpful for diagnosing communication issues

**Code Structure Decisions**:

1. **Multiple Binary Targets** (not features):
   - Each board gets its own entry point (`modbus_1.rs`, `modbus_2.rs`)
   - Shared code in `common.rs`
   - Board-specific constants (IP addresses)
   - Cleaner than feature flags for hardware variations

2. **Async Functions Throughout**:
   - Embassy requires async for timers and peripherals
   - Makes code more readable than RTIC state machines
   - Natural fit for network operations

3. **Baby Steps Approach**:
   - First: SPI peripheral only
   - Then: GPIO control pins
   - Then: Register read test
   - Then: Full W5500 initialization
   - Prevents overwhelming debugging sessions

**Next Steps**:
1. ~~Reconnect probe and verify W5500 version reads 0x04~~ ✅
2. ~~Configure W5500 network settings (MAC, IP, subnet, gateway)~~ ✅
3. Test network configuration with ping
4. Open TCP socket on port 502
5. Implement Modbus TCP request/response handling
6. Integrate SHT3x sensor
7. Add OLED display updates

---

### Session 2: 2026-01-02 - W5500 Network Configuration

**Objectives**:
- Add register write functionality to W5500
- Configure network settings (MAC, IP, subnet, gateway)
- Verify network configuration can be written

**Achievements**:
1. ✅ Implemented `w5500_write_register()` function for multi-byte writes
2. ✅ Added W5500 network register constants (MAC, IP, subnet, gateway)
3. ✅ Updated `init_hardware()` to accept IP and MAC parameters
4. ✅ Implemented network configuration sequence in `init_hardware()`
5. ✅ Updated both modbus_1.rs and modbus_2.rs with MAC addresses
6. ✅ Board 1: MAC 02:00:00:00:00:10, IP 10.10.10.100
7. ✅ Board 2: MAC 02:00:00:00:00:20, IP 10.10.10.200

**Key Learnings**:

1. **W5500 Register Write Protocol**:
   ```rust
   async fn w5500_write_register(
       spi: &mut Spi<'_, peripherals::SPI1, peripherals::DMA2_CH3, peripherals::DMA2_CH2>,
       cs: &mut Output<'_, peripherals::PB6>,
       address: u16,
       data: &[u8],
   ) -> Result<(), ()>
   ```
   - Control byte: `(BSB_COMMON_REG << 3) | CONTROL_PHASE_WRITE | 0x00`
   - Frame: [AddrH, AddrL, Control, ...data bytes]
   - Multiple bytes written in single transaction

2. **W5500 Network Configuration Order**:
   ```
   1. Gateway (REG_GAR0 @ 0x0001) - 4 bytes
   2. Subnet  (REG_SUBR0 @ 0x0005) - 4 bytes
   3. MAC     (REG_SHAR0 @ 0x0009) - 6 bytes
   4. IP      (REG_SIPR0 @ 0x000F) - 4 bytes
   ```
   - Order matters for proper network initialization
   - All registers in common register block (BSB=0x00)

3. **MAC Address Selection**:
   - Using locally administered MACs (bit 1 of first byte = 1)
   - Board 1: `02:00:00:00:00:10` (0x02 = locally administered)
   - Board 2: `02:00:00:00:00:20`
   - Avoids conflicts with vendor-assigned MACs

4. **Error Handling Approach**:
   - Early return if W5500 version check fails
   - Early return if any network config write fails
   - Prevents partial configuration
   - Clear logging at each step

**Code Structure Updates**:

1. **Modified function signature** - [common.rs:50](src/common.rs#L50):
   ```rust
   pub async fn init_hardware(
       board_id: &str,
       ip_addr: [u8; 4],
       mac_addr: [u8; 6]
   )
   ```

2. **Network config sequence** - [common.rs:119-156](src/common.rs#L119-L156):
   - Gateway → Subnet → MAC → IP
   - Logged each write with formatted addresses
   - Error checking after each write

3. **Board-specific MACs**:
   - modbus_1.rs: `[0x02, 0x00, 0x00, 0x00, 0x00, 0x10]`
   - modbus_2.rs: `[0x02, 0x00, 0x00, 0x00, 0x00, 0x20]`

**Testing Status**:
- ✅ Code compiles successfully (0.61s release build)
- ✅ Flashed to Board 1 successfully
- ✅ RTT logs show network configuration completed
- ✅ **TCP/IP connectivity achieved!** Network is working!
- ✅ W5500 responds on 10.10.10.100
- ✅ Ready for TCP socket implementation

---

### Session 3: 2026-01-02 - TCP Socket Implementation

**Objectives**:
- Implement W5500 socket register access functions
- Open TCP socket on port 502 (Modbus TCP standard port)
- Verify socket enters LISTEN state

**Achievements**:
1. ✅ Added W5500 socket register constants (Mode, Command, Status, Port)
2. ✅ Implemented socket register read/write functions
3. ✅ Created TCP socket initialization sequence in `init_hardware()`
4. ✅ Socket 0 opened successfully (status: 0x13 = INIT)
5. ✅ **Socket 0 LISTENING on port 502 (status: 0x14) ✓**
6. ✅ TCP server ready for connections!

**Key Learnings**:

1. **W5500 Socket Initialization Sequence**:
   ```
   1. Write Socket Mode Register (REG_S0_MR) = 0x01 (TCP mode)
   2. Write Socket Port Register (REG_S0_PORT0) = 0x01F6 (502 big-endian)
   3. Write Socket Command Register (REG_S0_CR) = 0x01 (OPEN command)
   4. Wait 10ms, verify Status Register (REG_S0_SR) = 0x13 (INIT)
   5. Write Socket Command Register (REG_S0_CR) = 0x02 (LISTEN command)
   6. Wait 10ms, verify Status Register (REG_S0_SR) = 0x14 (LISTEN)
   ```

2. **Socket Register Access**:
   - Socket registers use Block Select Bit (BSB) = 0x01
   - Different from common registers (BSB = 0x00)
   - Control byte: `(BSB_SOCKET0_REG << 3) | CONTROL_PHASE_WRITE | 0x00`

3. **Socket Status Values**:
   - `0x00` = CLOSED
   - `0x13` = INIT (socket initialized, ready for LISTEN/CONNECT)
   - `0x14` = LISTEN (TCP server mode, waiting for connections)
   - `0x17` = ESTABLISHED (connection active)

**RTT Log Output**:
```
[INFO ] Socket 0 LISTENING on port 502 (status: 0x14) ✓
[INFO ] TCP server ready on port 502!
[INFO ] Hardware initialization complete for Board 1
[INFO ] === Board ready - Network configured ===
[INFO ] Board 1 heartbeat - Ready for Modbus TCP
```

**Testing Status**:
- ✅ Builds successfully (0.83s)
- ✅ Flashed to Board 1
- ✅ TCP socket listening on port 502
- ⏳ Next: Test TCP connection with `nc 10.10.10.100 502`
- ⏳ Next: Implement Modbus TCP request/response handling

---

## W5500 Integration Notes

### SPI Configuration
- **Frequency**: Started at 10 MHz (conservative)
- **Mode**: Mode 0 (CPOL=0, CPHA=0)
- **DMA**: Using DMA2_CH3 (TX) and DMA2_CH2 (RX)

### Pin Assignments (VERIFIED)
```
SPI1_SCK  = PA5  (Morpho CN7 pin 10)
SPI1_MISO = PA6  (Morpho CN7 pin 12)
SPI1_MOSI = PA7  (Morpho CN7 pin 14)
CS        = PB6  (Morpho CN7 pin 16) - GPIO output
RST       = PC7  (Morpho CN5 pin 19) - GPIO output
```

### Reset Sequence
```rust
rst.set_low();
Timer::after_millis(100).await;  // Hold reset
rst.set_high();
Timer::after_millis(200).await;  // Wait for PLL lock
```

### Register Read Protocol
1. Assert CS (low)
2. Send: `[AddrH] [AddrL] [Control] [Dummy]`
3. Receive 4 bytes (data in byte 3)
4. Deassert CS (high)

**Example - Reading Version Register**:
```
TX: [00 39 00 00]
RX: [xx xx xx 04]  // 0x04 = W5500 version
```

---

## Embassy Framework Notes

### Peripheral Initialization
```rust
let p = embassy_stm32::init(Default::default());
```
- Must be called once, returns all peripherals
- Peripherals consumed when passed to drivers
- Can't call twice (ownership system prevents it)

### Async Timers
```rust
use embassy_time::Timer;
Timer::after_millis(100).await;
Timer::after_micros(1).await;
```
- Non-blocking delays
- Allows other tasks to run
- Preferred over `cortex_m::asm::delay`

### SPI with DMA
- Fully async SPI operations
- `transfer()` returns Future
- DMA channels required for async operation
- Much more efficient than blocking SPI

---

## Project Structure

```
wk9-opcua-modbus/
├── Cargo.toml          # [[bin]] modbus_1, [[bin]] modbus_2
├── .cargo/
│   └── config.toml     # probe-rs runner, defmt linker flags
├── memory.x            # STM32F446RE linker script
├── build.rs            # Copy memory.x to OUT_DIR
├── TODO.md             # Task tracking
├── README.md           # User-facing documentation
├── NOTES.md            # This file - development notes
├── TROUBLESHOOTING.md  # Known issues and solutions
└── src/
    ├── modbus_1.rs     # Board 1 (10.10.10.100:502)
    ├── modbus_2.rs     # Board 2 (10.10.10.200:502)
    └── common.rs       # Shared W5500, Modbus, sensors, OLED
```

---

## Dependencies Overview

### Core
- `embassy-executor` - Async runtime
- `embassy-stm32` - STM32 HAL with async support
- `embassy-time` - Non-blocking delays
- `embassy-sync` - Async primitives (Mutex, Signal)

### Networking
- `w5500` - W5500 Ethernet driver
- `rmodbus` - Modbus protocol parsing/encoding

### Sensors & Display
- `shtcx` - SHT3x I2C temperature/humidity sensor
- `ssd1306` - OLED display driver
- `embedded-graphics` - Drawing primitives for OLED

### Debug & Utilities
- `defmt` - Efficient logging framework
- `defmt-rtt` - RTT transport for defmt
- `panic-probe` - Panic handler with defmt
- `heapless` - Static data structures (Vec, String)

---

## Build & Flash Commands

### Build Single Binary
```bash
cargo build --release --bin modbus_1
cargo build --release --bin modbus_2
```

### Erase Flash (when boards need reset)
```bash
# Board 1
probe-rs erase --probe 0483:374b:0671FF3833554B3043164817 --chip STM32F446RETx --protocol swd --connect-under-reset

# Board 2
probe-rs erase --probe 0483:374b:066DFF3833584B3043115433 --chip STM32F446RETx --protocol swd --connect-under-reset
```

**Shell Aliases**:
```bash
alias erase_modbus_1='probe-rs erase --probe 0483:374b:0671FF3833554B3043164817 --chip STM32F446RETx --protocol swd --connect-under-reset'
alias erase_modbus_2='probe-rs erase --probe 0483:374b:066DFF3833584B3043115433 --chip STM32F446RETx --protocol swd --connect-under-reset'
```

### Flash with probe-rs
```bash
# Board 1
probe-rs run --probe 0483:374b:0671FF3833554B3043164817 --chip STM32F446RETx target/thumbv7em-none-eabihf/release/modbus_1

# Board 2
probe-rs run --probe 0483:374b:066DFF3833584B3043115433 --chip STM32F446RETx target/thumbv7em-none-eabihf/release/modbus_2
```

### Using Aliases (from DEVELOPMENT_SETUP.md)
```bash
modbus_1  # Build + flash Board 1
modbus_2  # Build + flash Board 2
```

---

## Testing Workflow

### 1. Basic Connectivity
```bash
ping 10.10.10.100
ping 10.10.10.200
```

### 2. TCP Socket Test
```bash
nc 10.10.10.100 502
nc 10.10.10.200 502
```

### 3. Modbus TCP Queries (mbpoll)
```bash
# Read holding registers (FC03)
mbpoll -t 4 -r 1 -c 5 10.10.10.100

# Temperature only
mbpoll -t 4 -r 1 -c 2 10.10.10.100

# Humidity only
mbpoll -t 4 -r 3 -c 2 10.10.10.100
```

---

## Register Map

| Register | Address | Type    | Data Type | Description           |
|----------|---------|---------|-----------|----------------------|
| 40001    | 0x0000  | Holding | float32   | Temperature (°C)     |
| 40003    | 0x0002  | Holding | float32   | Humidity (%RH)       |
| 40005    | 0x0004  | Holding | uint16    | Device Status        |
| 40006    | 0x0005  | Holding | uint32    | Uptime (seconds)     |
| 40008    | 0x0007  | Holding | uint16    | Reserved             |

**Note**: Modbus uses 1-based addressing. Register 40001 = address 0x0000 in protocol.

---

## Performance Notes

### Build Times
- **First build**: ~8 seconds (all dependencies)
- **Incremental rebuild**: ~0.5 seconds (only changed code)
- **Both binaries**: Second build is instant (common.rs cached)

### Flashing Speed
- **probe-rs flash**: ~1 second
- Much faster than OpenOCD

### Binary Size
- **Release build**: ~50KB (with optimizations)
- **Debug build**: ~200KB (without optimizations)

---

## References

- [Embassy Book](https://embassy.dev/book/)
- [W5500 Datasheet](https://www.wiznet.io/product-item/w5500/)
- [Modbus TCP Specification](https://www.modbus.org/specs.php)
- [defmt Documentation](https://defmt.ferrous-systems.com/)
- [probe-rs Documentation](https://probe.rs/)

---

*Last Updated*: 2026-01-02
*Status*: SPI initialization complete, W5500 communication ready for testing

---

### Session 4: 2026-01-03 - OLED Display Integration

**Objectives**:
- Integrate SSD1306 OLED display (128x64)
- Display real-time sensor data and connection status
- Solve I2C bus sharing between sensor and display

**Achievements**:
1. ✅ Integrated ssd1306 and embedded-graphics crates
2. ✅ Implemented I2C bus sharing solution (SHT31-D + OLED on same I2C1)
3. ✅ Created display layout with 5 lines of information
4. ✅ Implemented graceful error handling (system works without OLED)
5. ✅ Updated board IDs to "MODBUS_1" and "MODBUS_2"
6. ✅ Display updates every 2 seconds with live sensor data
7. ✅ Connection status tracking (LISTENING/CONNECTED)

**Key Technical Solutions**:

1. **I2C Bus Sharing Challenge**:
   - Problem: SHT31-D uses async I2C with DMA, OLED requires blocking I2C
   - Solution: Steal I2C1 peripheral twice with different configurations
   - Works because access is strictly sequential in main loop

2. **I2C Configuration**:
   ```rust
   // SHT31-D - Async with DMA
   let i2c_sensor = I2c::new(
       p.I2C1,
       p.PB8, p.PB9,
       I2c1Irqs,
       p.DMA1_CH6,  // TX DMA
       p.DMA1_CH0,  // RX DMA
       Hertz(100_000),
       config,
   );

   // OLED - Blocking without DMA
   let i2c_oled = I2c::new(
       p.I2C1,
       p.PB8, p.PB9,
       I2c1Irqs,
       NoDma,  // No DMA
       NoDma,
       Hertz(100_000),
       config,
   );
   ```

3. **Display Layout** (128x64 pixels, FONT_6X10):
   ```
   Line 1 (y=10):  MODBUS_1
   Line 2 (y=22):  10.10.10.100:502
   Line 3 (y=34):  T: 30.2C
   Line 4 (y=46):  H: 59.0%
   Line 5 (y=58):  LISTENING / CONNECTED
   ```

4. **Graceful Degradation**:
   - All display functions check for errors and return early
   - Modbus and sensor continue working if OLED fails
   - User sees warnings in RTT logs but system remains operational

**Troubleshooting**:

1. **Initial Issue**: OLED configured on I2C2 (PB10/PB3), but physically wired to I2C1 (PB8/PB9)
   - Fixed by checking working sht31-d-nucleo project
   - OLED shares same I2C bus as sensor in reference implementation

2. **Build Errors**: Type mismatch between I2C2 and I2C1 peripheral types
   - Fixed OledDisplay type definition to use I2C1
   - Removed unused I2C2 interrupt bindings

3. **Runtime Panics**: Display functions using `.unwrap()` failed when OLED not available
   - Changed all `.unwrap()` calls to `.is_err()` checks or `let _ =` pattern
   - Functions now return early silently if display fails

**Updated Documentation**:
- ✅ README.md updated with OLED display format
- ✅ TODO.md updated with all completed tasks
- ✅ NOTES.md updated with session details

**Current Status**: 
🎉 **DAY 1 COMPLETE - FULLY OPERATIONAL**

Both boards (MODBUS_1 at 10.10.10.100 and MODBUS_2 at 10.10.10.200) are fully functional with:
- W5500 Ethernet connectivity
- Modbus TCP protocol (FC03)
- SHT31-D sensor readings
- OLED display showing real-time data
- Robust error handling and automatic reconnection

Next steps: OPC-UA server integration on desktop PC (Day 2-3)

