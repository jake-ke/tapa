"""Helpers for Xilinx verilog.

This package defines constants and helper functions for verilog files generated
for Xilinx devices.
"""

import os
import shutil
import sys
import tempfile
from typing import IO, BinaryIO, Dict, Iterable, Iterator, List, TextIO, Union

import tapa.instance
from haoda.backend import xilinx as backend
from tapa.verilog import ast
# pylint: disable=wildcard-import,unused-wildcard-import
from tapa.verilog.util import *
from tapa.verilog.xilinx.async_mmap import *
from tapa.verilog.xilinx.axis import *
from tapa.verilog.xilinx.const import *
from tapa.verilog.xilinx.m_axi import *
from tapa.verilog.xilinx.module import *
from tapa.verilog.xilinx.typing import *


def ctrl_instance_name(top: str) -> str:
  return 'control_s_axi_U'


def is_data_port(port: str) -> bool:
  return (port.endswith(ISTREAM_SUFFIXES[0]) or
          port.endswith(OSTREAM_SUFFIXES[0]))


def generate_handshake_ports(
    instance: tapa.instance.Instance,
    rst_q: Pipeline,
) -> Iterator[ast.PortArg]:
  yield ast.make_port_arg(port=HANDSHAKE_CLK, arg=CLK)
  yield ast.make_port_arg(port=HANDSHAKE_RST_N, arg=rst_q[-1])
  yield ast.make_port_arg(port=HANDSHAKE_START, arg=instance.start)
  for port in HANDSHAKE_OUTPUT_PORTS:
    yield ast.make_port_arg(
        port=port,
        arg="" if instance.is_autorun else wire_name(instance.name, port),
    )


def fifo_partition_name(name: str, idx: int) -> str:
  return f'{name}/inst[{idx}].unit'


def pack(top_name: str, rtl_dir: str, ports: Iterable[tapa.instance.Port],
         output_file: Union[str, BinaryIO]) -> None:
  port_tuple = tuple(ports)
  if isinstance(output_file, str):
    xo_file = output_file
  else:
    xo_file = tempfile.mktemp(prefix='tapa_' + top_name + '_', suffix='.xo')
  with tempfile.NamedTemporaryFile(mode='w+',
                                   prefix='tapa_' + top_name + '_',
                                   suffix='_kernel.xml') as kernel_xml_obj:
    print_kernel_xml(name=top_name, ports=port_tuple, kernel_xml=kernel_xml_obj)
    kernel_xml_obj.flush()
    with backend.PackageXo(
        xo_file=xo_file,
        top_name=top_name,
        kernel_xml=kernel_xml_obj.name,
        hdl_dir=rtl_dir,
        m_axi_names=(port.name for port in port_tuple if port.cat in {
            tapa.instance.Instance.Arg.Cat.MMAP,
            tapa.instance.Instance.Arg.Cat.ASYNC_MMAP
        })) as proc:
      stdout, stderr = proc.communicate()
    if proc.returncode == 0 and os.path.exists(xo_file):
      if not isinstance(output_file, str):
        with open(xo_file, 'rb') as xo_obj:
          shutil.copyfileobj(xo_obj, output_file)
    else:
      sys.stdout.write(stdout.decode('utf-8'))
      sys.stderr.write(stderr.decode('utf-8'))
  if not isinstance(output_file, str):
    os.remove(xo_file)


def print_constraints(
    instance_dict: Dict[str, str],
    output: TextIO,
    pre: str = '',
    post: str = '',
) -> None:
  directive_dict: Dict[str, List[str]] = {}
  for instance, pblock in instance_dict.items():
    directive_dict.setdefault(pblock, []).append(instance)

  output.write('# partitioning constraints generated by tapac\n')
  output.write('# modify only if you know what you are doing\n')
  output.write('puts "applying partitioning constraints generated by tapac"\n')
  output.write(pre)
  output.write('\n')
  for pblock, modules in directive_dict.items():
    output.write(f'add_cells_to_pblock [get_pblocks {pblock}] '
                 '[get_cells -regex {\n')
    for module in modules:
      module = module.replace('[', r'\\[').replace('.', r'\\.')
      output.write(f'  pfm_top_i/dynamic_region/.*/inst/{module}\n')
    output.write('}]\n')
  output.write(post)


def print_kernel_xml(name: str, ports: Iterable[tapa.instance.Port],
                     kernel_xml: IO[str]) -> None:
  """Generate kernel.xml file.

  Args:
    name: name of the kernel.
    ports: Iterable of tapa.instance.Port.
    kernel_xml: file object to write to.
  """
  args = []
  for port in ports:
    if port.cat == tapa.instance.Instance.Arg.Cat.SCALAR:
      cat = backend.Cat.SCALAR
    elif port.cat in {
        tapa.instance.Instance.Arg.Cat.MMAP,
        tapa.instance.Instance.Arg.Cat.ASYNC_MMAP
    }:
      cat = backend.Cat.MMAP
    elif port.cat == tapa.instance.Instance.Arg.Cat.ISTREAM:
      cat = backend.Cat.ISTREAM
    elif port.cat == tapa.instance.Instance.Arg.Cat.OSTREAM:
      cat = backend.Cat.OSTREAM
    else:
      raise ValueError(f'unexpected port.cat: {port.cat}')

    args.append(
        backend.Arg(
            cat=cat,
            name=port.name,
            port='',  # use defaults
            ctype=port.ctype,
            width=port.width,
        ))
  backend.print_kernel_xml(name, args, kernel_xml)
