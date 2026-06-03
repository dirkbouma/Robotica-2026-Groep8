from setuptools import find_packages, setup

package_name = 'my_robot_controller1'

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
            "test_node = my_robot_controller1.my_first_node:main",
            "servo_node = my_robot_controller1.servo_controller:main",
            'strawberry_node = my_robot_controller1.strawberry_detector:main'
        ],
    },
)
