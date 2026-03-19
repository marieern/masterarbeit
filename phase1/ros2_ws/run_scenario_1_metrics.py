#!/usr/bin/env python3
import time
import math
import psutil
import threading
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

# KONFIGURATION
GOAL_X = 4.97   # <-- Ersetzen mit deinem X-Wert vom Gabelstapler
GOAL_Y = 0.919  # <-- Ersetzen mit deinem Y-Wert vom Gabelstapler
GOAL_W = 1.0   # Ausrichtung
# ---------------------------------------------------

class MetricsMonitor(Node):
    def __init__(self):
        super().__init__('metrics_monitor')
        # Subscriber für Odometrie (Position)
        self.subscription = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10)
        
        self.total_distance = 0.0
        self.last_x = None
        self.last_y = None
        self.cpu_readings = []
        self.running = False

    def odom_callback(self, msg):
        # Berechnet die gefahrene Strecke
        if not self.running:
            return
            
        current_x = msg.pose.pose.position.x
        current_y = msg.pose.pose.position.y

        if self.last_x is not None:
            dx = current_x - self.last_x
            dy = current_y - self.last_y
            dist = math.sqrt(dx*dx + dy*dy)
            self.total_distance += dist
        
        self.last_x = current_x
        self.last_y = current_y

    def start_recording(self):
        self.running = True
        # Setze Startpunkt zurück (damit wir nicht den Sprung vom Start zählen)
        self.last_x = None 
        self.last_y = None
        self.total_distance = 0.0
        self.cpu_readings = []
        
        # Starte CPU Überwachung in separatem Thread
        self.cpu_thread = threading.Thread(target=self.record_cpu)
        self.cpu_thread.start()

    def stop_recording(self):
        self.running = False
        if hasattr(self, 'cpu_thread'):
            self.cpu_thread.join()

    def record_cpu(self):
        while self.running:
            # Misst die CPU-Last des gesamten Systems (Intervall 0.5s)
            cpu = psutil.cpu_percent(interval=0.5)
            self.cpu_readings.append(cpu)

    def get_results(self):
        avg_cpu = sum(self.cpu_readings) / len(self.cpu_readings) if self.cpu_readings else 0.0
        return self.total_distance, avg_cpu

def main():
    # 1. Initialisierung
    rclpy.init()
    
    # Navigator für Steuerbefehle
    navigator = BasicNavigator()
    
    # Monitor-Node für die Messdaten
    metrics_node = MetricsMonitor()

    # Metrics-Node in einem Thread spinnen lassen, 
    # damit er im Hintergrund Daten empfängt
    executor = rclpy.executors.MultiThreadedExecutor()
    executor.add_node(metrics_node)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()

    # Warten auf Nav2
    print("⏳ Warte auf Navigation...")
    navigator.waitUntilNav2Active()

    # 2. Ziel setzen
    goal_pose = PoseStamped()
    goal_pose.header.frame_id = 'map'
    goal_pose.header.stamp = navigator.get_clock().now().to_msg()
    goal_pose.pose.position.x = GOAL_X
    goal_pose.pose.position.y = GOAL_Y
    goal_pose.pose.orientation.w = GOAL_W

    print(f"🚀 START: Szenario 1 -> Fahrt zum Stapler ({GOAL_X}, {GOAL_Y})")
    
    # --- MESSUNG START ---
    start_time = time.time()
    metrics_node.start_recording()
    
    navigator.goToPose(goal_pose)

    # Schleife während der Fahrt
    i = 0
    while not navigator.isTaskComplete():
        i += 1
        feedback = navigator.getFeedback()
        if feedback and i % 5 == 0:
            print(f"   ...fahre (Restweg: {feedback.distance_remaining:.2f}m)")
            
        # Wenn es zu lange dauert (Timeout-Schutz, z.B. 120 sek)
        if time.time() - start_time > 120.0:
            navigator.cancelTask()
            
        time.sleep(1.0)

    # --- MESSUNG STOP ---
    end_time = time.time()
    metrics_node.stop_recording()
    
    # 3. Ergebnisse auswerten
    result = navigator.getResult()
    duration = end_time - start_time
    distance, avg_cpu = metrics_node.get_results()

    print("\n" + "="*40)
    if result == TaskResult.SUCCEEDED:
        print("✅ ZIEL ERREICHT!")
    else:
        print("❌ FAHRT NICHT ERFOLGREICH!")
    
    print("-" * 40)
    print(f"⏱️  Zeitdauer:      {duration:.2f} Sekunden")
    print(f"📏  Weglänge:       {distance:.2f} Meter")
    print(f"💻  CPU-Last (Ø):   {avg_cpu:.1f} %")
    print("="*40 + "\n")

    navigator.lifecycleShutdown()
    metrics_node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()