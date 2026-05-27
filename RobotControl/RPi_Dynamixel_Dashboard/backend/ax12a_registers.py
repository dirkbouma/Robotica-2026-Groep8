# Control table for Dynamixel AX-12A
# Refer to the official ROBOTIS e-Manual for AX-12A control table

CONTROL_TABLE = {
    # EEPROM Area (Requires torque off to change usually, stored permanently)
    "Model Number": {"address": 0, "size": 2, "type": "EEPROM"},
    "Firmware Version": {"address": 2, "size": 1, "type": "EEPROM"},
    "ID": {"address": 3, "size": 1, "type": "EEPROM", "min": 0, "max": 253},
    "Baud Rate": {"address": 4, "size": 1, "type": "EEPROM", "min": 0, "max": 254},
    "Return Delay Time": {"address": 5, "size": 1, "type": "EEPROM", "min": 0, "max": 254},
    "CW Angle Limit": {"address": 6, "size": 2, "type": "EEPROM", "min": 0, "max": 1023},
    "CCW Angle Limit": {"address": 8, "size": 2, "type": "EEPROM", "min": 0, "max": 1023},
    "Temperature Limit": {"address": 11, "size": 1, "type": "EEPROM", "min": 0, "max": 100},
    "Min Voltage Limit": {"address": 12, "size": 1, "type": "EEPROM", "min": 50, "max": 160},
    "Max Voltage Limit": {"address": 13, "size": 1, "type": "EEPROM", "min": 50, "max": 160},
    "Max Torque": {"address": 14, "size": 2, "type": "EEPROM", "min": 0, "max": 1023},
    "Status Return Level": {"address": 16, "size": 1, "type": "EEPROM", "min": 0, "max": 2},
    "Alarm LED": {"address": 17, "size": 1, "type": "EEPROM", "min": 0, "max": 127},
    "Shutdown": {"address": 18, "size": 1, "type": "EEPROM", "min": 0, "max": 127},
    
    # RAM Area (Resets on power cycle)
    "Torque Enable": {"address": 24, "size": 1, "type": "RAM", "min": 0, "max": 1},
    "LED": {"address": 25, "size": 1, "type": "RAM", "min": 0, "max": 1},
    "CW Compliance Margin": {"address": 26, "size": 1, "type": "RAM", "min": 0, "max": 255},
    "CCW Compliance Margin": {"address": 27, "size": 1, "type": "RAM", "min": 0, "max": 255},
    "CW Compliance Slope": {"address": 28, "size": 1, "type": "RAM", "min": 0, "max": 254},
    "CCW Compliance Slope": {"address": 29, "size": 1, "type": "RAM", "min": 0, "max": 254},
    "Goal Position": {"address": 30, "size": 2, "type": "RAM", "min": 0, "max": 1023},
    "Moving Speed": {"address": 32, "size": 2, "type": "RAM", "min": 0, "max": 2047},
    "Torque Limit": {"address": 34, "size": 2, "type": "RAM", "min": 0, "max": 1023},
    "Present Position": {"address": 36, "size": 2, "type": "RAM", "readonly": True},
    "Present Speed": {"address": 38, "size": 2, "type": "RAM", "readonly": True},
    "Present Load": {"address": 40, "size": 2, "type": "RAM", "readonly": True},
    "Present Voltage": {"address": 42, "size": 1, "type": "RAM", "readonly": True},
    "Present Temperature": {"address": 43, "size": 1, "type": "RAM", "readonly": True},
    "Registered": {"address": 44, "size": 1, "type": "RAM", "readonly": True},
    "Moving": {"address": 46, "size": 1, "type": "RAM", "readonly": True},
    "Lock": {"address": 47, "size": 1, "type": "RAM", "min": 0, "max": 1},
    "Punch": {"address": 48, "size": 2, "type": "RAM", "min": 0, "max": 1023},
}

ADDR_GOAL_POSITION = CONTROL_TABLE["Goal Position"]["address"]
ADDR_PRESENT_POSITION = CONTROL_TABLE["Present Position"]["address"]
ADDR_PRESENT_VOLTAGE = CONTROL_TABLE["Present Voltage"]["address"]
ADDR_PRESENT_TEMPERATURE = CONTROL_TABLE["Present Temperature"]["address"]
ADDR_PRESENT_LOAD = CONTROL_TABLE["Present Load"]["address"]
ADDR_TORQUE_ENABLE = CONTROL_TABLE["Torque Enable"]["address"]
