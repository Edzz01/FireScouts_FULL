import threading

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32, Float64

from flask import Flask, request, jsonify

app = Flask(__name__)
ros_node = None

class WebBridgeNode(Node):
    def __init__(self):
        super().__init__('web_bridge_node')

        # Publisher for Movement
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # State variables to hold the latest sensor telemetry
        self.latest_distance = 0.0
        self.latest_gas = 0.0
        self.latest_temperature = 0.0

        # Subscribers for Sensors (Assuming Float32 - if your simulator uses Float64, change these)
        self.create_subscription(Float32, '/sensor/distance', self.distance_callback, 10)
        self.create_subscription(Float32, '/sensor/gas', self.gas_callback, 10)
        self.create_subscription(Float32, '/sensor/temperature', self.temperature_callback, 10)

        self.get_logger().info('FireScout Web Bridge ROS 2 node started with Sensor Telemetry.')

    # Callbacks to update state when new messages arrive
    def distance_callback(self, msg):
        self.latest_distance = msg.data

    def gas_callback(self, msg):
        self.latest_gas = msg.data

    def temperature_callback(self, msg):
        self.latest_temperature = msg.data

    def send_velocity(self, linear_x, angular_z):
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)
        self.cmd_vel_pub.publish(msg)
        self.get_logger().info(f'Published /cmd_vel -> linear.x={linear_x}, angular.z={angular_z}')

def ros_spin_thread():
    global ros_node
    rclpy.init()
    ros_node = WebBridgeNode()
    rclpy.spin(ros_node)
    ros_node.destroy_node()
    rclpy.shutdown()


# --- HTTP ENDPOINTS ---

@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'online',
        'ros_node': ros_node is not None,
        'service': 'FireScout Web Bridge'
    })

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    """HTTP endpoint to serve the latest sensor telemetry to the Web App."""
    if ros_node is None:
        return jsonify({'error': 'ROS 2 node is not initialized'}), 500
        
    return jsonify({
        'distance': round(ros_node.latest_distance, 2),
        'gas': round(ros_node.latest_gas, 2),
        'temperature': round(ros_node.latest_temperature, 2)
    })

@app.route('/api/move', methods=['POST'])
def move_robot():
    if not request.is_json:
        return jsonify({'error': 'Request must be JSON'}), 400

    data = request.get_json()
    direction = data.get('direction', 'STOP').upper()
    linear_x, angular_z = 0.0, 0.0

    if direction == 'FORWARD':
        linear_x = 0.5
    elif direction == 'BACKWARD':
        linear_x = -0.5
    elif direction == 'LEFT':
        angular_z = 0.5
    elif direction == 'RIGHT':
        angular_z = -0.5
    elif direction == 'STOP':
        pass
    else:
        return jsonify({'error': f'Unknown direction: {direction}'}), 400

    if ros_node is None:
        return jsonify({'error': 'ROS 2 node is not initialized'}), 500

    ros_node.send_velocity(linear_x, angular_z)
    return jsonify({
        'status': 'success',
        'command': direction,
        'topic': '/cmd_vel'
    })

def main():
    ros_thread = threading.Thread(target=ros_spin_thread, daemon=True)
    ros_thread.start()

    print('\n========================================')
    print('       FireScout Web Bridge API')
    print('========================================')
    print('ROS 2: Starting')
    print('HTTP: http://127.0.0.1:5001\n')
    print('Endpoints:')
    print('GET  /api/status')
    print('GET  /api/sensors  <-- NEW')
    print('POST /api/move')
    print('========================================\n')

    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)

if __name__ == '__main__':
    main()