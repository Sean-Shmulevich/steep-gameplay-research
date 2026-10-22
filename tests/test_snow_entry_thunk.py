"""Compile and emulate only authored Win64 adapter/fixture; no game payloads."""
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
try:
    import pefile
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_64, UC_HOOK_CODE
    from unicorn import x86_const as reg
except ImportError:
    pefile = None
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(pefile and shutil.which('x86_64-w64-mingw32-gcc'),
                     'Requires MinGW, pefile and unicorn on Python path')
class EntryThunkTests(unittest.TestCase):
    def test_win64_entry_registers_and_abi(self):
        with tempfile.TemporaryDirectory() as d:
            dll = Path(d) / 'fixture.dll'
            subprocess.run(['x86_64-w64-mingw32-gcc', '-shared', '-nostdlib',
                '-Wl,--entry,0,--export-all-symbols', '-O2', '-Wall', '-Wextra', '-Werror',
                '-I', str(ROOT/'native/snow_host'),
                str(ROOT/'native/snow_host/snow_entry_thunk.S'),
                str(ROOT/'tests/fixtures/snow_entry_thunk_fixture.c'),
                '-o', str(dll)], check=True, capture_output=True, timeout=60)
            pe = pefile.PE(str(dll)); base = pe.OPTIONAL_HEADER.ImageBase
            exports = {s.name.decode(): base+s.address for s in pe.DIRECTORY_ENTRY_EXPORT.symbols}
            entry = exports['SnowProbe_EntryThunk']; out = exports['observed_entry']
            unwind = [x for x in pe.DIRECTORY_ENTRY_EXCEPTION
                      if base+x.struct.BeginAddress == entry]
            self.assertEqual(len(unwind), 1, 'Entry needs Windows unwind metadata')
            u = Uc(UC_ARCH_X86, UC_MODE_64)
            u.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage+4095)//4096*4096)
            u.mem_write(base, pe.get_memory_mapped_image())
            stack = 0x10000000; u.mem_map(stack, 0x20000)
            sp = stack+0x18008; stop = stack+0x1f000
            calls = []
            def at_dispatch(uc, address, size, context):
                if address != exports['SnowProbe_EntryDispatch']:
                    return
                rsp = uc.reg_read(reg.UC_X86_REG_RSP)
                self.assertEqual(rsp % 16, 8)
                self.assertEqual(uc.reg_read(reg.UC_X86_REG_R9), rsp+40)
                # A legal callee may overwrite all four shadow slots.
                uc.mem_write(rsp+8, bytes([0xa5])*32)
                calls.append(address)
            u.hook_add(UC_HOOK_CODE, at_dispatch)
            saved_regs = [reg.UC_X86_REG_RBX,reg.UC_X86_REG_RBP,reg.UC_X86_REG_RDI,
                          reg.UC_X86_REG_RSI,reg.UC_X86_REG_R12,reg.UC_X86_REG_R13,
                          reg.UC_X86_REG_R14,reg.UC_X86_REG_R15]
            for ordinal, bits in enumerate([(0x3c088889,0x3d088889), (0,0x80000000),
                                            (0x7fc12345,0xff800000)]):
                values = {r: 0x12340000+ordinal*0x100+i for i,r in enumerate(saved_regs)}
                for r,v in values.items(): u.reg_write(r,v)
                for i in range(6,16): u.reg_write(getattr(reg,f'UC_X86_REG_XMM{i}'),(1<<100)+i)
                actor = 0x34567890+ordinal
                u.mem_write(sp,struct.pack('<Q',stop));u.reg_write(reg.UC_X86_REG_RSP,sp)
                u.reg_write(reg.UC_X86_REG_RCX,actor)
                u.reg_write(reg.UC_X86_REG_XMM1,bits[0]);u.reg_write(reg.UC_X86_REG_XMM2,bits[1])
                u.emu_start(entry,stop,count=1000)
                self.assertEqual(u.reg_read(reg.UC_X86_REG_RIP),stop)
                self.assertEqual(u.reg_read(reg.UC_X86_REG_RSP),sp+8)
                actual = struct.unpack('<8Q',u.mem_read(out,64))
                self.assertEqual(actual,(values[reg.UC_X86_REG_RDI],values[reg.UC_X86_REG_RSI],
                    values[reg.UC_X86_REG_RBX],stop,sp,actor,*bits))
                for r,v in values.items(): self.assertEqual(u.reg_read(r),v)
                for i in range(6,16): self.assertEqual(u.reg_read(getattr(reg,f'UC_X86_REG_XMM{i}')),(1<<100)+i)

            self.assertEqual(len(calls),3)
