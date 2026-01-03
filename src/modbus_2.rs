#![no_std]
#![no_main]

mod common;

use defmt::info;
use embassy_executor::Spawner;
use embassy_stm32 as _;  // Import to register time driver
use {defmt_rtt as _, panic_probe as _};

// Board 2 Configuration
const BOARD_ID: &str = "MODBUS_2";
const IP_ADDRESS: [u8; 4] = [10, 10, 10, 200];
const MAC_ADDRESS: [u8; 6] = [0x02, 0x00, 0x00, 0x00, 0x00, 0x20]; // Locally administered MAC
const MODBUS_PORT: u16 = 502;

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    info!("========================================");
    info!("Week 9: Modbus TCP Slave - {}", BOARD_ID);
    info!("========================================");

    // Initialize hardware (W5500 with network config)
    common::init_hardware(BOARD_ID, IP_ADDRESS, MAC_ADDRESS).await;

    // TODO: Display board info on OLED
    // common::display_startup(&mut oled, BOARD_ID, IP_ADDRESS);

    // TODO: Spawn sensor reading task
    // spawner.spawn(common::sensor_task(sensor)).unwrap();

    // TODO: Spawn OLED update task
    // spawner.spawn(common::oled_task(oled)).unwrap();

    // TODO: Run Modbus TCP server (blocking)
    // common::run_modbus_server(w5500, MODBUS_PORT).await;

    info!("=== Board ready - Network configured ===");

    // Temporary: heartbeat to verify firmware is running
    loop {
        embassy_time::Timer::after_secs(2).await;
        info!("{} heartbeat - Ready for Modbus TCP", BOARD_ID);
    }
}
