#!/usr/bin/env python3
"""
Simple OPC-UA client to test the gateway server
"""
import asyncio
from asyncua import Client

async def main():
    url = "opc.tcp://localhost:4840/freeopcua/server/"

    print(f"Connecting to OPC-UA server at {url}")

    async with Client(url=url) as client:
        print("Connected!")

        # Browse the root objects
        root = client.get_root_node()
        print(f"\nRoot node: {root}")

        objects = client.get_objects_node()
        print(f"Objects node: {objects}")

        # Get ModbusDevices folder
        modbus_devices = await objects.get_child(["2:ModbusDevices"])
        print(f"\nModbusDevices node: {modbus_devices}")

        # Get MODBUS_1
        modbus_1 = await modbus_devices.get_child(["2:MODBUS_1"])
        print(f"\nMODBUS_1 node: {modbus_1}")

        # Read all variables
        temp = await modbus_1.get_child(["2:Temperature"])
        hum = await modbus_1.get_child(["2:Humidity"])
        status = await modbus_1.get_child(["2:DeviceStatus"])
        uptime = await modbus_1.get_child(["2:Uptime"])
        conn = await modbus_1.get_child(["2:ConnectionStatus"])

        print("\n=== MODBUS_1 Current Values ===")
        print(f"Temperature: {await temp.read_value()}°C")
        print(f"Humidity: {await hum.read_value()}%")
        print(f"Device Status: {await status.read_value()}")
        print(f"Uptime: {await uptime.read_value()}s")
        print(f"Connection Status: {await conn.read_value()}")

        # Try MODBUS_2 (will show DISCONNECTED)
        try:
            modbus_2 = await modbus_devices.get_child(["2:MODBUS_2"])
            conn2 = await modbus_2.get_child(["2:ConnectionStatus"])
            print(f"\nMODBUS_2 Connection Status: {await conn2.read_value()}")
        except Exception as e:
            print(f"\nMODBUS_2: {e}")

if __name__ == "__main__":
    asyncio.run(main())
