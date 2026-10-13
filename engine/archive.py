"""Bounded read-only version-27 forge index and version-2 block framing.

Based on Studio document hashes in STUDIO_SOURCES.json. No archive writer,
checksum inference or implicit asset publication. Names are labels, IDs keys.
Optional native decompression uses installed zstd/lzo2 libraries, never bundles.
"""
import ctypes
import ctypes.util
from dataclasses import dataclass
import io
import struct
import zlib

MAGIC=bytes.fromhex('33aafb5799fa0410')

@dataclass(frozen=True)
class Entry:
    resource_id:int
    offset:int
    size:int
    name:str
    type_id:int
    reserved_size:int

class Archive:
    def __init__(self,stream,max_entries=1_000_000):
        self.stream=stream;here=stream.tell();stream.seek(0,2);self.size=stream.tell();stream.seek(here)
        if self.read_at(0,9)!=b'scimitar\0':raise ValueError('Not a forge archive')
        version,header=struct.unpack('<IQ',self.read_at(9,12))
        if version!=27:raise ValueError('Unsupported forge version')
        data=self.read_at(header,44);count=struct.unpack_from('<I',data)[0];capacity,tables,table=struct.unpack_from('<IIQ',data,28)
        if capacity!=5000 or not 0<tables<=1000 or count>max_entries:raise ValueError('Invalid archive table limits')
        entries=[];visited=set();ids=set()
        for table_no in range(tables):
            if table in visited:raise ValueError('Cyclic archive tables')
            visited.add(table);h=self.read_at(table,48)
            used,folders,index,next_table,first,last,names,folder_data=struct.unpack('<IIQqIIQQ',h)
            if used>capacity or folders>capacity or first!=table_no*capacity or last!=first+capacity-1:raise ValueError('Invalid table header')
            if index!=table+48 or names!=index+capacity*20 or folder_data!=names+capacity*192:raise ValueError('Unsupported table layout')
            self.bounds(folder_data,capacity*176+1)
            raw=self.read_at(index,used*20);labels=self.read_at(names,used*192)
            for i in range(used):
                offset,key,size=struct.unpack_from('<QQI',raw,i*20)
                if key in ids or size==0:raise ValueError('Duplicate ID or empty payload')
                ids.add(key);self.bounds(offset,size)
                label=labels[i*192:(i+1)*192];reserved=struct.unpack_from('<I',label)[0];type_id=struct.unpack_from('<I',label,16)[0]
                if reserved<size:raise ValueError('Payload exceeds reserved slot')
                name_bytes=label[44:172]
                if b'\0' not in name_bytes:raise ValueError('Unterminated resource name')
                try:name=name_bytes.split(b'\0',1)[0].decode('ascii')
                except UnicodeDecodeError as exc:raise ValueError('Unsupported name encoding') from exc
                entries.append(Entry(key,offset,size,name,type_id,reserved))
            if table_no==tables-1:
                if next_table!=-1:raise ValueError('Unterminated table chain')
            elif next_table<0:raise ValueError('Premature table termination')
            table=next_table
        if len(entries)!=count:raise ValueError('Archive entry count mismatch')
        self.entries=tuple(entries);self.by_id={entry.resource_id:entry for entry in entries}
    def bounds(self,offset,size):
        if offset<0 or size<0 or offset>self.size-size:raise ValueError('Archive range outside file')
    def read_at(self,offset,size):
        self.bounds(offset,size);self.stream.seek(offset);data=self.stream.read(size)
        if len(data)!=size:raise ValueError('Short archive read')
        return data
    def payload(self,key,max_bytes=64*1024*1024):
        entry=self.by_id[key]
        if entry.size>max_bytes:raise ValueError('Payload exceeds read budget')
        return self.read_at(entry.offset,entry.size)


def resolve_layers(layers):
    """Explicit low-to-high precedence; preserve overwritten IDs as provenance."""
    selected={};history={}
    for label,archive in layers:
        for entry in archive.entries:
            history.setdefault(entry.resource_id,[]).append(label);selected[entry.resource_id]=(label,entry)
    return selected,history


def decode_blocks(payload,decoder=None,max_output=64*1024*1024):
    """Return decoded blocks, exact framing and bounded output; no magic scanning."""
    view=memoryview(payload);offset=0;total=0;blocks=[]
    def read(n):
        nonlocal offset
        if n<0 or offset+n>len(view):raise ValueError('Truncated block')
        value=bytes(view[offset:offset+n]);offset+=n;return value
    def chunk(codec,packed,expected):
        nonlocal total
        if not 0<packed<=expected or expected>0x40000:raise ValueError('Invalid chunk sizes')
        if total+expected>max_output:raise ValueError('Decompression budget exceeded')
        checksum=struct.unpack('<I',read(4))[0];data=read(packed)
        if zlib.adler32(data,0)&0xffffffff!=checksum:raise ValueError('Chunk checksum mismatch')
        if packed==expected:result=data
        else:
            if decoder is None:raise ValueError('Compressed chunk needs a codec backend')
            result=decoder(codec,data,expected)
        if not isinstance(result,bytes) or len(result)!=expected:raise ValueError('Decoded length mismatch')
        total+=expected;return result
    while offset<len(view):
        start=offset
        if read(8)!=MAGIC:raise ValueError('Trailing data or unsupported block magic')
        version,codec,flags=struct.unpack('<HBI',read(7));layout=bool(flags&0x80000000);chunk_size=flags&0x7fffffff
        if version!=2 or chunk_size!=0x40000 or (layout,codec) not in ((True,5),(False,0),(False,1)):raise ValueError('Unsupported block header')
        chunks=[]
        if layout:
            count=struct.unpack('<I',read(4))[0]
            if not 0<count<=8192:raise ValueError('Invalid chunk count')
            sizes=[struct.unpack('<II',read(8)) for _ in range(count)]
            for i,(expected,packed) in enumerate(sizes):
                if (i<count-1 and expected!=chunk_size) or (i==count-1 and not 0<expected<chunk_size):raise ValueError('Unsupported chunk termination')
                chunks.append(chunk(codec,packed,expected))
        else:
            for _ in range(8192):
                flag,packed,expected=struct.unpack('<BII',read(9))
                if flag!=1:raise ValueError('Unsupported layout-B flag')
                chunks.append(chunk(codec,packed,expected))
                if expected<chunk_size:break
            else:raise ValueError('Unterminated chunk stream')
        blocks.append(dict(codec=codec,layout='A' if layout else 'B',offset=start,consumed=offset-start,data=b''.join(chunks)))
    if not blocks:raise ValueError('Empty block stream')
    return blocks


class NativeCodecs:
    """Optional bounded zstd/LZO decoder with explicit native ABI signatures."""
    def __init__(self,libraries=None):
        self._libraries={};self.library_paths=dict(libraries or {})
        if set(self.library_paths)-{'zstd','lzo2'}:raise ValueError('Unknown native library')
    def __call__(self,codec,data,expected):
        if codec not in (0,1,5) or not 0<expected<=0x40000:raise ValueError('Unsupported codec/output size')
        name='zstd' if codec==5 else 'lzo2'
        if name not in self._libraries:
            path=self.library_paths.get(name) or ctypes.util.find_library(name)
            if path is None:raise ValueError(f'Optional system library unavailable: {name}')
            self._libraries[name]=ctypes.CDLL(path)
        lib=self._libraries[name];source=ctypes.create_string_buffer(data);output=ctypes.create_string_buffer(expected)
        if codec==5:
            lib.ZSTD_getFrameContentSize.argtypes=[ctypes.c_void_p,ctypes.c_size_t];lib.ZSTD_getFrameContentSize.restype=ctypes.c_ulonglong
            lib.ZSTD_findFrameCompressedSize.argtypes=[ctypes.c_void_p,ctypes.c_size_t];lib.ZSTD_findFrameCompressedSize.restype=ctypes.c_size_t
            lib.ZSTD_decompress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t];lib.ZSTD_decompress.restype=ctypes.c_size_t
            if lib.ZSTD_getFrameContentSize(source,len(data))!=expected or lib.ZSTD_findFrameCompressedSize(source,len(data))!=len(data):raise ValueError('Zstd frame size mismatch')
            actual=lib.ZSTD_decompress(output,expected,source,len(data))
            if actual!=expected:raise ValueError('Zstd decode failed or wrong length')
        else:
            # LZO uint is pointer-sized on the supported 64-bit Unix ABI.
            if ctypes.sizeof(ctypes.c_ulong)!=ctypes.sizeof(ctypes.c_void_p):raise ValueError('Unsupported LZO ABI')
            lib.lzo1x_decompress_safe.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.POINTER(ctypes.c_size_t),ctypes.c_void_p];lib.lzo1x_decompress_safe.restype=ctypes.c_int
            actual=ctypes.c_size_t(expected)
            if lib.lzo1x_decompress_safe(source,len(data),output,ctypes.byref(actual),None)!=0 or actual.value!=expected:raise ValueError('LZO decode failed or wrong length')
        return output.raw
