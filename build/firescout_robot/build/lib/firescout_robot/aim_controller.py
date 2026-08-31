import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool, Float32, String


class AimController(Node):

    def __init__(self):

        super().__init__('aim_controller')

        # =====================================================
        # CURRENT AI STATE
        # =====================================================

        self.fire_detected = False
        self.fire_class = "none"
        self.confidence = 0.0

        self.center_x = -1.0
        self.center_y = -1.0
        self.robot_action = "SEARCH"

        # =====================================================
        # CAMERA FRAME
        # =====================================================

        # Your detector uses a 320 x 320 model.
        #
        # The center is therefore:
        #
        # X = 160
        # Y = 160

        self.image_width = 320.0
        self.image_height = 320.0

        self.image_center_x = self.image_width / 2.0
        self.image_center_y = self.image_height / 2.0

        # =====================================================
        # SERVO SETTINGS
        # =====================================================

        self.servo_x = 90.0
        self.servo_y = 90.0

        self.min_servo_x = 0.0
        self.max_servo_x = 180.0

        self.min_servo_y = 0.0
        self.max_servo_y = 180.0

        # How much the servo moves per update.
        self.servo_step = 2.0

        # Dead zone around image center.
        #
        # If fire is close enough to the center,
        # don't keep moving the servos.

        self.dead_zone = 20.0

        # Minimum confidence required for aiming.

        self.minimum_confidence = 0.50

        # =====================================================
        # AI SUBSCRIPTIONS
        # =====================================================

        self.detected_sub = self.create_subscription(
            Bool,
            '/fire/detected',
            self.detected_callback,
            10
        )

        self.class_sub = self.create_subscription(
            String,
            '/fire/class',
            self.class_callback,
            10
        )

        self.confidence_sub = self.create_subscription(
            Float32,
            '/fire/confidence',
            self.confidence_callback,
            10
        )

        self.center_x_sub = self.create_subscription(
            Float32,
            '/fire/center_x',
            self.center_x_callback,
            10
        )

        self.center_y_sub = self.create_subscription(
            Float32,
            '/fire/center_y',
            self.center_y_callback,
            10
        )
        self.action_sub = self.create_subscription(
            String,
            '/robot/action',
            self.action_callback,
            10
        )

        # =====================================================
        # SERVO OUTPUT
        # =====================================================

        self.servo_x_pub = self.create_publisher(
            Float32,
            '/aim/servo_x',
            10
        )

        self.servo_y_pub = self.create_publisher(
            Float32,
            '/aim/servo_y',
            10
        )

        self.aim_status_pub = self.create_publisher(
            String,
            '/aim/status',
            10
        )

        # =====================================================
        # TIMER
        # =====================================================

        self.timer = self.create_timer(
            0.1,
            self.update_aim
        )

        self.get_logger().info(
            'FireScout Aim Controller started.'
        )

    # =========================================================
    # CALLBACKS
    # =========================================================

    def detected_callback(self, msg):

        self.fire_detected = msg.data

    def class_callback(self, msg):

        self.fire_class = msg.data

    def confidence_callback(self, msg):

        self.confidence = msg.data

    def center_x_callback(self, msg):

        self.center_x = msg.data

    def center_y_callback(self, msg):

        self.center_y = msg.data
    def action_callback(self, msg):
        
        self.robot_action = msg.data.strip()    

    # =========================================================
    # CLAMP SERVO
    # =========================================================

    def clamp_servo(self, value):

        return max(
            0.0,
            min(180.0, value)
        )

    # =========================================================
    # AIMING LOGIC
    # =========================================================

    def update_aim(self):

        # -----------------------------------------------------
        # Robot must have a fire-related action before aiming
        # -----------------------------------------------------

        if self.robot_action not in [
            "APPROACH_FIRE",
            "FIRE_CONFIRMED"
        ]:
            self.publish_status("IDLE")
            return

        # -----------------------------------------------------
        # No fire detected
        # -----------------------------------------------------

        if not self.fire_detected:
            self.publish_status("IDLE")
            return

        # -----------------------------------------------------
        # Only aim at FIRE
        # -----------------------------------------------------

        if self.fire_class.lower() != "fire":

            self.publish_status(
                "TARGET_NOT_FIRE"
            )

            return

        # -----------------------------------------------------
        # Confidence check
        # -----------------------------------------------------

        if self.confidence < self.minimum_confidence:

            self.publish_status(
                "LOW_CONFIDENCE"
            )

            return

        # -----------------------------------------------------
        # Check coordinates
        # -----------------------------------------------------

        if self.center_x < 0 or self.center_y < 0:

            self.publish_status(
                "NO_TARGET_COORDINATES"
            )

            return

        # =====================================================
        # CALCULATE ERROR
        # =====================================================

        error_x = (
            self.center_x
            - self.image_center_x
        )

        error_y = (
            self.center_y
            - self.image_center_y
        )

        # =====================================================
        # X AXIS
        # =====================================================

        if abs(error_x) > self.dead_zone:

            if error_x < 0:

                # Fire is left.
                #
                # Increase/decrease this direction later
                # if the physical servo is mounted opposite.

                self.servo_x -= self.servo_step

            else:

                # Fire is right.

                self.servo_x += self.servo_step

        # =====================================================
        # Y AXIS
        # =====================================================

        if abs(error_y) > self.dead_zone:

            if error_y < 0:

                # Fire is above center.

                self.servo_y -= self.servo_step

            else:

                # Fire is below center.

                self.servo_y += self.servo_step

        # =====================================================
        # LIMIT SERVO POSITIONS
        # =====================================================

        self.servo_x = self.clamp_servo(
            self.servo_x
        )

        self.servo_y = self.clamp_servo(
            self.servo_y
        )

        # =====================================================
        # PUBLISH SERVO POSITIONS
        # =====================================================

        x_msg = Float32()
        x_msg.data = self.servo_x

        y_msg = Float32()
        y_msg.data = self.servo_y

        self.servo_x_pub.publish(x_msg)
        self.servo_y_pub.publish(y_msg)

        # =====================================================
        # AIM STATUS
        # =====================================================

        if (
            abs(error_x) <= self.dead_zone
            and
            abs(error_y) <= self.dead_zone
        ):

            status = "AIM_LOCKED"

        else:

            status = (
                f"AIMING | "
                f"ErrorX={error_x:.1f} "
                f"ErrorY={error_y:.1f}"
            )

        self.publish_status(status)

    # =========================================================
    # STATUS PUBLISHER
    # =========================================================

    def publish_status(self, status):

        msg = String()

        msg.data = (
            f"{status} | "
            f"X={self.servo_x:.1f} | "
            f"Y={self.servo_y:.1f} | "
            f"Target={self.center_x:.1f},"
            f"{self.center_y:.1f} | "
            f"Confidence={self.confidence:.2f}"
        )

        self.aim_status_pub.publish(msg)

        # Don't spam the terminal while idle.
        if status != "IDLE":

            self.get_logger().info(
                msg.data
            )


# =============================================================
# MAIN
# =============================================================

def main(args=None):

    rclpy.init(args=args)

    node = AimController()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        node.get_logger().info(
            'Aim controller stopped.'
        )

    finally:

        node.destroy_node()

        if rclpy.ok():

            rclpy.shutdown()


if __name__ == '__main__':

    main()