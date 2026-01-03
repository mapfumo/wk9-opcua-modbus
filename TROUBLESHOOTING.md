# Week 9: Modbus TCP Troubleshooting Guide

**Project**: W5500 Ethernet + Modbus TCP on STM32F446RE
**Last Updated**: 2026-01-02

---

## Table of Contents

1. [W5500 Communication Issues](#w5500-communication-issues)
2. [SPI Configuration Problems](#spi-configuration-problems)
3. [Build Errors](#build-errors)
4. [Probe/Flashing Issues](#probeflashing-issues)
5. [Network Problems](#network-problems)
6. [Embassy-Specific Issues](#embassy-specific-issues)

---

## W5500 Communication Issues

### ❌ W5500 Returns 0xFF on All Register Reads

**Symptom**:
```
[INFO ] SPI TX: [00 39 00 00]
[INFO ] SPI RX: [FF FF FF FF]
[WARN ] W5500 version: 0xFF - UNEXPECTED (expected 0x04)
```

**Cause**: W5500 not responding - MISO line stays high

**Solutions**:

1. **MOST COMMON - Wrong SPI Pins** ✅ **FIXED**
   ```rust
   // ❌ WRONG - Arduino connector pins
   let spi = Spi::new(p.SPI1, p.PB3, p.PB5, p.PB4, ...);

   // ✅ CORRECT - Morpho connector pins
   let spi = Spi::new(p.SPI1, p.PA5, p.PA7, p.PA6, ...);
   ```

   **How We Found This**:
   - Checked working `modbus_example` code
   - Found it uses PA5/PA6/PA7, not PB3/PB4/PB5
   - Wiring document said "Arduino D11-D13" but actual hardware uses Morpho connector

2. **W5500 Not Powered**:
   - Check 3.3V on VCC pin with multimeter
   - Verify GND connection
   - Some W5500 modules have onboard regulator - check if jumper needed

3. **CS Pin Not Connected**:
   - W5500 ignores all SPI if CS not properly controlled
   - Verify PB6 → CS connection
   - Check CS goes LOW during transaction in logic analyzer

4. **Reset Not Released**:
   - Ensure RST pin (PC7) is HIGH after reset sequence
   - Try longer reset pulse (was 100ms, try 200ms)
   - Try longer PLL stabilization wait (was 50ms, now 200ms)

5. **SPI Mode Mismatch**:
   - W5500 requires SPI Mode 0 (CPOL=0, CPHA=0)
   - Embassy SPI default should be correct, but verify in logic analyzer

6. **Wiring Issues**:
   - Check continuity with multimeter
   - MOSI/MISO swapped?
   - Loose breadboard connections?

**Debugging Steps**:
```rust
// Add this before W5500 read
info!("CS pin state: {}", cs_pin.is_set_high());
info!("RST pin state: {}", rst_pin.is_set_high());

// Toggle CS manually to test
cs_pin.set_low();
Timer::after_millis(1).await;
cs_pin.set_high();
info!("CS toggle test complete");
```

---

## SPI Configuration Problems

### ❌ SPI Transfer Returns Error

**Symptom**:
```rust
Err(_) => warn!("Failed to read W5500 version register - SPI communication error");
```

**Causes & Solutions**:

1. **DMA Channel Conflict**:
   - Ensure no other peripheral uses DMA2_CH2 or DMA2_CH3
   - Embassy will panic if DMA channel already in use

2. **SPI Peripheral Already Initialized**:
   - Embassy peripherals can only be used once
   - Check you're not calling `init_hardware()` multiple times
   - Don't try to create multiple SPI instances from same peripheral

3. **Invalid Pin Configuration**:
   - Ensure pins support SPI alternate function
   - PA5/PA6/PA7 are guaranteed SPI1 pins on F446RE
   - Some pins have multiple alt functions - check reference manual

**Verification**:
```bash
# Check that firmware built successfully
cargo build --release --bin modbus_1 2>&1 | grep "Finished"

# Should show:
# Finished `release` profile [optimized + debuginfo] target(s) in X.XXs
```

---

### ❌ Compiler Error: trait bound not satisfied

**Symptom**:
```
error[E0277]: the trait bound `Spi<...>: SpiDevice` is not satisfied
```

**Solution**:
Don't use generic `SpiDevice` trait, use concrete `Spi` type:

```rust
// ❌ WRONG
async fn w5500_read_register<SPI>(
    spi: &mut SPI,
    ...
) where SPI: SpiDevice

// ✅ CORRECT
async fn w5500_read_register(
    spi: &mut Spi<'_, peripherals::SPI1, peripherals::DMA2_CH3, peripherals::DMA2_CH2>,
    ...
)
```

---

## Build Errors

### ❌ unresolved import: `embedded_hal_async`

**Symptom**:
```
error[E0433]: failed to resolve: use of unresolved module or unlinked crate `embedded_hal_async`
```

**Solution**:
Add to `Cargo.toml`:
```toml
[dependencies]
embedded-hal-async = "1.0"
```

**Why**: Embassy uses async HAL traits from `embedded-hal-async`, not the blocking `embedded-hal` crate.

---

### ❌ Struct takes 3 generic arguments but 1/2 supplied

**Symptom**:
```
error[E0107]: struct takes 3 generic arguments but 1 generic argument was supplied
  --> src/common.rs:25:14
   |
25 |     pub spi: Spi<'static, peripherals::SPI1>,
```

**Solution**:
Specify all three type parameters:
```rust
Spi<'static, peripherals::SPI1, peripherals::DMA2_CH3, peripherals::DMA2_CH2>
//  ^        ^                    ^                      ^
//  lifetime SPI peripheral       TX DMA                 RX DMA
```

---

### ❌ Linker Error: memory.x not found

**Symptom**:
```
error: linking with `rust-lld` failed: exit status: 1
note: rust-lld: error: cannot open memory.x: No such file or directory
```

**Solution**:
Ensure `build.rs` exists and copies `memory.x`:
```rust
use std::env;
use std::fs::File;
use std::io::Write;
use std::path::PathBuf;

fn main() {
    let out = &PathBuf::from(env::var_os("OUT_DIR").unwrap());
    File::create(out.join("memory.x"))
        .unwrap()
        .write_all(include_bytes!("memory.x"))
        .unwrap();
    println!("cargo:rustc-link-search={}", out.display());
    println!("cargo:rerun-if-changed=memory.x");
}
```

---

## Probe/Flashing Issues

### ❌ JtagNoDeviceConnected Error

**Symptom**:
```
WARN probe_rs::probe::stlink: send_jtag_command 242 failed: JtagNoDeviceConnected
Error: Connecting to the chip was unsuccessful.
```

**Causes**:

1. **USB Cable Disconnected**:
   - Check physical USB connection
   - Try different USB port
   - Use `probe-rs list` to verify probe detected

2. **Probe Already in Use**:
   - Another probe-rs instance running?
   - Kill with: `killall probe-rs`
   - Or: find PID with `ps aux | grep probe-rs` and `kill <PID>`

3. **Board Powered Off**:
   - Ensure USB provides power
   - LED on NUCLEO board should be on

4. **BOOT0 Pin Set**:
   - Ensure BOOT0 jumper is in normal position (not bootloader mode)

**Recovery**:
```bash
# List available probes
probe-rs list

# Should show both probes:
# [0]: STLink V2-1 (VID: 0483, PID: 374b, Serial: 0671FF3...)
# [1]: STLink V2-1 (VID: 0483, PID: 374b, Serial: 066DFF3...)

# Try resetting board
# Unplug USB, wait 5 seconds, plug back in
```

---

### ❌ RTT Buffer Not Initialized

**Symptom**:
```
WARN probe_rs::rtt: Buffer for up channel 0 not initialized
```

**Impact**:
- Warning only, not an error
- RTT logs may not appear immediately
- Usually resolves after firmware completes initialization

**Solutions**:
1. Increase timeout: `timeout 10 probe-rs run ...` (instead of 5)
2. RTT logging starts working after Embassy init completes
3. Non-issue - firmware is running correctly

---

### ❌ Available Probes Selection Prompt

**Symptom**:
```
Available Probes:
0: STLink V2-1 -- 0483:374b:066DFF3833584B3043115433 (ST-LINK)
1: STLink V2-1 -- 0483:374b:0671FF3833554B3043164817 (ST-LINK)
Selection:
```

**Cause**:
Both probes connected but `--probe` flag not specific enough

**Solution**:
Use full `VID:PID:Serial` format:
```bash
# ❌ WRONG - probe index can change
probe-rs run --probe 0 ...

# ❌ WRONG - serial alone not recognized
probe-rs run --probe 0671FF3... ...

# ✅ CORRECT - full VID:PID:Serial
probe-rs run --probe "0483:374b:0671FF3833554B3043164817" ...
```

---

## Network Problems

### ❌ Cannot Ping W5500 IP Address

**Symptom**:
```bash
$ ping 10.10.10.100
PING 10.10.10.100 (10.10.10.100) 56(84) bytes of data.
From 10.10.10.1 icmp_seq=1 Destination Host Unreachable
```

**Causes**:

1. **W5500 Not Initialized** (current state):
   - We haven't configured network settings yet
   - Need to set IP/subnet/gateway in W5500 registers
   - This is expected at this stage of development

2. **Ethernet Cable Not Connected**:
   - Check physical RJ45 connection
   - Link LED on W5500 module should be on
   - Try different cable

3. **Wrong Subnet**:
   - Desktop: 10.10.10.1
   - Board 1: 10.10.10.100
   - Board 2: 10.10.10.200
   - All must be /24 (255.255.255.0)

4. **Switch/Router Issues**:
   - Power cycle Ethernet switch
   - Check all devices on same physical network

**Next Implementation Steps** (not done yet):
```rust
// TODO: Configure W5500 network
w5500.set_mac(&[0x02, 0x00, 0x00, 0x00, 0x00, 0x10]);
w5500.set_ip(&[10, 10, 10, 100]);
w5500.set_subnet(&[255, 255, 255, 0]);
w5500.set_gateway(&[10, 10, 10, 1]);
```

---

## Embassy-Specific Issues

### ❌ Peripherals Already Taken Panic

**Symptom**:
```
panicked at 'embassy_stm32::init() may only be called once'
```

**Cause**:
Called `embassy_stm32::init()` multiple times

**Solution**:
- Only call `init()` once in `main()`
- Pass peripherals down to functions
- Don't call `init_hardware()` multiple times

```rust
// ✅ CORRECT
#[embassy_executor::main]
async fn main(spawner: Spawner) {
    common::init_hardware(BOARD_ID).await;  // Only once!
    // ...
}
```

---

### ❌ Task Must Be Async

**Symptom**:
```
error: `#[embassy_executor::task]` must be applied to async functions
```

**Solution**:
All Embassy tasks must be `async`:
```rust
// ❌ WRONG
#[embassy_executor::task]
fn sensor_task() {
    loop {
        // ...
    }
}

// ✅ CORRECT
#[embassy_executor::task]
async fn sensor_task() {
    loop {
        Timer::after_secs(1).await;
        // ...
    }
}
```

---

### ❌ Main Function Must Be Async

**Symptom**:
```
error: main function must be async
```

**Solution**:
Use `#[embassy_executor::main]` macro:
```rust
// ✅ CORRECT
#[embassy_executor::main]
async fn main(spawner: Spawner) {
    // ...
}
```

---

## Common Warnings (Can Ignore)

### ⚠️ Unused Imports/Variables

```
warning: unused import: `defmt::info`
warning: unused variable: `spawner`
warning: function `f32_to_registers` is never used
```

**Impact**: None - just warnings
**Fix**: Prefix with underscore or remove when done prototyping

### ⚠️ `cargo fix` Suggestions

```
warning: `modbus-tcp` (bin "modbus_1") generated 14 warnings
  (run `cargo fix --bin "modbus_1" -p modbus-tcp` to apply 2 suggestions)
```

**Impact**: None - just cleanup suggestions
**Fix**: Run suggested command when code is stable

---

## Debug Checklist

When something doesn't work:

1. ✅ **Build Succeeds**:
   ```bash
   cargo build --release --bin modbus_1 2>&1 | grep -E "(error|Finished)"
   ```

2. ✅ **Flash Succeeds**:
   ```bash
   probe-rs run --probe "0483:374b:0671FF..." --chip STM32F446RETx ...
   # Should show "Finished in X.XXs"
   ```

3. ✅ **Firmware Boots**:
   - Look for initial INFO logs
   - "Embassy peripherals initialized" should appear

4. ✅ **SPI Configured**:
   - "SPI1 initialized at 10 MHz" appears
   - No panics or errors

5. ✅ **Heartbeat Running**:
   - "Board X heartbeat - SPI ready" appears every 2 seconds
   - Proves firmware running and not stuck

6. ✅ **Pin Configuration**:
   - Verify using PA5/PA6/PA7 (not PB3/PB4/PB5)
   - Check `src/common.rs` line 68-72

---

## Quick Reference - Working Configuration

### Pins (VERIFIED CORRECT)
```
PA5 = SPI1_SCK
PA6 = SPI1_MISO
PA7 = SPI1_MOSI
PB6 = CS (GPIO)
PC7 = RST (GPIO)
```

### Probe IDs
```
Board 1: 0483:374b:0671FF3833554B3043164817
Board 2: 0483:374b:066DFF3833584B3043115433
```

### Build Command
```bash
cargo build --release --bin modbus_1
```

### Flash Command
```bash
probe-rs run --probe "0483:374b:0671FF3833554B3043164817" \
  --chip STM32F446RETx \
  target/thumbv7em-none-eabihf/release/modbus_1
```

---

## Getting Help

If stuck:
1. Check this file first
2. Review NOTES.md for context
3. Compare with `../modbus_example/` working code
4. Check Embassy examples: https://github.com/embassy-rs/embassy
5. W5500 datasheet for register details

---

*Last Updated*: 2026-01-02
*Status*: SPI communication working, W5500 pin configuration fixed
