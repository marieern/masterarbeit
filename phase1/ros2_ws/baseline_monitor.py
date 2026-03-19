import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
import math
import time
import psutil

class BaselineMonitor(Node):
    def __init__(self):
        super().__init__('baseline_monitor')
        self.subscription = self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.start_time = None
        self.total_distance = 0.0
        self.last_pose = None
        self.cpu_usages = []
        self.is_running = False
        print("Monitoring bereit. Starte die Fahrt in RViz!")

    def odom_callback(self, msg):
        curr_pose = msg.pose.pose.position
        # Start-Trigger: Wenn sich der Roboter zum ersten Mal bewegt
        if not self.is_running and msg.twist.twist.linear.x > 0.01:
            self.is_running = True
            self.start_time = time.time()
            print("Fahrt detektiert! Erfasse Daten...")

        if self.is_running:
            # Weglänge berechnen: L = sum(sqrt((x_i - x_{i-1})^2 + (y_i - y_{i-1})^2))
            if self.last_pose:
                dist = math.sqrt((curr_pose.x - self.last_pose.x)**2 + (curr_pose.y - self.last_pose.y)**2)
                self.total_distance += dist
            self.last_pose = curr_pose
            self.cpu_usages.append(psutil.cpu_percent())

            # Stopp-Trigger: Wenn der Roboter das Ziel erreicht hat und steht
            if msg.twist.twist.linear.x < 0.001 and self.total_distance > 1.0:
                self.stop_monitoring()

    def stop_monitoring(self):
        duration = time.time() - self.start_time
        avg_cpu = sum(self.cpu_usages) / len(self.cpu_usages)
        print("\n--- TEST ERGEBNISSE ---")
        print(f"Zeitdauer: {duration:.2f} Sekunden")
        print(f"Weglänge: {self.total_distance:.2f} Meter")
        print(f"Durchschn. CPU-Last: {avg_cpu:.1f} %")
        rclpy.shutdown()

def main():
    rclpy.init()
    node = BaselineMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
