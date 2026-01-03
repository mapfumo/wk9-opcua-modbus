#!/usr/bin/env python3
"""
Test OPC-UA client to show data from both boards
"""
import asyncio
from asyncua import Client

async def read_board_data(client, board_name):
    """Read all data from a specific board"""
    try:
        objects = client.get_objects_node()
        modbus_devices = await objects.get_child(["2:ModbusDevices"])
        board = await modbus_devices.get_child([f"2:{board_name}"])

        temp = await board.get_child(["2:Temperature"])
        hum = await board.get_child(["2:Humidity"])
        status = await board.get_child(["2:DeviceStatus"])
        uptime = await board.get_child(["2:Uptime"])
        conn = await board.get_child(["2:ConnectionStatus"])

        temp_val = await temp.read_value()
        hum_val = await hum.read_value()
        status_val = await status.read_value()
        uptime_val = await uptime.read_value()
        conn_val = await conn.read_value()

        return {
            "temperature": temp_val,
            "humidity": hum_val,
            "status": status_val,
            "uptime": uptime_val,
            "connection": conn_val
        }
    except Exception as e:
        return None

async def main():
    url = "opc.tcp://localhost:4840/freeopcua/server/"
    print(f"Connecting to OPC-UA server at {url}\n")

    async with Client(url=url) as client:
        print("=" * 60)

        # Read MODBUS_1
        data1 = await read_board_data(client, "MODBUS_1")
        if data1 and data1["connection"] == "CONNECTED":
            print("MODBUS_1 (10.10.10.100:502) - CONNECTED")
            print(f"  Temperature: {data1['temperature']:.1f}°C")
            print(f"  Humidity: {data1['humidity']:.1f}%")
            print(f"  Device Status: {data1['status']}")
            print(f"  Uptime: {data1['uptime']}s ({data1['uptime']//60}min {data1['uptime']%60}s)")
        else:
            print("MODBUS_1 (10.10.10.100:502) - DISCONNECTED")

        print()

        # Read MODBUS_2
        data2 = await read_board_data(client, "MODBUS_2")
        if data2 and data2["connection"] == "CONNECTED":
            print("MODBUS_2 (10.10.10.200:502) - CONNECTED")
            print(f"  Temperature: {data2['temperature']:.1f}°C")
            print(f"  Humidity: {data2['humidity']:.1f}%")
            print(f"  Device Status: {data2['status']}")
            print(f"  Uptime: {data2['uptime']}s ({data2['uptime']//60}min {data2['uptime']%60}s)")
        else:
            print("MODBUS_2 (10.10.10.200:502) - DISCONNECTED")

        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
