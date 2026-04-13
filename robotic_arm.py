import os
import time
import shutil
import sys

from datetime import datetime

import cv2
import pyvisa
from xarm.wrapper import XArmAPI

from image_analysis import detect_coffee_ring

sys.path.append("FastSAM")
from fastsam import FastSAM


class RoboticArm:
  def __init__(self):
    self.arm = XArmAPI("169.254.211.213")

    self.rm = pyvisa.ResourceManager()
    self.hotplate_path = 'ASRL5::INSTR'
    print(self.rm.list_resources(), file=sys.stderr)
    
    self.plate_hotel_standard_position = [493.5, -110.0, 136.4, 180, 0, 0] #(20260408)
    self.plate_hotel1_z_floor_position = [405.0, -216.5, 46.0, 180, 0, 0] #(20260406)
    self.plate_hotel2_z_floor_position = [582.0, -216.5, 46.0, 180, 0, 0] #(20260406)
    self.arm_position1 = [390.0, 177.0, 136.4, 180, 0, 90] #(20260408)
    self.OT2_deck2_position = [571.0, 157.5, 72.5, 180, 0, 90] #(20260408)
    self.hot_plate_position = [240.0, 370.0, 92.5, 180, 0, 90] #(20260408)
    self.arm_position2 = [450.0, 20.0, 136.4, 180, 0, 0] #(20260408)
    self.arm_position3 = [270.0, -330.0, 136.4, 180, 0, -90] #(20260408)
    self.color_card_initial_position = [-30.0, -540.0, 10.0, 180, 0, -90]
    self.arm_position4 = [-30.0, -330.0, 30.0, 180, 0, -90]
    self.color_card_photo_position = [-125.0, -339.1, 0.0, 180, 0, -90]
    self.color_card_move_height = 60.0
    self.center_photo_position = [-91.35, -380.6, 30.0, 180, 0, -90] #(20260408)
    self.A1_photo_position = [-71.8, -341.5, 8.0, 180, 0, -90] #(20260408)

    self.plate_floor = 5
    self.next_drop_well = 0

    self.arm.motion_enable(enable=True)
    self.arm.set_mode(0)
    self.arm.set_state(state=0)

    self.arm.reset(wait=True)
    self.arm.set_bio_gripper_enable(True)
    self.arm.move_gohome(wait=True)
    self.arm.open_bio_gripper()

    # Prepare working directory
    self.result_path = os.path.join(os.path.dirname(__file__), datetime.now().strftime("%Y%m%d_%H%M"))
    os.makedirs(self.result_path)
   
    # Load FastSAM model
    self.fastsam_model = FastSAM("FastSAM/weights/FastSAM-x.pt")

  def load_plate(self):
    """
    Load well plate from plate hotel to OT-2
    """
    x, y, z, roll, pitch, yaw = self.plate_hotel_standard_position
    self.arm.set_position(x=x, y=y, z=z, speed=80, wait=True)

    assert(self.plate_floor >= 0)

    if self.plate_floor // 6 == 0:
        x, y, z, roll, pitch, yaw = self.plate_hotel1_z_floor_position
    else:
        x, y, z, roll, pitch, yaw = self.plate_hotel2_z_floor_position

    z += 45.2*(self.plate_floor % 6)
    self.arm.set_position(x=x, z=z, speed=80, wait=True)
    self.arm.set_position(y=y, speed=80, wait=True)
    self.arm.close_bio_gripper()
    self.arm.set_position(z=z+10, speed=25, wait=True)

    x, y, z, roll, pitch, yaw = self.plate_hotel_standard_position
    self.arm.set_position(y=y, speed=80, wait=True)
    self.arm.set_position(x=x, z=z, speed=80, wait=True)

    x, y, z, roll, pitch, yaw = self.arm_position1
    self.arm.set_position(x=x, y=y, yaw=yaw, speed=80, wait=True)
    
    x, y, z, roll, pitch, yaw = self.OT2_deck2_position
    self.arm.set_position(x=x, y=y, speed=80, wait=True)
    self.arm.set_position(z=z, speed=50, wait=True)
    self.arm.open_bio_gripper()

    x, y, z, roll, pitch, yaw = self.arm_position1
    self.arm.set_position(z=z, speed=50, wait=True)
    self.arm.set_position(x=x, speed=80, wait=True)

  def heat_plate(self, debug=True):
    """
    Heat well plate using heat plate
    """
    # Take well plate from OT-2
    x, y, z, roll, pitch, yaw = self.OT2_deck2_position
    self.arm.set_position(x=x, speed=80, wait=True)
    self.arm.set_position(z=z, speed=50, wait=True)
    self.arm.close_bio_gripper()

    x, y, z, roll, pitch, yaw = self.arm_position1
    self.arm.set_position(z=z, speed=25, wait=True)
           
    # Place the well plate on heat plate
    x, y, z, roll, pitch, yaw = self.hot_plate_position
    self.arm.set_position(x=x, speed=40, wait=True)
    self.arm.set_position(y=y, speed=40, wait=True)
    self.arm.set_position(z=z, speed=10, wait=True)

    self.arm.open_bio_gripper()
    with self.rm.open_resource(self.hotplate_path) as hotplate:
      hotplate.write('OUT_SP_1 60')
      hotplate.write('START_1')
      print("start heating at", datetime.now().strftime("%H:%M:%S"))
      if debug:
        time.sleep(5)
      else:
        time.sleep(3600)
      print("finish heating at", datetime.now().strftime("%H:%M:%S"))
      hotplate.write('STOP_1')

  def _prepare_plate_image(self):
    """
    Move robot arm to imaging pose
    Call this function before taking images
    """
    x, y, z, roll, pitch, yaw =self.hot_plate_position
    self.arm.set_position(x=x, y=y, yaw=yaw, speed=80, wait=True)
    self.arm.set_position(z=z, speed=50, wait=True)
    self.arm.close_bio_gripper()

    x, y, z, roll, pitch, yaw =self.arm_position2
    self.arm.set_position(z=z, speed=50, wait=True)
    self.arm.set_position(x=x, y=y, yaw=yaw, speed=80, wait=True)

    x, y, z, roll, pitch, yaw = self.arm_position3
    self.arm.set_position(x=x, y=y, z=z, roll=roll, pitch=pitch, yaw=yaw, speed=80, wait=True)

    x, y, z, roll, pitch, yaw = self.arm_position4
    self.arm.set_position(x=x, y=y, roll=roll, pitch=pitch, yaw=yaw, speed=80, wait=True)
    self.arm.set_position(z=z, speed=50, wait=True)

    x, y, z, roll, pitch, yaw = self.center_photo_position
    self.arm.set_position(x=x, y=y, z=z, roll=roll, pitch=pitch, yaw=yaw, speed=80, wait=True)

  def _get_image(self, debug=False):
    """
    Take images of well
    """
    
    well = self.next_drop_well
    
    offset_x = (well // 3) * 39.1
    offset_y = (well % 3) * 39.1

    x, y, z, roll, pitch, yaw = self.center_photo_position
    self.arm.set_position(z=z, speed=50, wait=True)

    x, y, z, roll, pitch, yaw = self.A1_photo_position
    self.arm.set_position(x=x-offset_x, y=y-offset_y, speed=80, wait=True)
    self.arm.set_position(z=z, speed=50, wait=True)

    # Camera setup
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)

    if debug:
      # Adjust camera position
      while True:
        _, frame = cap.read()
        h, w, _ = frame.shape
        cv2.line(frame, (w//2, 0), (w//2, h), color=(0, 255, 0), thickness=2)
        cv2.line(frame, (0, h//2), (w, h//2), color=(0, 255, 0), thickness=2)
        # cv2.imshow("Image", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        # if cv2.waitKey(10) > 0:
          # break
    
    _, frame = cap.read()
    cap.release()
    cv2.destroyAllWindows()
    
    now = datetime.now()
   
    well_name = ['A', 'B'][well//3] + str(well%3 + 1)

    filename = now.strftime("%Y%m%d%H%M%S_{}.jpg".format(well_name))
    
    cv2.imwrite(os.path.join(self.result_path, filename), frame)
    print("Saved image as {}".format(filename))
    return os.path.join(self.result_path, filename)

  def measure_results(self) -> int:
    self._prepare_plate_image()
    image_file = self._get_image()
    result = self._analyze_image(image_file)
    return result

  def _analyze_image(self, image_file: str) -> int:
    """Analyze image
    Return value: 1 (if cofee ring is observed) or 0 (otherwise).
    """
    ratio = detect_coffee_ring(self.fastsam_model, image_file, self.result_path)
    print("ratio:", ratio)

    if ratio > 0.3:
      print('Coffee ring')
      return 1
    else:
      print('No coffee ring')
      return 0


  def place_plate(self):
    """
    Place well plate on plate hotel
    """
    x, y, z, roll, pitch, yaw = self.center_photo_position
    self.arm.set_position(z=z, speed=50, wait=True)
    self.arm.set_position(x=x, y=y, roll=roll, pitch=pitch, yaw=yaw, speed=80, wait=True)
    
    x, y, z, roll, pitch, yaw = self.arm_position4
    self.arm.set_position(x=x, y=y, z=z, roll=roll, pitch=pitch, yaw=yaw, speed=80, wait=True)

    x, y, z, roll, pitch, yaw = self.arm_position3
    self.arm.set_position(z=z, speed=50, wait=True)
    self.arm.set_position(x=x, y=y, roll=roll, pitch=pitch, yaw=yaw, speed=80, wait=True)

    x, y, z, roll, pitch, yaw = self.plate_hotel_standard_position
    self.arm.set_position(x=x, y=y, z=z, roll=roll, pitch=pitch, yaw=yaw, speed=80, wait=True)

    if self.plate_floor // 6 == 0:
        x, y, z, roll, pitch, yaw = self.plate_hotel1_z_floor_position
    else:
        x, y, z, roll, pitch, yaw = self.plate_hotel2_z_floor_position

    z += 45.2*(self.plate_floor % 6)
    self.arm.set_position(x=x, z=z+10, speed=80, wait=True)
    self.arm.set_position(y=y, speed=50, wait=True)
    self.arm.set_position(z=z, speed=10, wait=True)
    self.arm.open_bio_gripper()

    x, y, z, roll, pitch, yaw = self.plate_hotel_standard_position  
    self.arm.set_position(y=y, speed=40, wait=True)
    self.arm.set_position(x=x, z=z, speed=50, wait=True)

    self.arm.move_gohome(wait=True)

    #self.plate_floor -= 1
    self.dropped_wells = []
    self.next_drop_well += 1

