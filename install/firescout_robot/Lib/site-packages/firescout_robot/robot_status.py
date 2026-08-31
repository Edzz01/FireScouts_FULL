import rclpy
from rclpy.node import Node

from std_msgs.msg import String


class RobotStatus(Node):

    def __init__(self):
        super().__init__('robot_status')

        self.publisher = self.create_publisher(
            String,
            'robot/status',
            10
        )

        self.timer = self.create_timer(
            1.0,
            self.publish_status
        )

        self.battery = 100
        self.temperature = 30.0
        self.distance = 100
        self.mode = "AUTO"
        self.fire = False

        self.get_logger().info(
            'FireScout Robot Status Node started'
        )

    def publish_status(self):

        self.battery -= 0.1

        message = String()

        message.data = (
            f"Battery: {self.battery:.1f}% | "
            f"Temperature: {self.temperature:.1f} C | "
            f"Distance: {self.distance} cm | "
            f"Mode: {self.mode} | "
            f"Fire: {self.fire}"
        )

        self.publisher.publish(message)

        self.get_logger().info(message.data)


def main(args=None):

    rclpy.init(args=args)

    node = RobotStatus()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()