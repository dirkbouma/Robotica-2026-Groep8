from setuptools import find_packages, setup

package_name = 'hogpie_arm_description'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        (
            'share/ament_index/resource_index/packages',
            ['resource/' + package_name]
        ),
        (
            'share/' + package_name,
            ['package.xml']
        ),
        (
            'share/' + package_name + '/urdf',
            ['urdf/hogpie_arm_description.urdf']
        ),
        (
            'share/' + package_name + '/launch',
            ['launch/display.launch.py']
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='groep8',
    maintainer_email='groep8@todo.todo',
    description='Robot description package',
    license='Apache-2.0',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [],
    },
)