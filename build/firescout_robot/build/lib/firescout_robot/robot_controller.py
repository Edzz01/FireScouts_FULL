import rclpy

from rclpy.node import Node

from std_msgs.msg import String
from geometry_msgs.msg import Twist


class RobotController(Node):

    def __init__(self):

        super().__init__('robot_controller')

        # =====================================================
        # ROBOT MOTOR COMMAND
        # =====================================================

        self.cmd_pub = self.create_publisher(
            Twist,
            '/cmd_vel',
            10
        )

        # =====================================================
        # FIRE RESPONSE COMMAND
        # =====================================================

        self.action_sub = self.create_subscription(
            String,
            '/robot/action',
            self.action_callback,
            10
        )

        # Current action

        self.current_action = "SEARCH"

        self.get_logger().info(
            'FireScout Robot Controller started.'
        )

    # =========================================================
    # ACTION CALLBACK
    # =========================================================

    def action_callback(self, msg):

        action = msg.data.strip()

        self.current_action = action

        cmd = Twist()

        # =====================================================
        # SEARCH
        # =====================================================

        if action == "SEARCH":

            cmd.linear.x = 0.10
            cmd.angular.z = 0.25

            self.get_logger().info(
                'SEARCH -> rotating/searching'
            )

        # =====================================================
        # APPROACH FIRE
        # =====================================================

        elif action == "APPROACH_FIRE":

            cmd.linear.x = 0.25
            cmd.angular.z = 0.0

            self.get_logger().info(
                'APPROACH_FIRE -> moving toward fire'
            )

        # =====================================================
        # SEARCH FOR FIRE
        # =====================================================

        elif action == "SEARCH_FIRE":

            cmd.linear.x = 0.10
            cmd.angular.z = 0.30

            self.get_logger().info(
                'SEARCH_FIRE -> slow search'
            )

        # =====================================================
        # FIRE CONFIRMED
        # =====================================================

        elif action == "FIRE_CONFIRMED":

            cmd.linear.x = 0.0
            cmd.angular.z = 0.0

            self.get_logger().info(
                'FIRE_CONFIRMED -> ROBOT STOPPED'
            )

        # =====================================================
        # CAUTION
        # =====================================================

        elif action == "CAUTION":

            cmd.linear.x = 0.05
            cmd.angular.z = 0.20

            self.get_logger().info(
                'CAUTION -> slow movement'
            )

        # =====================================================
        # STOP
        # =====================================================

        else:

            cmd.linear.x = 0.0
            cmd.angular.z = 0.0

            self.get_logger().info(
                f'{action} -> ROBOT STOPPED'
            )

        # =====================================================
        # PUBLISH MOTOR COMMAND
        # =====================================================

        self.cmd_pub.publish(cmd)


# =============================================================
# MAIN
# =============================================================

def main(args=None):

    rclpy.init(args=args)

    node = RobotController()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        node.get_logger().info(
            'Robot controller stopped.'
        )

    finally:

        # Make sure motors stop.

        stop_cmd = Twist()

        node.cmd_pub.publish(stop_cmd)

        node.destroy_node()

        if rclpy.ok():

            rclpy.shutdown()


if __name__ == '__main__':

    main()