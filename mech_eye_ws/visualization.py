import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from plyfile import PlyData


ply_data = PlyData.read("./mech_eye_ws/temp_dwnld/point_cloud.ply")

vertex = ply_data['vertex']
x = np.array(vertex['x'])
y = np.array(vertex['y'])
z = np.array(vertex['z'])




step = 100 
x_sub = x[::step]
y_sub = y[::step]
z_sub = z[::step]
# 2. Set up the matplotlib figure and 3D axis



colors = None
if 'red' in vertex and 'green' in vertex and 'blue' in vertex:
    r = np.array(vertex['red'][::step]) / 255.0
    g = np.array(vertex['green'][::step]) / 255.0
    b = np.array(vertex['blue'][::step]) / 255.0
    colors = np.vstack((r, g, b)).T
else:
    colors = z_sub



    
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')



# 3. Plot the point cloud
# 'c' colors the points by their Z-value for better depth perception
if isinstance(colors, np.ndarray):
    ax.scatter(x_sub, y_sub, z_sub, c=colors, s=0.5, marker='.')
else:
    ax.scatter(x_sub, y_sub, z_sub, c=colors, cmap='jet', s=0.5, marker='.')
# 4. Add a colorbar and labels
# plt.colorbar(sc, ax=ax, label='Z depth', pad=0.1)
ax.set_xlabel('X Axis')
ax.set_ylabel('Y Axis')
ax.set_zlabel('Z Axis')
ax.set_title('3D Point Cloud Visualization')

# 5. Optimize view angle and aspect ratio
ax.view_init(elev=20, azim=45)  # Change perspective
ax.set_box_aspect([1,1,1])       # Keeps the aspect ratio equal

# Show the interactive window
plt.show()