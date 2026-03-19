import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from geometry_msgs.msg import PoseWithCovarianceStamped
import math
import transforms3d # Falls nicht installiert: pip install transforms3d

class YawOffsetFinder(Node):
    def __init__(self):
        super().__init__('yaw_offset_finder')
        
        # Subscriptions
        self.imu_sub = self.create_subscription(Imu, '/imu', self.imu_callback, 10)
        self.amcl_sub = self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.amcl_callback, 10)
        
        self.current_imu_yaw = None
        self.current_amcl_yaw = None

        self.get_logger().info('Bewege den Roboter in Gazebo kurz vorwärts, bis AMCL stabil ist...')

    def quaternion_to_yaw(self, q):
        # Konvertiert Quaternion zu Euler-Yaw
        _, _, yaw = transforms3d.euler.quat2euler([q.w, q.x, q.y, q.z])
        return yaw

    def imu_callback(self, msg):
        self.current_imu_yaw = self.quaternion_to_yaw(msg.orientation)
        self.check_and_calculate()

    def amcl_callback(self, msg):
        self.current_amcl_yaw = self.quaternion_to_yaw(msg.pose.pose.orientation)
        self.check_and_calculate()

    def check_and_calculate(self):
        if self.current_imu_yaw is not None and self.current_amcl_yaw is not None:
            # Berechnung: Offset = AMCL_Yaw - IMU_Yaw
            offset = self.current_amcl_yaw - self.current_imu_yaw
            
            # Normalisierung auf -Pi bis Pi
            while offset > math.pi: offset -= 2.0 * math.pi
            while offset < -math.pi: offset += 2.0 * math.pi

            self.get_logger().info(f'\n--- GEFUNDENER YAW_OFFSET ---\n'
                                   f'Radiant: {offset:.6f}\n'
                                   f'Grad:    {math.degrees(offset):.2f}°\n'
                                   f'----------------------------')

def main(args=None):
    rclpy.init(args=args)
    node = YawOffsetFinder()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()