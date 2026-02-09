import ivoryos

from robotic_arm import RoboticArm
from liquid_handler import OT2

lh = OT2()
arm = RoboticArm()
    
if __name__ == "__main__":
  ivoryos.run(__name__, port=8888)