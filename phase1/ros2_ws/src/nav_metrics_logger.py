#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry, Path
from sensor_msgs.msg import LaserScan
from nav2_msgs.msg import BehaviorTreeLog
import numpy as np
import csv
import time
import math
from tf_transformations import euler_from_quaternion

class NavMetricsLogger(Node):
    def __init__(self):
        super().__init__('nav_metrics_logger')

        # Parameter & Speicher
        self.declare_parameter('csv_name', 'nav_test_log.csv')
        self.filename = self.get_parameter('csv_name').get_parameter_value().string_value
        
        # Metriken
        self.start_time = None
        self.total_distance = 0.0
        self.total_rotation = 0.0
        self.max_speed = 0.0
        self.speeds = []
        self.min_obstacle_dist = float('inf')
        self.recovery_count = 0
        self.last_pos = None
        self.last_yaw = None
        self.global_path = None
        self.cross_track_errors = []
        
        # Subscriptions
        self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        self.create_subscription(Path, '/plan', self.plan_callback, 10)
        self.create_subscription(BehaviorTreeLog, '/behavior_tree_log', self.bt_callback, 10)

        # CSV Header schreiben
        with open(self.filename, mode='w') as f:
            writer = csv.writer(f)
            writer.writerow(['Timestamp', 'Distanz_m', 'Rotation_deg', 'Speed_ms', 'Min_Scan_m', 'CT_Error_m', 'Recoveries'])

        self.timer = self.create_timer(0.5, self.log_to_csv) # Alle 0.5s loggen
        self.get_logger().info(f'Logging gestartet. Datei: {self.filename}')

    def odom_callback(self, msg):
        if self.start_time is None:
            self.start_time = self.get_clock().now()

        curr_pos = msg.pose.pose.position
        curr_speed = msg.twist.twist.linear.x
        
        # 1. Pfadlänge berechnen
        if self.last_pos is not None:
            dist = math.sqrt((curr_pos.x - self.last_pos.x)**2 + (curr_pos.y - self.last_pos.y)**2)
            self.total_distance += dist
        self.last_pos = curr_pos

        # 2. Geschwindigkeit messen
        self.speeds.append(curr_speed)
        if abs(curr_speed) > self.max_speed:
            self.max_speed = abs(curr_speed)

        # 3. Gesamtdrehung (Rotation)
        q = msg.pose.pose.orientation
        _, _, yaw = euler_from_quaternion([q.x, q.y, q.z, q.w])
        if self.last_yaw is not None:
            diff = abs(yaw - self.last_yaw)
            if diff > math.pi: diff = abs(diff - 2*math.pi) # Überlauf korrigieren
            self.total_rotation += math.degrees(diff)
        self.last_yaw = yaw

        # 4. Cross-Track Error (Abweichung vom Pfad)
        if self.global_path is not None and len(self.global_path.poses) > 0:
            dists = [math.sqrt((curr_pos.x - p.pose.position.x)**2 + (curr_pos.y - p.pose.position.y)**2) 
                     for p in self.global_path.poses]
            self.cross_track_errors.append(min(dists))

    def scan_callback(self, msg):
        # 5. Min Distanz zu Hindernissen
        valid_ranges = [r for r in msg.ranges if r > msg.range_min]
        if valid_ranges:
            m = min(valid_ranges)
            if m < self.min_obstacle_dist:
                self.min_obstacle_dist = m

    def plan_callback(self, msg):
        self.global_path = msg

    def bt_callback(self, msg):
        # 6. Recovery Behaviors zählen (Spin, Wait, BackUp)
        for event in msg.event_log:
            if "NavigateToPose" not in event.node_name and event.current_status == "RUNNING":
                if any(x in event.node_name for x in ["Spin", "Wait", "BackUp"]):
                    self.recovery_count += 1
                    self.get_logger().warn(f'Recovery erkannt: {event.node_name}')

    def log_to_csv(self):
        if self.start_time is None: return
        
        ts = (self.get_clock().now() - self.start_time).nanoseconds / 1e9
        ct_error = self.cross_track_errors[-1] if self.cross_track_errors else 0.0
        curr_speed = self.speeds[-1] if self.speeds else 0.0

        with open(self.filename, mode='a') as f:
            writer = csv.writer(f)
            writer.writerow([round(ts, 2), round(self.total_distance, 2), round(self.total_rotation, 2), 
                             round(curr_speed, 2), round(self.min_obstacle_dist, 2), 
                             round(ct_error, 3), self.recovery_count])

    def print_summary(self):
        self.get_logger().info("\n" + "="*30 + 
            f"\nTEST-ZUSAMMENFASSUNG:\n" +
            f"Zeit: {len(self.speeds)*0.1:.1f}s\n" +
            f"Strecke: {self.total_distance:.2f}m\n" +
            f"Max Speed: {self.max_speed:.2f}m/s\n" +
            f"Ø Abweichung: {np.mean(self.cross_track_errors) if self.cross_track_errors else 0:.3f}m\n" +
            f"Min Hindernisabstand: {self.min_obstacle_dist:.2f}m\n" +
            f"Anzahl Recoveries: {self.recovery_count}\n" +
            "="*30)

def main():
    rclpy.init()
    node = NavMetricsLogger()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.print_summary()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
