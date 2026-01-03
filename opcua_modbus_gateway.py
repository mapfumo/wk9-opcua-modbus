#!/usr/bin/env python3
"""
OPC-UA to Modbus TCP Gateway
Polls Modbus TCP slaves and exposes data via OPC-UA server
"""
import asyncio
import logging
import struct
from asyncua import Server, ua
from pymodbus.client import ModbusTcpClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modbus device configuration
MODBUS_DEVICES = [
    {"name": "MODBUS_1", "ip": "10.10.10.100", "port": 502, "unit_id": 1},
    {"name": "MODBUS_2", "ip": "10.10.10.200", "port": 502, "unit_id": 1},
]

# Modbus register map (0-based addressing internally)
REG_TEMPERATURE = 0  # Registers 0-1 (40001-40002): f32 temperature
REG_HUMIDITY = 2     # Registers 2-3 (40003-40004): f32 humidity
REG_STATUS = 4       # Register 4 (40005): u16 status
REG_UPTIME = 5       # Registers 5-6 (40006-40007): u32 uptime

# Poll interval (seconds)
POLL_INTERVAL = 2.0


def decode_float32(registers):
    """Decode two Modbus registers as IEEE 754 float32 (big-endian)"""
    if len(registers) != 2:
        return None
    # Pack as big-endian 16-bit integers, unpack as big-endian float
    bytes_data = struct.pack('>HH', registers[0], registers[1])
    return struct.unpack('>f', bytes_data)[0]


def decode_uint32(registers):
    """Decode two Modbus registers as uint32 (big-endian)"""
    if len(registers) != 2:
        return None
    return (registers[0] << 16) | registers[1]


async def poll_modbus_device(client_info, nodes):
    """Poll a single Modbus device and update OPC-UA nodes"""
    name = client_info["name"]
    ip = client_info["ip"]
    port = client_info["port"]
    unit_id = client_info["unit_id"]

    client = ModbusTcpClient(ip, port=port)

    try:
        if not client.connect():
            logger.error(f"[{name}] Failed to connect to {ip}:{port}")
            await nodes["status"].write_value("DISCONNECTED")
            return False

        # Read all registers (0-6) using FC03 (Read Holding Registers)
        # Modbus protocol uses 0-based addressing here
        result = client.read_holding_registers(address=0, count=7, device_id=unit_id)

        if result.isError():
            logger.error(f"[{name}] Modbus read error: {result}")
            await nodes["status"].write_value("ERROR")
            client.close()
            return False

        # Decode data
        registers = result.registers
        temperature = decode_float32(registers[0:2])
        humidity = decode_float32(registers[2:4])
        status_value = registers[4]
        uptime = decode_uint32(registers[5:7])

        # Update OPC-UA nodes
        if temperature is not None:
            await nodes["temperature"].write_value(temperature)
        if humidity is not None:
            await nodes["humidity"].write_value(humidity)

        await nodes["device_status"].write_value(status_value)
        if uptime is not None:
            await nodes["uptime"].write_value(uptime)
        await nodes["status"].write_value("CONNECTED")

        logger.info(f"[{name}] T={temperature:.1f}°C, H={humidity:.1f}%, Status={status_value}, Uptime={uptime}s")

        client.close()
        return True

    except Exception as e:
        logger.error(f"[{name}] Exception: {e}")
        await nodes["status"].write_value("ERROR")
        try:
            client.close()
        except:
            pass
        return False


async def main():
    logger.info("Starting OPC-UA to Modbus TCP Gateway")

    # Create OPC-UA server
    server = Server()
    await server.init()

    server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
    server.set_server_name("Modbus TCP to OPC-UA Gateway")

    # Setup namespace
    uri = "http://opcua.modbus.gateway"
    idx = await server.register_namespace(uri)

    # Create root object
    objects = server.get_objects_node()
    root = await objects.add_object(idx, "ModbusDevices")

    # Create OPC-UA nodes for each Modbus device
    device_nodes = {}

    for device in MODBUS_DEVICES:
        name = device["name"]
        logger.info(f"Creating OPC-UA namespace for {name}")

        # Create device folder
        device_folder = await root.add_object(idx, name)

        # Create variables for sensor data
        temp_node = await device_folder.add_variable(idx, "Temperature", 0.0)
        hum_node = await device_folder.add_variable(idx, "Humidity", 0.0)
        status_node = await device_folder.add_variable(idx, "DeviceStatus", 0)
        uptime_node = await device_folder.add_variable(idx, "Uptime", 0)
        connection_node = await device_folder.add_variable(idx, "ConnectionStatus", "DISCONNECTED")

        # Make variables writable by clients (optional)
        await temp_node.set_writable()
        await hum_node.set_writable()
        await status_node.set_writable()
        await uptime_node.set_writable()
        await connection_node.set_writable()

        device_nodes[name] = {
            "temperature": temp_node,
            "humidity": hum_node,
            "device_status": status_node,
            "uptime": uptime_node,
            "status": connection_node,
        }

    logger.info("OPC-UA server starting on opc.tcp://0.0.0.0:4840/freeopcua/server/")

    async with server:
        logger.info("OPC-UA server is running")

        # Polling loop
        while True:
            for device in MODBUS_DEVICES:
                name = device["name"]
                await poll_modbus_device(device, device_nodes[name])

            # Wait before next poll
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
