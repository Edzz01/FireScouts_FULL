import rclpy
from rclpy.node import Node

from std_msgs.msg import Float32
from std_msgs.msg import Bool
from std_msgs.msg import String


class RobotState(Node):

    def __init__(self):
        super().__init__('robot_state')

        self.temperature = 0.0
        self.distance = 0.0
        self.gas = 0.0
        self.fire = False

        self.create_subscription(
            Float32,
            '/sensor/temperature',
            self.temperature_callback,
            10
        )

        self.create_subscription(
            Float32,
            '/sensor/distance',
            self.distance_callback,
            10
        )

        self.create_subscription(
            Float32,
            '/sensor/gas',
            self.gas_callback,
            10
        )

        self.create_subscription(
            Bool,
            '/fire/detected',
            self.fire_callback,
            10
        )

        self.status_publisher = self.create_publisher(
            String,
            '/robot/status',
            10
        )

        self.timer = self.create_timer(
            1.0,
            self.publish_status
        )

    def temperature_callback(self, msg):
        self.temperature = msg.data

    def distance_callback(self, msg):
        self.distance = msg.data

    def gas_callback(self, msg):
        self.gas = msg.data

    def fire_callback(self, msg):
        self.fire = msg.data

    def publish_status(self):

        status = String()

        fire_status = "DETECTED" if self.fire else "CLEAR"

        status.data = (
            f"Temperature: {self.temperature:.1f} C | "
            f"Distance: {self.distance:.1f} cm | "
            f"Gas: {self.gas:.1f} | "
            f"Fire: {fire_status}"
        )

        self.status_publisher.publish(status)


def main(args=None):

    rclpy.init(args=args)

    node = RobotState()

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