import rclpy

from rclpy.node import Node

from std_msgs.msg import String, Float32


class ExtinguisherController(Node):

    def __init__(self):
        super().__init__('extinguisher_controller')

        # =====================================================
        # CURRENT SYSTEM STATE
        # =====================================================

        self.robot_action = "SEARCH"
        self.aim_status = "IDLE"

        self.extinguisher_angle = 0.0

        # =====================================================
        # SETTINGS
        # =====================================================

        # Servo positions
        self.RELEASE_ANGLE = 0.0
        self.ACTIVATE_ANGLE = 90.0

        # How long the extinguisher remains activated
        self.ACTIVATION_TIME = 3.0

        # Prevent repeated activation
        self.extinguishing = False

        self.activation_start_time = None

        # =====================================================
        # ROBOT ACTION SUBSCRIPTION
        # =====================================================

        self.action_sub = self.create_subscription(
            String,
            '/robot/action',
            self.action_callback,
            10
        )

        # =====================================================
        # AIM STATUS SUBSCRIPTION
        # =====================================================

        self.aim_status_sub = self.create_subscription(
            String,
            '/aim/status',
            self.aim_status_callback,
            10
        )

        # =====================================================
        # EXTINGUISHER SERVO OUTPUT
        # =====================================================

        self.servo_pub = self.create_publisher(
            Float32,
            '/extinguisher/servo',
            10
        )

        # =====================================================
        # EXTINGUISHER STATUS OUTPUT
        # =====================================================

        self.status_pub = self.create_publisher(
            String,
            '/extinguisher/status',
            10
        )

        # =====================================================
        # TIMER
        # =====================================================

        self.timer = self.create_timer(
            0.1,
            self.update_extinguisher
        )

        self.get_logger().info(
            'FireScout Extinguisher Controller started.'
        )

        self.publish_servo(self.RELEASE_ANGLE)

    # =========================================================
    # ROBOT ACTION CALLBACK
    # =========================================================

    def action_callback(self, msg):

        self.robot_action = msg.data.strip()

    # =========================================================
    # AIM STATUS CALLBACK
    # =========================================================

    def aim_status_callback(self, msg):

        self.aim_status = msg.data.strip()

    # =========================================================
    # SERVO COMMAND
    # =========================================================

    def publish_servo(self, angle):

        self.extinguisher_angle = angle

        msg = Float32()
        msg.data = float(angle)

        self.servo_pub.publish(msg)

    # =========================================================
    # STATUS
    # =========================================================

    def publish_status(self, status):

        msg = String()

        msg.data = (
            f'{status} | '
            f'Angle={self.extinguisher_angle:.1f}° | '
            f'Robot={self.robot_action} | '
            f'Aim={self.aim_status}'
        )

        self.status_pub.publish(msg)

    # =========================================================
    # EXTINGUISHER CONTROL
    # =========================================================

    def update_extinguisher(self):

        # -----------------------------------------------------
        # If currently extinguishing
        # -----------------------------------------------------

        if self.extinguishing:

            elapsed = (
                self.get_clock().now().nanoseconds / 1e9
                - self.activation_start_time
            )

            # Keep extinguisher activated
            if elapsed < self.ACTIVATION_TIME:

                self.publish_servo(
                    self.ACTIVATE_ANGLE
                )

                self.publish_status(
                    'EXTINGUISHING'
                )

                return

            # -------------------------------------------------
            # Activation finished
            # -------------------------------------------------

            self.publish_servo(
                self.RELEASE_ANGLE
            )

            self.extinguishing = False
            self.activation_start_time = None

            self.get_logger().info(
                'EXTINGUISHER RELEASED'
            )

            self.publish_status(
                'RELEASED'
            )

            return

        # -----------------------------------------------------
        # Safety condition
        # -----------------------------------------------------

        # Robot must be stopped before activation.

        if self.robot_action != "FIRE_CONFIRMED":

            self.publish_servo(
                self.RELEASE_ANGLE
            )

            self.publish_status(
                'SAFE'
            )

            return

        # -----------------------------------------------------
        # Aim must be locked
        # -----------------------------------------------------

        if not self.aim_status.startswith("AIM_LOCKED"):

            self.publish_servo(
                self.RELEASE_ANGLE
            )

            self.publish_status(
                'WAITING_FOR_AIM'
            )

            return

        # =====================================================
        # FIRE + ROBOT STOPPED + AIM LOCKED
        # =====================================================

        self.extinguishing = True

        self.activation_start_time = (
            self.get_clock().now().nanoseconds / 1e9
        )

        self.publish_servo(
            self.ACTIVATE_ANGLE
        )

        self.get_logger().warn(
            'EXTINGUISHER ACTIVATED'
        )

        self.publish_status(
            'EXTINGUISHING'
        )


# =============================================================
# MAIN
# =============================================================

def main(args=None):

    rclpy.init(args=args)

    node = ExtinguisherController()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        node.get_logger().info(
            'Extinguisher controller stopped.'
        )

    finally:

        # Always release extinguisher servo
        node.publish_servo(
            node.RELEASE_ANGLE
        )

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()