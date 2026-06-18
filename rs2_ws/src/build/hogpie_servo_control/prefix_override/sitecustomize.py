import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/groep8/rs2_ws/src/install/hogpie_servo_control'
