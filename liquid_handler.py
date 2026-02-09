import asyncio

from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends import OpentronsBackend
from pylabrobot.resources.opentrons import (
  OTDeck,
  opentrons_96_tiprack_1000ul,
  corning_12_wellplate_6point9ml_flat,
  corning_6_wellplate_16point8ml_flat,
  thermoscientificnunc_96_wellplate_1300ul
)
from pylabrobot.resources import Coordinate

class OT2:
  def __init__(self):
    self.lh = LiquidHandler(backend=OpentronsBackend(host="169.254.211.53"), deck=OTDeck())

    self.next_tip = 44
    self.next_mix_well = 38
    self.plate_floor = 5
    self.next_drop_well = 0

    self.initial_water_well = 4
    
    self.offset6 = Coordinate(1.0, 0.0, -15.0)
    self.offset12 = Coordinate(-1.7, -2.2, -17.0)
    self.offset96 = Coordinate(-0.5, -1.2, -17.0)

    asyncio.run(self._setup())

  def _set_next_tip(self, num):
    self.next_tip = num
  
  def _get_tip_spot_name(self, num):
    if num < 0 or num >= 96:
      return None
    else:
      return ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'][num//12] + str(num%12 + 1)
  
  def _get_well_name6(self, num):
    if num < 0 or num >= 6:
      return None
    else:
      return ['A', 'B'][num//3] + str(num%3 + 1)
  
  def _get_well_name12(self, num):
    if num < 0 or num >= 12:
      return None
    else:
      return ['A', 'B', 'C'][num//4] + str(num%4 + 1)

  def _get_well_name96(self, num):
    if num < 0 or num >= 96:
      return None
    else:
      return ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'][num//12] + str(num%12 + 1)
  
  async def _auto_pick_up_tip(self):
    if self.next_tip < 96:
      tip = self._get_tip_spot_name(self.next_tip)
      await self.lh.pick_up_tips(self.tip_rack1[tip],
                                offsets=[Coordinate(0.6, -2.0, 2.0)])
    else:
      tip = self._get_tip_spot_name(self.next_tip-96)
      await self.lh.pick_up_tips(self.tip_rack2[tip],
                                offsets=[Coordinate(0.6, -2.0, 2.0)])
    self.next_tip += 1
  
  async def _setup(self):
    await self.lh.setup()
    await self.lh.backend.home()
    
    self.tip_rack1 = opentrons_96_tiprack_1000ul(name="tip_rack1")
    self.lh.deck.assign_child_at_slot(self.tip_rack1, slot=10)

    self.tip_rack2 = opentrons_96_tiprack_1000ul(name="tip_rack2")
    self.lh.deck.assign_child_at_slot(self.tip_rack2, slot=11)

    self.silica_water_plate = corning_12_wellplate_6point9ml_flat(name="silica_water_plate")
    self.lh.deck.assign_child_at_slot(self.silica_water_plate, slot=8)

    self.surfactant_plate = corning_12_wellplate_6point9ml_flat(name="surfactant_plate")
    self.lh.deck.assign_child_at_slot(self.surfactant_plate, slot=9)

    self.mix_plate = thermoscientificnunc_96_wellplate_1300ul(name="mix_plate")
    self.lh.deck.assign_child_at_slot(self.mix_plate, slot=7)

    self.drop_plate = corning_6_wellplate_16point8ml_flat(name="drop_plate")
    self.lh.deck.assign_child_at_slot(self.drop_plate, slot=2)

  async def _prepare_single_sample_async(self, silica: float, water: float, PVA: float, SDS: float, DTAB: float, PVP: float):
      mix_well = self._get_well_name96(self.next_mix_well)
      self.next_mix_well += 1
      water_well = self._get_well_name12(self.next_drop_well//3+self.initial_water_well)
   
      # surfactants
      Surfactants = [PVA, SDS, DTAB, PVP]
      well_names  = [("A1", "B1"), ("A2", "B2"), ("A3", "B3"), ("C4", "B4")]  
      for surf, wells in zip(Surfactants, well_names):
        diluted_well, concentrated_well = wells
        if surf > 0: 
          if surf < 0.01:
            await self._auto_pick_up_tip()
            for _ in range(3):
                await self.lh.aspirate(self.surfactant_plate[diluted_well], vols=[300],
                              offsets=[self.offset12])
                await self.lh.dispense(self.surfactant_plate[diluted_well], vols=[300],
                              offsets=[self.offset12])
            await self.lh.aspirate(self.surfactant_plate[diluted_well], vols=[surf*50000],
                              offsets=[self.offset12])
            await self.lh.dispense(self.mix_plate[mix_well], vols=[surf*50000],
                              offsets=[self.offset96])
            await self.lh.discard_tips()
            water -= surf*50000
          
          else: 
            await self._auto_pick_up_tip()
            for _ in range(3):
                await self.lh.aspirate(self.surfactant_plate[concentrated_well], vols=[400],
                              offsets=[self.offset12])
                await self.lh.dispense(self.surfactant_plate[concentrated_well], vols=[400],
                              offsets=[self.offset12])
            await self.lh.aspirate(self.surfactant_plate[concentrated_well], vols=[surf*10000],
                              offsets=[self.offset12])
            await self.lh.dispense(self.mix_plate[mix_well], vols=[surf*10000],
                              offsets=[self.offset96])
            await self.lh.discard_tips()
            water -= surf*10000

      # water
      await self._auto_pick_up_tip()
      await self.lh.aspirate(self.silica_water_plate[water_well], vols=[water],
                          offsets=[self.offset12])
      await self.lh.dispense(self.mix_plate[mix_well], vols=[water],
                          offsets=[self.offset96])
      await self.lh.discard_tips()


      # silica
      await self._auto_pick_up_tip()
      for _ in range(3):
        await self.lh.aspirate(self.silica_water_plate["A1"], vols=[200],
                               offsets=[self.offset12])
        await self.lh.dispense(self.silica_water_plate["A1"], vols=[200],
                               offsets=[self.offset12])
      await self.lh.aspirate(self.silica_water_plate["A1"], vols=[silica],
                         offsets=[self.offset12])
      await self.lh.dispense(self.mix_plate[mix_well], vols=[silica],
                         offsets=[self.offset96])
       

      drop_well = self._get_well_name6(self.next_drop_well)
      for _ in range(2):
        await self.lh.aspirate(self.mix_plate[mix_well], vols=[100],
                                offsets=[self.offset96])
        await self.lh.dispense(self.mix_plate[mix_well], vols=[100],
                                offsets=[self.offset96])
      await self.lh.aspirate(self.mix_plate[mix_well], vols=[100],
                            offsets=[self.offset96])
      await self.lh.dispense(self.drop_plate[drop_well], vols=[100],
                            offsets=[self.offset6])
      self.next_drop_well += 1
        
      await self.lh.discard_tips()
      await self.lh.backend.home()

  def prepare_single_sample(self, pva: float, dtab: float):
    silica = 100
    pvp = 0
    sds = 0
    water = 1000 - silica
    print("pva:", pva, "dtab:", dtab)
    asyncio.run(self._prepare_single_sample_async(silica, water, pva, sds, dtab, pvp))