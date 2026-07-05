from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, TimerAction
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder
import os


def launch_setup(context, *args, **kwargs):
    urdf_full_path = os.path.join(
        get_package_share_directory("fanuc_tesollo_description"),
        "urdf",
        "fanuc_m20_tesollo.urdf.xacro",
    )

    moveit_config = (
        MoveItConfigsBuilder("fanuc_m20_tesollo", package_name="df3fb_moveit_config")
        .robot_description(file_path=urdf_full_path, mappings={})
        .robot_description_semantic(
            file_path="srdf/fanuc_m20_tesollo.srdf"
        )
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .planning_scene_monitor(
            publish_robot_description=True,
            publish_robot_description_semantic=True,
        )
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )

    ros2_controllers_path = PathJoinSubstitution(
        [FindPackageShare("df3fb_moveit_config"), "config", "ros2_controllers.yaml"]
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[
            moveit_config.robot_description,
            ros2_controllers_path,
        ],
        output="both",
    )

    spawn_jsb = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster", "--controller-manager", "/controller_manager"],
    )

    spawn_arm = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["fanuc_arm_controller", "--controller-manager", "/controller_manager"],
    )

    spawn_gripper = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["delto_controller", "--controller-manager", "/controller_manager"],
    )

    rsp_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[moveit_config.robot_description],
    )

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[moveit_config.to_dict()],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.planning_pipelines,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
        arguments=[
            "-d",
            PathJoinSubstitution(
                [FindPackageShare("df3fb_moveit_config"), "rviz", "moveit.rviz"]
            ),
        ],
    )

    scene_node = Node(
        package="df3fb_moveit_config",
        executable="setup_planning_scene.py",
        output="screen",
    )

    return [
        control_node,
        rsp_node,
        spawn_jsb,
        spawn_arm,
        spawn_gripper,
        move_group_node,
        rviz_node,
        TimerAction(period=3.0, actions=[scene_node]),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim",
                default_value="true",
                description="Mock ros2_control (no real Fanuc/gripper hardware)",
            ),
            OpaqueFunction(function=launch_setup),
        ]
    )
