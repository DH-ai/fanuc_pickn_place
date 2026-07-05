#!/usr/bin/env python3
"""Populate the MoveIt planning scene with table and pick-place workspace objects."""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose
from moveit_msgs.msg import CollisionObject, PlanningScene
from shape_msgs.msg import SolidPrimitive


def _box(name, frame, x, y, z, sx, sy, sz):
    obj = CollisionObject()
    obj.header.frame_id = frame
    obj.id = name
    primitive = SolidPrimitive()
    primitive.type = SolidPrimitive.BOX
    primitive.dimensions = [sx, sy, sz]
    pose = Pose()
    pose.position.x = x
    pose.position.y = y
    pose.position.z = z
    pose.orientation.w = 1.0
    obj.primitives.append(primitive)
    obj.primitive_poses.append(pose)
    obj.operation = CollisionObject.ADD
    return obj


class PlanningSceneSetup(Node):
    def __init__(self):
        super().__init__("setup_planning_scene")
        self.pub = self.create_publisher(PlanningScene, "/planning_scene", 10)
        self.timer = self.create_timer(2.0, self._publish_once)
        self.sent = False

    def _publish_once(self):
        if self.sent:
            return
        self.sent = True
        self.timer.cancel()

        scene = PlanningScene()
        scene.is_diff = True
        scene.world.collision_objects.extend(
            [
                _box("table", "world", 0.75, 0.0, 0.375, 1.5, 1.0, 0.75),
                _box("pick_bin", "world", 0.45, -0.35, 0.82, 0.35, 0.35, 0.04),
                _box("place_bin", "world", 0.45, 0.35, 0.82, 0.35, 0.35, 0.04),
                _box("object_circle", "world", 0.45, -0.35, 0.87, 0.06, 0.06, 0.03),
                _box("object_triangle", "world", 0.45, 0.0, 0.87, 0.07, 0.07, 0.03),
                _box("object_heart", "world", 0.45, 0.35, 0.87, 0.08, 0.08, 0.03),
            ]
        )
        self.pub.publish(scene)
        self.get_logger().info("Planning scene updated (table + bins + objects)")


def main():
    rclpy.init()
    node = PlanningSceneSetup()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
