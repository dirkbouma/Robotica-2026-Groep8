from setuptools import find_packages, setup
from glob import glob
from setuptools import find_packages, setup

package_name = 'hogpie_controller_sensors'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
            glob('launch/*.launch.py'))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='groep8',
    maintainer_email='groep8@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts':[
        'tcp_listener = hogpie_controller_sensors.controller_sensors_input:main',
        'data_converter = hogpie_controller_sensors.controller_data_reform:main',
        'moveit_commander = hogpie_controller_sensors.moveit_pose_commander:main',
        'pose_test = hogpie_controller_sensors.hogpie_pose_test:main',
        'ik_test = hogpie_controller_sensors.ik_test:main',
        'workspace_scan = hogpie_controller_sensors.workspace_scan:main',
        'tcp_arm_controller = hogpie_controller_sensors.tcp_arm_controller:main',
        'IkOnly = hogpie_controller_sensors.IkOnly:main',
        'pose_backup = hogpie_controller_sensors.pose_commander_backpy.py:main'
        ],
    },
)
