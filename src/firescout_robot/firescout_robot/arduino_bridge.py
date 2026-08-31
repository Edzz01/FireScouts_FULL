import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_msgs.msg import Float32


class ArduinoBridgeNode(Node):

    def __init__(self):
        super().__init__('arduino_bridge')

        # =====================================================
        # CURRENT MOTOR STATE
        # =====================================================

        self.left_motor = 0
        self.right_motor = 0

        # =====================================================
        # CURRENT SERVO STATE
        # =====================================================

        self.servo_x = 90.0
        self.servo_y = 90.0
        self.extinguisher_servo = 0.0

        # =====================================================
        # MOTOR SETTINGS
        # =====================================================

        self.max_pwm = 255

        # Converts ROS velocity into simulated PWM.
        self.speed_scale = 360.0

        # =====================================================
        # ROS SUBSCRIPTIONS
        # =====================================================

        # Motor command
        self.cmd_vel_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )

        # Horizontal aiming servo
        self.servo_x_sub = self.create_subscription(
            Float32,
            '/aim/servo_x',
            self.servo_x_callback,
            10
        )

        # Vertical aiming servo
        self.servo_y_sub = self.create_subscription(
            Float32,
            '/aim/servo_y',
            self.servo_y_callback,
            10
        )

        # Extinguisher servo
        self.extinguisher_sub = self.create_subscription(
            Float32,
            '/extinguisher/servo',
            self.extinguisher_callback,
            10
        )

        # =====================================================
        # STATUS TIMER
        # =====================================================

        self.status_timer = self.create_timer(
            2.0,
            self.publish_status
        )

        self.get_logger().info(
            'FireScout Arduino Mega Bridge started.'
        )

        self.get_logger().info(
            'Motors + X/Y aiming servos + extinguisher servo ready.'
        )

    # =========================================================
    # MOTOR CONTROL
    # =========================================================

    def cmd_vel_callback(self, msg):

        linear_x = msg.linear.x
        angular_z = msg.angular.z

        # Differential-drive mixing
        left_speed = (
            linear_x - angular_z
        ) * self.speed_scale

        right_speed = (
            linear_x + angular_z
        ) * self.speed_scale

        # Limit PWM
        left_speed = max(
            min(int(left_speed), self.max_pwm),
            -self.max_pwm
        )

        right_speed = max(
            min(int(right_speed), self.max_pwm),
            -self.max_pwm
        )

        self.left_motor = left_speed
        self.right_motor = right_speed

        # Simulated Arduino serial command
        serial_payload = (
            f"M,{left_speed},{right_speed}"
        )

        self.get_logger().info(
            f'MOTOR | Left={left_speed} '
            f'Right={right_speed} | '
            f'Serial TX: {serial_payload}'
        )

    # =========================================================
    # X SERVO
    # =========================================================

    def servo_x_callback(self, msg):

        angle = self.clamp_angle(msg.data)

        self.servo_x = angle

        serial_payload = f'X,{angle:.1f}'

        self.get_logger().info(
            f'AIM X SERVO = {angle:.1f}° | '
            f'Serial TX: {serial_payload}'
        )

    # =========================================================
    # Y SERVO
    # =========================================================

    def servo_y_callback(self, msg):

        angle = self.clamp_angle(msg.data)

        self.servo_y = angle

        serial_payload = f'Y,{angle:.1f}'

        self.get_logger().info(
            f'AIM Y SERVO = {angle:.1f}° | '
            f'Serial TX: {serial_payload}'
        )

    # =========================================================
    # EXTINGUISHER SERVO
    # =========================================================

    def extinguisher_callback(self, msg):

        angle = self.clamp_angle(msg.data)

        self.extinguisher_servo = angle

        serial_payload = f'E,{angle:.1f}'

        if angle >= 90.0:

            self.get_logger().warn(
                f'EXTINGUISHER SERVO = ACTIVATED '
                f'({angle:.1f}°) | '
                f'Serial TX: {serial_payload}'
            )

        else:

            self.get_logger().info(
                f'EXTINGUISHER SERVO = RELEASED '
                f'({angle:.1f}°) | '
                f'Serial TX: {serial_payload}'
            )

    # =========================================================
    # SERVO LIMIT
    # =========================================================

    def clamp_angle(self, angle):

        return max(
            0.0,
            min(180.0, float(angle))
        )

    # =========================================================
    # STATUS
    # =========================================================

    def publish_status(self):

        self.get_logger().info(
            f'ARDUINO STATE | '
            f'Motors L={self.left_motor} '
            f'R={self.right_motor} | '
            f'Aim X={self.servo_x:.1f}° '
            f'Y={self.servo_y:.1f}° | '
            f'Extinguisher={self.extinguisher_servo:.1f}°'
        )


# =============================================================
# MAIN
# =============================================================

def main(args=None):

    rclpy.init(args=args)

    node = ArduinoBridgeNode()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        node.get_logger().info(
            'Arduino bridge stopped.'
        )

    finally:

        # Do not publish after ROS context is invalid.
        if rclpy.ok():

            node.left_motor = 0
            node.right_motor = 0
            node.extinguisher_servo = 0.0

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()