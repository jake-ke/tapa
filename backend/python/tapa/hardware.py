AREA_OF_ASYNC_MMAP = {
    32: {
        'BRAM': 0,
        'DSP': 0,
        'FF': 377,
        'LUT': 786,
        'URAM': 0,
    },
    64: {
        'BRAM': 0,
        'DSP': 0,
        'FF': 375,
        'LUT': 848,
        'URAM': 0,
    },
    128: {
        'BRAM': 0,
        'DSP': 0,
        'FF': 373,
        'LUT': 971,
        'URAM': 0,
    },
    256: {
        'BRAM': 0,
        'DSP': 0,
        'FF': 371,
        'LUT': 1225,
        'URAM': 0,
    },
    512: {
        'BRAM': 0,
        'DSP': 0,
        'FF': 369,
        'LUT': 1735,
        'URAM': 0,
    },
    1024: {
        'BRAM': 0,
        'DSP': 0,
        'FF': 367,
        'LUT': 2755,
        'URAM': 0,
    },
}

# FIXME: currently assume 512 bit width
AREA_PER_HBM_CHANNEL = {
    'LUT': 5000,
    'FF': 6500,
    'BRAM': 0,
    'URAM': 0,
    'DSP': 0,
}

ZERO_AREA = {
    'LUT': 0,
    'FF': 0,
    'BRAM': 0,
    'URAM': 0,
    'DSP': 0,
}

# default pipeline level for control signals
DEFAULT_REGISTER_LEVEL = 3

SUPPORTED_PART_NUM_PREFIXS = (
    'xcu280-',
    'xcu250-',
    'xcvp1802-',
)


def get_zero_area():
  return ZERO_AREA


def get_hbm_controller_area():
  """ area of one hbm controller """
  return AREA_PER_HBM_CHANNEL


def get_async_mmap_area(data_channel_width: int):
  return AREA_OF_ASYNC_MMAP[_next_power_of_2(data_channel_width)]


def _next_power_of_2(x):
  return 1 if x == 0 else 2**(x - 1).bit_length()


def get_ctrl_instance_region(part_num: str) -> str:
  if part_num.startswith('xcu250-') or part_num.startswith('xcu280-'):
    return 'COARSE_X1Y0'
  raise NotImplementedError(f'unknown {part_num}')


def get_port_region(part_num: str, port_cat: str, port_id: int) -> str:
  """
  return the physical location of a given port
  refer to the Vitis platforminfo command
  """
  if part_num.startswith('xcu280-'):
    if port_cat == 'HBM' and 0 <= port_id < 32:
      return f'COARSE_X{port_id // 16}Y0'
    if port_cat == 'DDR' and 0 <= port_id < 2:
      return f'COARSE_X1Y{port_id}'
    if port_cat == 'PLRAM' and 0 <= port_id < 6:
      return f'COARSE_X1Y{int(port_id/2)}'

  elif part_num.startswith('xcu250-'):
    if port_cat == 'DDR' and 0 <= port_id < 4:
      return f'COARSE_X1Y{port_id}'
    if port_cat == 'PLRAM' and 0 <= port_id < 4:
      return f'COARSE_X1Y{port_id}'

  raise NotImplementedError(
      f'unknown port_cat {port_cat}, port_id {port_id} for {part_num}')


class xcvp1802_hardware():
  part_num = 'xcvp1802-lsvc4072-2MP-e-S'
  noc = {}

  def __init__(self) -> None:
    self.init_avail_noc()

  def init_avail_noc(self):
    # coarse region granularity
    # 4 SLRs and each SLR is split vertically into two coarse regions
    # COARSE_X0Y0 = CR_X0Y0:CR_X4Y4  | COARSE_X1Y0 = CR_X5Y0:CR_X9Y4
    # COARSE_X0Y1 = CR_X0Y5:CR_X4Y7  | COARSE_X1Y1 = CR_X5Y5:CR_X9Y7
    # COARSE_X0Y2 = CR_X0Y8:CR_X4Y10 | COARSE_X1Y2 = CR_X058:CR_X4910
    # COARSE_X0Y3 = CR_X0Y11:CR_X4Y13| COARSE_X1Y3 = CR_X0Y51:CR_X4913
    self.noc[(0, 0)] = 28
    self.noc[(0, 1)] = 24
    self.noc[(0, 2)] = 24
    self.noc[(0, 3)] = 24
    self.noc[(1, 0)] = 28
    self.noc[(1, 1)] = 24
    self.noc[(1, 2)] = 24
    self.noc[(1, 3)] = 24

  def get_port_region(self, port_cat: str) -> str:
    if port_cat == "DDR" or port_cat == "LPDDR":
      for coord, avail in self.noc.items():
        if avail >= 2:
          self.noc[coord] -= 2
          return f'COARSE_X{coord[0]}Y{coord[1]}'
      assert "Running out of available clock regions with NOC for memory port assignments"

    raise NotImplementedError(
      f'unknown port_cat {port_cat} for {self.part_num}')


def get_slr_count(part_num: str):
  if part_num.startswith('xcu280-'):
    return 3
  elif part_num.startswith('xcu250-'):
    return 4
  elif part_num.startswith('xcvp1802-'):
    return 4
  else:
    raise NotImplementedError('unknown part_num %s', part_num)


def is_part_num_supported(part_num: str):
  return any(
      part_num.startswith(prefix) for prefix in SUPPORTED_PART_NUM_PREFIXS)
