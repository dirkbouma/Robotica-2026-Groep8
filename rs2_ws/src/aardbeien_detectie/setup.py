from setuptools import find_packages, setup

package_name = "aardbeien_detectie"

setup(
    name=package_name,
    version="1.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages",
         [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/detectie.launch.py"]),
        (f"share/{package_name}/config",  ["config/detectie_params.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Jouw Naam",
    maintainer_email="jij@example.com",
    description="Aardbeidetectie via reCamera RTSP-stream — ROS2 node",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "detectie_node = aardbeien_detectie.strawberry_detection_node:main",
		"kleur_node = aardbeien_detectie.color_detection_node:main"
        ],
    },
)
