import ivoryos

from robotic_arm import RoboticArm
from liquid_handler import OT2

lh = OT2()
arm = RoboticArm()
    
if __name__ == "__main__":
  ivoryos.run(__name__, port=8888)
  # # x1 = 0
  # # x2 = 0
  # # sdl.select_candidates("RE")
  # for _ in range(6):
  #   sdl.select_candidates("PDC")
  #   arm.load_plate()
  #   sdl.prepare_samples()
  #   arm.heat_plate(debug=False)
  #   sdl.measure_results()
  #   arm.place_plate()
