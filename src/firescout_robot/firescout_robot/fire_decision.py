import rclpy
from rclpy.node import Node

from std_msgs.msg import Float32, String


class FireDecision(Node):

    def __init__(self):
        super().__init__('fire_decision')

        self.temperature = 0.0
        self.gas = 0

        self.temperature_sub = self.create_subscription(
            Float32,
            'sensor/temperature',
            self.temperature_callback,
            10
        )

        self.gas_sub = self.create_subscription(
            Float32,
            'sensor/gas',
            self.gas_callback,
            10
        )

        self.fire_pub = self.create_publisher(
            String,
            'fire/status',
            10
        )

        self.timer = self.create_timer(
            1.0,
            self.evaluate_fire
        )

        self.get_logger().info(
            'FireScout Fire Decision Node started'
        )

    def temperature_callback(self, msg):
        self.temperature = msg.data

    def gas_callback(self, msg):
        self.gas = msg.data

    def evaluate_fire(self):

        if self.temperature >= 40.0 and self.gas >= 600:
            status = "FIRE DETECTED"

        elif self.temperature >= 35.0 or self.gas >= 500:
            status = "WARNING"

        else:
            status = "SAFE"

        msg = String()
        msg.data = (
            f"{status} | "
            f"Temperature: {self.temperature:.1f} C | "
            f"Gas: {self.gas}"
        )

        self.fire_pub.publish(msg)

        self.get_logger().info(msg.data)


def main(args=None):

    rclpy.init(args=args)

    node = FireDecision()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        node.get_logger().info(
            'Fire decision node stopped.'
        )

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()