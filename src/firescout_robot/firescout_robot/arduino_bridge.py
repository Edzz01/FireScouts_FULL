import threading

import rclpy
import serial

from rclpy.node import Node

from geometry_msgs.msg import Twist
from std_msgs.msg import Float32


class ArduinoBridgeNode(Node):

    def __init__(self):
        super().__init__('arduino_bridge')

        # =====================================================
        # SERIAL CONNECTION
        # =====================================================

        self.declare_parameter('port', 'COM4')
        self.declare_parameter('baud', 115200)

        port = self.get_parameter('port').value
        baud = self.get_parameter('baud').value

        self.serial_lock = threading.Lock()

        try:
            self.arduino = serial.Serial(
                port,
                baud,
                timeout=1.0
            )

        except serial.SerialException as e:
            self.get_logger().error(
                f'Could not open {port}: {e}'
            )
            raise

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
        # SENSOR STATE
        # =====================================================

        self.temperature = 0.0
        self.gas = 0.0

        self.ultrasonic_1 = None
        self.ultrasonic_2 = None

        # =====================================================
        # MOTOR SETTINGS
        # =====================================================

        self.max_pwm = 255

        self.speed_scale = 360.0

        # =====================================================
        # SENSOR TELEMETRY OUTPUT
        # =====================================================

        # MLX90614 temperature
        self.temperature_pub = self.create_publisher(
            Float32,
            '/sensor/temperature',
            10
        )

        # MQ-2 gas
        self.gas_pub = self.create_publisher(
            Float32,
            '/sensor/gas',
            10
        )

        # Nearest ultrasonic distance
        self.distance_pub = self.create_publisher(
            Float32,
            '/sensor/distance',
            10
        )

        # =====================================================
        # ROS SUBSCRIPTIONS
        # =====================================================

        # -----------------------------------------------------
        # Motor command
        # -----------------------------------------------------

        self.cmd_vel_sub = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )

        # -----------------------------------------------------
        # Horizontal aiming servo
        # -----------------------------------------------------

        self.servo_x_sub = self.create_subscription(
            Float32,
            '/aim/servo_x',
            self.servo_x_callback,
            10
        )

        # -----------------------------------------------------
        # Vertical aiming servo
        # -----------------------------------------------------

        self.servo_y_sub = self.create_subscription(
            Float32,
            '/aim/servo_y',
            self.servo_y_callback,
            10
        )

        # -----------------------------------------------------
        # Extinguisher servo
        # -----------------------------------------------------

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

        # =====================================================
        # SERIAL READER THREAD
        # =====================================================

        self.reader_running = True

        self.reader_thread = threading.Thread(
            target=self.read_serial_loop,
            daemon=True
        )

        self.reader_thread.start()

        # =====================================================
        # STARTUP
        # =====================================================

        self.get_logger().info(
            f'FireScout Arduino Mega Bridge started '
            f'on {port} @ {baud}.'
        )

        self.get_logger().info(
            'Motors + X/Y aiming servos + '
            'extinguisher servo + MLX90614 + '
            'MQ-2 + ultrasonic sensors ready.'
        )

    # =========================================================
    # SERIAL WRITE
    # =========================================================

    def send_serial(self, payload):

        with self.serial_lock:

            try:
                self.arduino.write(
                    (payload + '\n').encode('ascii')
                )

            except serial.SerialException as e:

                self.get_logger().error(
                    f'Serial write failed: {e}'
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

        serial_payload = (
            f'M,{left_speed},{right_speed}'
        )

        self.send_serial(serial_payload)

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

        self.send_serial(serial_payload)

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

        self.send_serial(serial_payload)

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

        self.send_serial(serial_payload)

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
    # SERIAL READ / TELEMETRY
    # =========================================================

    def read_serial_loop(self):

        last_u1 = None
        last_u2 = None

        while self.reader_running and rclpy.ok():

            try:

                line = self.arduino.readline().decode(
                    'ascii',
                    errors='ignore'
                ).strip()

            except serial.SerialException as e:

                self.get_logger().error(
                    f'Serial read failed: {e}'
                )

                continue

            if not line:
                continue

            parts = line.split(',')

            tag = parts[0].strip().upper()

            try:

                # =================================================
                # MLX90614 TEMPERATURE
                # Arduino format:
                #
                # T,42.5
                # =================================================

                if tag == 'T' and len(parts) == 2:

                    temperature = float(parts[1])

                    self.temperature = temperature

                    msg = Float32()

                    msg.data = temperature

                    self.temperature_pub.publish(msg)

                # =================================================
                # MQ-2 GAS
                # Arduino format:
                #
                # G,650
                # =================================================

                elif tag == 'G' and len(parts) == 2:

                    gas = float(parts[1])

                    self.gas = gas

                    msg = Float32()

                    msg.data = gas

                    self.gas_pub.publish(msg)

                # =================================================
                # ULTRASONIC SENSOR 1
                #
                # U1,85.0
                # =================================================

                elif tag == 'U1' and len(parts) == 2:

                    last_u1 = float(parts[1])

                    self.ultrasonic_1 = last_u1

                    self.publish_nearest_distance(
                        last_u1,
                        last_u2
                    )

                # =================================================
                # ULTRASONIC SENSOR 2
                #
                # U2,120.0
                # =================================================

                elif tag == 'U2' and len(parts) == 2:

                    last_u2 = float(parts[1])

                    self.ultrasonic_2 = last_u2

                    self.publish_nearest_distance(
                        last_u1,
                        last_u2
                    )

            except ValueError:

                self.get_logger().warn(
                    f'Bad telemetry line: {line}'
                )

    # =========================================================
    # DISTANCE
    # =========================================================

    def publish_nearest_distance(
        self,
        u1,
        u2
    ):

        readings = [
            d
            for d in (u1, u2)
            if d is not None and d >= 0
        ]

        if not readings:
            return

        msg = Float32()

        msg.data = min(readings)

        self.distance_pub.publish(msg)

    # =========================================================
    # STATUS
    # =========================================================

    def publish_status(self):

        self.get_logger().info(
            f'ARDUINO STATE | '
            f'Motors L={self.left_motor} '
            f'R={self.right_motor} | '
            f'Temp={self.temperature:.1f}C | '
            f'Gas={self.gas:.1f} | '
            f'Distance='
            f'{self.get_distance_text()} | '
            f'Aim X={self.servo_x:.1f}° '
            f'Y={self.servo_y:.1f}° | '
            f'Extinguisher='
            f'{self.extinguisher_servo:.1f}°'
        )

    # =========================================================
    # DISTANCE STATUS TEXT
    # =========================================================

    def get_distance_text(self):

        readings = [
            d
            for d in (
                self.ultrasonic_1,
                self.ultrasonic_2
            )
            if d is not None and d >= 0
        ]

        if not readings:
            return 'N/A'

        return f'{min(readings):.1f}cm'

    # =========================================================
    # SHUTDOWN
    # =========================================================

    def destroy_node(self):

        self.reader_running = False

        # -----------------------------------------------------
        # Stop motors and release extinguisher before closing
        # serial connection.
        # -----------------------------------------------------

        try:

            with self.serial_lock:

                self.arduino.write(
                    b'M,0,0\n'
                )

                self.arduino.write(
                    b'E,0\n'
                )

        except Exception:
            pass

        try:

            self.arduino.close()

        except Exception:
            pass

        super().destroy_node()


# =============================================================
# MAIN
# =============================================================

def main(args=None):

    rclpy.init(args=args)

    node = None

    try:

        node = ArduinoBridgeNode()

        rclpy.spin(node)

    except KeyboardInterrupt:

        if node is not None:

            node.get_logger().info(
                'Arduino bridge stopped.'
            )

    finally:

        if node is not None:

            node.destroy_node()

        if rclpy.ok():

            rclpy.shutdown()


if __name__ == '__main__':
    main()