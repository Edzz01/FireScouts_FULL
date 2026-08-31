import random

import rclpy
from rclpy.node import Node

from std_msgs.msg import Float32, Bool


class SensorSimulator(Node):

    def __init__(self):
        super().__init__('sensor_simulator')

        self.temperature_pub = self.create_publisher(
            Float32,
            'sensor/temperature',
            10
        )

        self.distance_pub = self.create_publisher(
            Float32,
            'sensor/distance',
            10
        )

        self.gas_pub = self.create_publisher(
            Float32,
            'sensor/gas',
            10
        )

        self.fire_pub = self.create_publisher(
            Bool,
            'fire/detected',
            10
        )

        self.timer = self.create_timer(
            1.0,
            self.publish_sensors
        )

        self.get_logger().info(
            'FireScout Sensor Simulator started'
        )

    def publish_sensors(self):

        temperature = random.uniform(28.0, 45.0)
        distance = random.uniform(30.0, 250.0)
        gas = random.randint(100, 800)

        fire_detected = (
            temperature >= 40.0 and
            gas >= 600
        )

        temp_msg = Float32()
        temp_msg.data = temperature
        self.temperature_pub.publish(temp_msg)

        distance_msg = Float32()
        distance_msg.data = distance
        self.distance_pub.publish(distance_msg)

        gas_msg = Float32()
        gas_msg.data = float(gas)

        self.get_logger().info(
            f"GAS DEBUG -> variable={gas} | message={gas_msg.data}"
        )

        self.gas_pub.publish(gas_msg)

        fire_msg = Bool()
        fire_msg.data = fire_detected
        self.fire_pub.publish(fire_msg)

        self.get_logger().info(
            f'Temp: {temperature:.1f} C | '
            f'Distance: {distance:.1f} cm | '
            f'Gas: {gas} | '
            f'Fire: {fire_detected}'
        )


def main(args=None):
    rclpy.init(args=args)

    node = SensorSimulator()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()