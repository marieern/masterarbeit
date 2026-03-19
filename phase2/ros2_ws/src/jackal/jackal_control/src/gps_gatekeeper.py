#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseWithCovarianceStamped, Twist, PoseStamped
from robot_localization.srv import SetPose
from nav2_msgs.srv import ClearEntireCostmap
from std_srvs.srv import Empty

from rclpy.action import ActionClient
from nav2_msgs.action import NavigateToPose, NavigateThroughPoses
from action_msgs.srv import CancelGoal

from tf2_ros import TransformListener, Buffer
from rclpy.qos import qos_profile_sensor_data
import rclpy.time
import math

# TRIGGER_X: x-Koordinate, ab der die Transition eingeleitet wird (ca. 2m vor dem physischen Tor)
TRIGGER_X = 11.0          
# ENTRY_KOORDINATEN: Definierte Eintrittspose für den Hard-Reset zur Vermeidung von GNSS-Multipath-Fehlern
ENTRY_X = 11.0            
ENTRY_Y = -0.257         
ENTRY_Q_Z = 0.983        
ENTRY_Q_W = -0.186       

class HybridManager(Node):
    """
    Gatekeeper-Modul: Orchestriert den hybriden Wechsel zwischen GNSS- (Outdoor) 
    und LiDAR/AMCL-basierter (Indoor) Navigation. Fungiert als Datenweiche und 
    Zustandsüberwacher, um EKF-Sprünge an Gebäudeübergängen abzufangen.
    """
    def __init__(self):
        super().__init__('hybrid_manager')
        self.get_logger().info('Hybrid Manager V25: Timer Tracking & No Spin-Filter')
        
        # TF-Buffer zur kontinuierlichen Abfrage der aktuellen Roboterpose (map -> base_link)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        # Zustandsvariablen für die Transitionslogik
        self.is_inside = None 
        self.spin_timer = None
        self.spin_start_time = None
        self.settle_timer = None
        self.indoor_trigger_time = None
        self.last_valid_x = None

        # Nav2 Action Clients
        # Werden genutzt, um die aktive Navigation während der Transition zu pausieren und nach erfolgreichem Hard-Reset mit einem Orientierungspunkt fortzusetzen
        self.latest_goal = None
        self.sub_goal = self.create_subscription(PoseStamped, '/goal_pose', self.goal_callback, 10)
        self.nav_through_client = ActionClient(self, NavigateThroughPoses, 'navigate_through_poses')
        self.cancel_through_client = self.create_client(CancelGoal, '/navigate_through_poses/_action/cancel_goal')
        self.cancel_nav_client = self.create_client(CancelGoal, '/navigate_to_pose/_action/cancel_goal')

        # Publishers (Daten OUT)
        self.pub_amcl_init = self.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
        self.pub_amcl_filtered = self.create_publisher(PoseWithCovarianceStamped, '/amcl_pose_filtered', 10)
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_rear_filtered = self.create_publisher(LaserScan, '/scan_rear_filtered', 10)
        self.pub_gps_final = self.create_publisher(Odometry, '/odometry/gps', 10)

        # Subscribers (Daten IN)
        self.sub_amcl = self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.amcl_callback, 10)
        self.sub_rear = self.create_subscription(LaserScan, '/scan_rear', self.rear_callback, qos_profile_sensor_data)
        self.sub_gps_raw = self.create_subscription(Odometry, '/odometry/gps_raw', self.gps_raw_callback, qos_profile_sensor_data)

        # Service Clients (Systemeingriffe)
        self.ekf_set_pose_client = self.create_client(SetPose, '/ekf_filter_node_map/set_pose')
        self.clear_global = self.create_client(ClearEntireCostmap, '/global_costmap/clear_entirely_global_costmap')
        self.clear_local = self.create_client(ClearEntireCostmap, '/local_costmap/clear_entirely_local_costmap')
        self.nomotion_client = self.create_client(Empty, '/request_nomotion_update')

        # TIMER STATT GPS
        # Entkoppelt die Positionsprüfung vom GPS-Signal. Garantiert eine deterministische 
        # Überwachung (10 Hz) der Koordinaten, selbst wenn das GNSS-Signal im Gebäude abbricht.
        self.check_timer = self.create_timer(0.1, self.check_location)

    def goal_callback(self, msg):
        self.latest_goal = msg

    # DATEN-WEICHEN (Routing-Logik): Blockieren Sensoren je nach Navigationszone
    def rear_callback(self, msg):
        # Heck-Scanner nur indoor aktivieren, um Costmap outdoor sauber zu halten
        if self.is_inside is True: self.pub_rear_filtered.publish(msg)

    def gps_raw_callback(self, msg):
        # GNSS-Datenstrom kappen, sobald der Roboter in die Halle fährt
        if self.is_inside is False or self.is_inside is None: self.pub_gps_final.publish(msg)

    def amcl_callback(self, msg):
        # AMCL-Korrektursprünge blockieren, während der Roboter outdoor per GNSS navigiert
        if self.is_inside is True: self.pub_amcl_filtered.publish(msg)


    # KERN-LOGIK: Überwachung und Transition
    def check_location(self):
        if not self.tf_buffer.can_transform('map', 'base_link', rclpy.time.Time(), timeout=rclpy.duration.Duration(seconds=0.05)):
            return 
        try:
            trans = self.tf_buffer.lookup_transform('map', 'base_link', rclpy.time.Time())
            curr_x = trans.transform.translation.x
            
            # ANTI-TELEPORTATIONS-FILTER (Glitch-Erkennung)
            # Verhindert, dass fehlerhafte, asynchrone Sprünge im EKF (z.B. durch Signalreflexionen) versehentlich eine Transition auslösen
            if self.last_valid_x is not None:
                if abs(curr_x - self.last_valid_x) > 3.0:
                    self.get_logger().warn(f'EKF Glitch detected! ({self.last_valid_x:.2f} -> {curr_x:.2f}). Ignoring.')
                    return
            self.last_valid_x = curr_x

            # Bestimmt beim Start des Skripts, in welcher Zone sich der Roboter befindet
            if self.is_inside is None:
                if curr_x < TRIGGER_X:
                    self.is_inside = True
                    self.get_logger().info(f'Init: Started INDOOR (x={curr_x:.2f})')
                else:
                    self.is_inside = False
                    self.get_logger().info(f'Init: Started OUTDOOR (x={curr_x:.2f})')
                return

            # INDOOR TRANSITION
            if not self.is_inside:
                if 8.0 < curr_x < TRIGGER_X: 
                    # 1-Sekunde Puffer: Stellt sicher, dass die Grenze physisch überschritten 
                    # wird und es sich nicht um ein temporäres Signalrauschen handelt.
                    if self.indoor_trigger_time is None:
                        self.indoor_trigger_time = self.get_clock().now()
                    else:
                        elapsed = (self.get_clock().now() - self.indoor_trigger_time).nanoseconds / 1e9
                        if elapsed > 1.0:
                            self.switch_to_indoor()
                            self.indoor_trigger_time = None
                else:
                    self.indoor_trigger_time = None
            else:
                # OUTDOOR HYSTERESE 
                # Schaltet erst auf GNSS um, wenn x = 13.0 überschritten wird (+ 2.0m Puffer).
                # Verhindert instabiles Umschalten (Chattering) direkt an der Gebäudekante.
                if curr_x > (TRIGGER_X + 2.0): 
                    self.switch_to_outdoor()
                
        except Exception as e:
            pass

 
    # TRANSITIONS-ROUTINEN (Hard-Reset und Wiederanlauf)
    def switch_to_indoor(self):
        self.get_logger().info('>>> SWITCHING TO INDOOR: Pausing Nav2 & Re-aligning')
        self.is_inside = True
        
        # 1. Stoppt jegliche dynamische Einflüsse
        self.cancel_current_nav_goal()
        self.stop_robot()
        
        # 2. Hard-Reset der Koordinaten zur Eliminierung der GNSS-Ungenauigkeit
        self.send_entry_pose_to_amcl()
        self.call_ekf_set_pose()
        
        # 3. Bereinigung der Costmaps von temporären Sensor-Artefakten
        self.clear_costmaps()
        
        self.get_logger().info('Forcing AMCL to align with walls...')
        self.update_count = 0
        
        # 4. Startet Settle-Timer für die statische Konvergenz der Partikelwolke
        self.settle_timer = self.create_timer(0.5, self.settle_timer_callback)

    def settle_timer_callback(self):
        # Erzwingt asynchrone AMCL-Updates ohne physische Roboterbewegung
        if self.update_count < 4:
            if self.nomotion_client.wait_for_service(timeout_sec=0.1):
                self.nomotion_client.call_async(Empty.Request())
            self.update_count += 1
        else:
            self.get_logger().info('AMCL alignment complete. Resuming Nav2 directly.')
            self.resume_nav_goal()
            self.settle_timer.cancel()
            self.settle_timer = None

    def switch_to_outdoor(self):
        self.get_logger().info('<<< SWITCHING TO OUTDOOR: GPS Active')
        self.is_inside = False
        self.clear_costmaps()
        if self.spin_timer is not None:
            self.spin_timer.cancel()
            self.spin_timer = None

    def cancel_current_nav_goal(self):
        req = CancelGoal.Request()
        if self.cancel_nav_client.wait_for_service(timeout_sec=0.5):
            self.cancel_nav_client.call_async(req)
        if self.cancel_through_client.wait_for_service(timeout_sec=0.5):
            self.cancel_through_client.call_async(req)

    def resume_nav_goal(self):
        # Generiert eine Wegpunkt-Liste (Via-Points), um das Jackal UGV sicher durch die schmale Tor-Passage zu führen, bevor das eigentliche Ziel anvisiert wird
        if self.latest_goal is not None:
            self.get_logger().info('Resuming Nav2 with alignment waypoint...')
            if self.nav_through_client.wait_for_server(timeout_sec=2.0):
                goal_msg = NavigateThroughPoses.Goal()
                waypoint = PoseStamped()
                waypoint.header.frame_id = 'map'
                waypoint.header.stamp = self.get_clock().now().to_msg()
                waypoint.pose.position.x = 10.0  
                waypoint.pose.position.y = 0.0   
                waypoint.pose.orientation.z = 1.0
                waypoint.pose.orientation.w = 0.0
                goal_msg.poses = [waypoint, self.latest_goal]
                self.nav_through_client.send_goal_async(goal_msg)
        else:
            self.get_logger().info('No previous goal saved. Standing by.')

    def get_hardcoded_gate_pose(self):
        from geometry_msgs.msg import Pose
        p = Pose()
        p.position.x = ENTRY_X
        p.position.y = ENTRY_Y
        p.position.z = 0.0
        mag = math.sqrt(ENTRY_Q_Z**2 + ENTRY_Q_W**2)
        p.orientation.x = 0.0
        p.orientation.y = 0.0
        p.orientation.z = ENTRY_Q_Z / mag
        p.orientation.w = ENTRY_Q_W / mag
        return p

    def send_entry_pose_to_amcl(self):
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.pose.pose = self.get_hardcoded_gate_pose()
        cov = [0.0] * 36
        cov[0] = 0.5; cov[7] = 0.5; cov[14] = 0.01; cov[21] = 0.01; cov[28] = 0.01; cov[35] = 0.5  
        msg.pose.covariance = cov
        self.pub_amcl_init.publish(msg)

    def call_ekf_set_pose(self):
        if not self.ekf_set_pose_client.wait_for_service(timeout_sec=1.0): return
        req = SetPose.Request()
        req.pose.header.stamp = self.get_clock().now().to_msg()
        req.pose.header.frame_id = 'map'
        req.pose.pose.pose = self.get_hardcoded_gate_pose()
        req.pose.pose.covariance = [0.2] * 36 
        self.ekf_set_pose_client.call_async(req)

    def stop_robot(self):
        self.pub_cmd_vel.publish(Twist())

    def clear_costmaps(self):
        if self.clear_global.service_is_ready():
            self.clear_global.call_async(ClearEntireCostmap.Request())
        if self.clear_local.service_is_ready():
            self.clear_local.call_async(ClearEntireCostmap.Request())

def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(HybridManager())
    rclpy.shutdown()

if __name__ == '__main__': main()
