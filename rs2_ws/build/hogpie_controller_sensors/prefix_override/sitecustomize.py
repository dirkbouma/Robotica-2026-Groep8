import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/groep8/rs2_ws/install/hogpie_controller_sensors'
