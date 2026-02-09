import os
import time
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
    pass
    self.arm = XArmAPI("169.254.211.213")

    self.rm = pyvisa.ResourceManager()
    self.hotplate = self.rm.open_resource('ASRL5::INSTR')
    self.fastsam_model = FastSAM("FastSAM/weights/FastSAM-x.pt")
    
    self.plate_hotel_standard_position = [507.0, -110.0, 150.0, 180, 0, 0]
    self.plate_hotel1_z_floor_position = [417.5, -216.5, 46.0, 180, 0, 0]
    self.plate_hotel2_z_floor_position = [594, -216.5, 48.0, 180, 0, 0]
    self.arm_position1 = [390.0, 177.0, 150.0, 180, 0, 90]
    self.OT2_deck2_position = [582.0, 180.5, 72.0, 180, 0, 90] 
    self.hot_plate_position = [240.0, 370.0, 91.0, 180, 0, 90]
    self.arm_position2 = [450.0, 20.0, 150.0, 180, 0, 0]
    self.arm_position3 = [270.0, -330.0, 150.0, 180, 0, -90]
    self.color_card_initial_position = [-30.0, -540.0, 10.0, 180, 0, -90]
    self.arm_position4 = [-30.0, -330.0, 30.0, 180, 0, -90]
    self.color_card_photo_position = [-125.0, -339.1, 0.0, 180, 0, -90]
    self.color_card_move_height = 60.0
    self.center_photo_position = [-125.0, -339.1, 30.0, 180, 0, -90]
    self.A1_photo_position = [-100.0, -307.0, 6.0, 180, 0, -90]

    self.plate_floor = 5
    self.next_drop_well = 0

    self.arm.motion_enable(enable=True)
    self.arm.set_mode(0)
    self.arm.set_state(state=0)

    self.arm.reset(wait=True)
    self.arm.set_bio_gripper_enable(True)
    self.arm.move_gohome(wait=True)
    self.arm.open_bio_gripper()
  
  def _set_result_path(self, result_path):
    self.result_path = result_path

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

  def heat_plate(self):
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
    self.hotplate.write('OUT_SP_1 60')
    self.hotplate.write('START_1')
    print("start heating at", datetime.now().strftime("%H:%M:%S"))
    debug = False
    if debug:
      time.sleep(5)
    else:
      time.sleep(3600)
    print("finish heating at", datetime.now().strftime("%H:%M:%S"))
    self.hotplate.write('STOP_1')

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
  
  def get_image(self):
    """
    Take images of well
    Return value: 1 (if cofee ring is observed) or 0 (otherwise).
    """
    self._prepare_plate_image()    
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

    debug = False
    if debug:
      # Adjust camera position
      while True:
        _, frame = cap.read()
        h, w, _ = frame.shape
        cv2.line(frame, (w//2, 0), (w//2, h), color=(0, 255, 0), thickness=2)
        cv2.line(frame, (0, h//2), (w, h//2), color=(0, 255, 0), thickness=2)
        cv2.imshow("Image", cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if cv2.waitKey(10) > 0:
          break
    
    _, frame = cap.read()
    cap.release()
    cv2.destroyAllWindows()
    
    now = datetime.now()
   
    well_name = ['A', 'B'][well//3] + str(well%3 + 1)

    filename = now.strftime("%Y%m%d%H%M%S_{}.jpg".format(well_name))
    
    cv2.imwrite(os.path.join(self.result_path, filename), frame)
    print("Saved image as {}".format(filename))
    ratio = detect_coffee_ring(self.fastsam_model, filename, self.result_path)
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

    self.dropped_wells = []
    self.next_drop_well += 1