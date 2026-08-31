import sys
if sys.prefix == 'C:\\pixi_ws\\.pixi\\envs\\default':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = 'C:\\FireScout_ROS\\install\\firescout_robot'
