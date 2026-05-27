echo Installing and configuring git-lfs
sudo apt install git-lfs
git lfs install

echo Checking out GitHub repositories
mkdir ~/ws_fanuc/src -p
cd ~/ws_fanuc/src
git clone https://github.com/FANUC-CORPORATION/fanuc_description.git
git clone --branch humble --single-branch --recurse-submodules https://github.com/FANUC-CORPORATION/fanuc_driver.git

echo Installing FANUC dependencies
cd ~/ws_fanuc
sudo apt update
rosdep update
rosdep install --ignore-src --from-paths src -y

echo Building FANUC libraries
colcon build --symlink-install --cmake-args 
