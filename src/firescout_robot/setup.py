from setuptools import find_packages, setup

package_name = 'firescout_robot'

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
    maintainer='edzzjoseph',
    maintainer_email='68220640+Edzz01@users.noreply.github.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
    'console_scripts': [
        'robot_status = firescout_robot.robot_status:main',
        'sensor_simulator = firescout_robot.sensor_simulator:main',
        'fire_decision = firescout_robot.fire_decision:main',
        'robot_state = firescout_robot.robot_state:main',
        'robot_controller = firescout_robot.robot_controller:main',
        'motor_controller = firescout_robot.motor_controller:main',
        'web_bridge = firescout_robot.web_bridge:main',
        'arduino_bridge = firescout_robot.arduino_bridge:main',
        'fire_detector = firescout_robot.fire_detector_node:main',
        'fire_response = firescout_robot.fire_response:main',
        'aim_controller = firescout_robot.aim_controller:main',
        'extinguisher_controller = firescout_robot.extinguisher_controller:main',
    ],
},
)
