import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class MotorController(Node):

    def __init__(self):
        super().__init__('motor_controller')

        self.last_command_time = self.get_clock().now()
        self.timeout_seconds = 0.5

        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )

        self.timer = self.create_timer(
            0.1,
            self.safety_check
        )

        self.get_logger().info('Motor Controller started.')

    def cmd_vel_callback(self, msg):

        self.last_command_time = self.get_clock().now()

        linear = msg.linear.x
        angular = msg.angular.z

        if abs(linear) < 0.01 and abs(angular) < 0.01:
            command = 'STOP'

        elif linear > 0.01 and abs(angular) < 0.01:
            command = 'FORWARD'

        elif linear < -0.01 and abs(angular) < 0.01:
            command = 'BACKWARD'

        elif angular > 0.01:
            command = 'TURN LEFT'

        elif angular < -0.01:
            command = 'TURN RIGHT'

        else:
            command = 'STOP'

        self.get_logger().info(
            f'{command} | '
            f'linear.x={linear:.2f} | '
            f'angular.z={angular:.2f}'
        )

    def safety_check(self):

        elapsed = (
            self.get_clock().now() - self.last_command_time
        ).nanoseconds / 1e9

        if elapsed > self.timeout_seconds:
            # Stop motors here later when Arduino is connected.
            pass


def main(args=None):
    rclpy.init(args=args)

    node = MotorController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()