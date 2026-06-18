from setuptools import find_packages, setup

package_name = 'hogpie_servo_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
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
        'console_scripts': [
        'ax12_driver = hogpie_servo_control.ax12_driver:main',
        'encoder_node = hogpie_servo_control.as5600_encoder_node:main',
        'encoder_jointstate = hogpie_servo_control.encoder_jointstate_node:main',
        'joints_controller = hogpie_servo_control.joints_controller_node:main',
        'trajectory_executor = hogpie_servo_control.trajectory_executor_node:main'
        ],
    },
)
