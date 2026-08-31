import random
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


class SensorNode(Node):
    def __init__(self):
        super().__init__('sensor_node')

        # Publishers
        self.distance_pub = self.create_publisher(Float32, '/sensor/distance', 10)
        self.temp_pub = self.create_publisher(Float32, '/sensor/temperature', 10)
        self.gas_pub = self.create_publisher(Float32, '/sensor/gas', 10)

        # Timer to publish sensor data every 1 second
        self.timer = self.create_timer(1.0, self.publish_sensor_data)

        # Baseline values
        self.sim_distance = 150.0  # cm
        self.sim_temp = 28.5       # °C
        self.sim_gas = 120.0       # PPM

        self.get_logger().info('FireScout Mock Sensor Node started publishing...')

    def publish_sensor_data(self):
        # Slightly fluctuate values to simulate real hardware reading noise
        self.sim_distance = max(10.0, min(300.0, self.sim_distance + random.uniform(-5.0, 5.0)))
        self.sim_temp = max(20.0, min(60.0, self.sim_temp + random.uniform(-0.2, 0.3)))
        self.sim_gas = max(50.0, min(500.0, self.sim_gas + random.uniform(-2.0, 2.0)))

        # Create Float32 messages
        dist_msg = Float32(data=round(self.sim_distance, 1))
        temp_msg = Float32(data=round(self.sim_temp, 1))
        gas_msg = Float32(data=round(self.sim_gas, 1))

        # Publish to topics
        self.distance_pub.publish(dist_msg)
        self.temp_pub.publish(temp_msg)
        self.gas_pub.publish(gas_msg)

        self.get_logger().info(
            f"Sensors Published | Distance: {dist_msg.data} cm | Temp: {temp_msg.data} °C | Gas: {gas_msg.data} PPM"
        )


def main(args=None):
    rclpy.init(args=args)
    node = SensorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()