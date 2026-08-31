import rclpy
from rclpy.node import Node

from std_msgs.msg import Bool, Float32, String


class FireResponse(Node):

    def __init__(self):
        super().__init__('fire_response')

        # =====================================================
        # CURRENT SYSTEM STATE
        # =====================================================

        self.ai_fire_detected = False
        self.ai_class = "none"
        self.ai_confidence = 0.0

        self.temperature = 0.0
        self.gas = 0.0

        self.fire_status = "SAFE"

        # =====================================================
        # AI FIRE DETECTOR
        # =====================================================

        self.ai_detected_sub = self.create_subscription(
            Bool,
            '/fire/detected',
            self.ai_detected_callback,
            10
        )

        self.ai_class_sub = self.create_subscription(
            String,
            '/fire/class',
            self.ai_class_callback,
            10
        )

        self.ai_confidence_sub = self.create_subscription(
            Float32,
            '/fire/confidence',
            self.ai_confidence_callback,
            10
        )

        # =====================================================
        # SENSOR FIRE DECISION
        # =====================================================

        self.fire_status_sub = self.create_subscription(
            String,
            '/fire/status',
            self.fire_status_callback,
            10
        )

        # Direct sensor subscriptions
        self.temperature_sub = self.create_subscription(
            Float32,
            '/sensor/temperature',
            self.temperature_callback,
            10
        )

        self.gas_sub = self.create_subscription(
            Float32,
            '/sensor/gas',
            self.gas_callback,
            10
        )

        # =====================================================
        # ROBOT ACTION OUTPUT
        # =====================================================

        self.action_pub = self.create_publisher(
            String,
            '/robot/action',
            10
        )

        # =====================================================
        # FIRE RESPONSE STATUS
        # =====================================================

        self.response_pub = self.create_publisher(
            String,
            '/fire/response',
            10
        )

        # =====================================================
        # EVALUATION TIMER
        # =====================================================

        self.timer = self.create_timer(
            1.0,
            self.evaluate_response
        )

        self.get_logger().info(
            'FireScout Fire Response Coordinator started.'
        )

    # =========================================================
    # CALLBACKS
    # =========================================================

    def ai_detected_callback(self, msg):
        self.ai_fire_detected = msg.data

    def ai_class_callback(self, msg):
        self.ai_class = msg.data

    def ai_confidence_callback(self, msg):
        self.ai_confidence = msg.data

    def fire_status_callback(self, msg):
        self.fire_status = msg.data

    def temperature_callback(self, msg):
        self.temperature = msg.data

    def gas_callback(self, msg):
        self.gas = msg.data

    # =========================================================
    # FIRE RESPONSE LOGIC
    # =========================================================

    def evaluate_response(self):

        # -----------------------------------------------------
        # Determine whether AI has detected fire
        # -----------------------------------------------------

        strong_ai_fire = (
            self.ai_fire_detected
            and self.ai_class.lower() == "fire"
            and self.ai_confidence >= 0.50
        )

        # -----------------------------------------------------
        # Determine whether sensors indicate dangerous fire
        # -----------------------------------------------------

        strong_sensor_fire = (
            self.temperature >= 40.0
            and self.gas >= 600.0
        )

        sensor_warning = (
            self.temperature >= 35.0
            or self.gas >= 500.0
        )

        # =====================================================
        # RESPONSE DECISION
        # =====================================================

        if strong_ai_fire and strong_sensor_fire:

            action = "FIRE_CONFIRMED"
            response = (
                "FIRE CONFIRMED | "
                "AI + SENSOR AGREEMENT"
            )

        elif strong_ai_fire:

            action = "APPROACH_FIRE"
            response = (
                "AI FIRE DETECTED | "
                "Approach fire for confirmation"
            )

        elif strong_sensor_fire:

            action = "SEARCH_FIRE"
            response = (
                "SENSOR FIRE WARNING | "
                "Search for fire using camera"
            )

        elif sensor_warning:

            action = "CAUTION"
            response = (
                "WARNING | "
                "Elevated temperature or gas"
            )

        else:

            action = "SEARCH"
            response = "AREA SAFE | Continue searching"

        # =====================================================
        # PUBLISH ROBOT ACTION
        # =====================================================

        action_msg = String()
        action_msg.data = action

        self.action_pub.publish(action_msg)

        # =====================================================
        # PUBLISH FIRE RESPONSE
        # =====================================================

        response_msg = String()
        response_msg.data = (
            f"{response} | "
            f"AI={self.ai_class} "
            f"{self.ai_confidence:.2f} | "
            f"Temp={self.temperature:.1f}C | "
            f"Gas={self.gas:.1f}"
        )

        self.response_pub.publish(response_msg)

        # =====================================================
        # TERMINAL OUTPUT
        # =====================================================

        self.get_logger().info(
            f"ACTION: {action} | "
            f"AI: {self.ai_class} "
            f"{self.ai_confidence:.2f} | "
            f"Temp: {self.temperature:.1f} C | "
            f"Gas: {self.gas:.1f}"
        )


def main(args=None):

    rclpy.init(args=args)

    node = FireResponse()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        node.get_logger().info(
            'Fire response coordinator stopped.'
        )

    finally:

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()