/joint_states publisher

using sensor_msgs/msg/JointState


publish 

finger1_joint1
finger1_joint2
finger1_joint3
finger1_joint4

finger2_joint1
finger2_joint2
finger2_joint3
finger2_joint4

finger3_joint1
finger3_joint2
finger3_joint3
finger3_joint4


subscriber -> /gripper_target using -> std_msgs/msg/Float64MultiArray ex [-5,-2.3,62,69,
 -60,-1.6,57.5,69.2,
 60,-2.3,54.8,68.4]


callback -> self.gripper.update_target(msg.data)


services /open /close /home /hold /release 


gripper_action_server.py -> control_msgs/action/GripperCommand

goal float64[12] target

Feedback float64[12] current_position

Result bool success


execution -> /
self.gripper.update_target(goal.target)

while not reached:
    publish_feedback()

return result