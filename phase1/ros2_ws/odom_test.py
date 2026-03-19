import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import math

class OdomTest(Node):
    def __init__(self):
        super().__init__('odom_test')
        self.publisher_ = self.create_publisher(Twist, 'cmd_vel', 10)
        self.subscription = self.create_subscription(Odometry, 'odom', self.odom_callback, 10)
        self.start_x = None
        self.start_y = None
        self.distance_traveled = 0.0
        self.target_distance = 1.0  # Ziel: 1 Meter
        self.finished = False

    def odom_callback(self, msg):
        curr_x = msg.pose.pose.position.x
        curr_y = msg.pose.pose.position.y

        if self.start_x is None:
            self.start_x = curr_x
            self.start_y = curr_y
            return

        # Berechne die gefahrene Distanz (Euklidisch)
        self.distance_traveled = math.sqrt((curr_x - self.start_x)**2 + (curr_y - self.start_y)**2)
        
        if not self.finished:
            self.get_logger().info(f'Distanz laut Odom: {self.distance_traveled:.3f} m')

            if self.distance_traveled < self.target_distance:
                move_msg = Twist()
                move_msg.linear.x = 0.1  # Langsame Fahrt (0.1 m/s)
                self.publisher_.publish(move_msg)
            else:
                # Ziel erreicht, anhalten
                self.publisher_.publish(Twist())
                self.finished = True
                self.get_logger().info('--- TEST BEENDET: 1 Meter erreicht ---')
                self.get_logger().info('Prüfe jetzt in Gazebo die tatsächliche Position!')

def main(args=None):
    rclpy.init(args=args)
    node = OdomTest()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
