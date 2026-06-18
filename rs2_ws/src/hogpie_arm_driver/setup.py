from setuptools import find_packages, setup

package_name = 'hogpie_arm_driver'

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
            'fake_joint_state_publisher = hogpie_arm_driver.fake_joint_state_publisher:main',
            'trajectory_server = hogpie_arm_driver.trajectory_server:main'
        ],
    },
)
