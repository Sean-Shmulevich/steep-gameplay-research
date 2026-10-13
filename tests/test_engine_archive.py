import io
import struct
import unittest
import zlib
from engine.archive import Archive,MAGIC,decode_blocks,resolve_layers

def archive(key=42,label=b'invented'):
    header=64;table=108;index=table+48;names=index+5000*20;folders=names+5000*192;data=folders+5000*176+1
    raw=bytearray(data+3);raw[:9]=b'scimitar\0';struct.pack_into('<IQ',raw,9,27,header)
    struct.pack_into('<I',raw,header,1);struct.pack_into('<IIQ',raw,header+28,5000,1,table)
    struct.pack_into('<IIQqIIQQ',raw,table,1,0,index,-1,0,4999,names,folders)
    struct.pack_into('<QQI',raw,index,data,key,3);struct.pack_into('<I',raw,names,3);raw[names+44:names+44+len(label)]=label;raw[data:]=b'abc'
    return raw

def block(data=b'abc'):
    return MAGIC+struct.pack('<HBI',2,5,0x80040000)+struct.pack('<III',1,len(data),len(data))+struct.pack('<I',zlib.adler32(data,0))+data

class ArchiveTests(unittest.TestCase):
    def test_index_and_patch_identity(self):
        a=Archive(io.BytesIO(archive()));b=Archive(io.BytesIO(archive(label=b'renamed')))
        self.assertEqual(a.payload(42),b'abc');selected,history=resolve_layers([('base',a),('patch',b)])
        self.assertEqual(selected[42][1].name,'renamed');self.assertEqual(history[42],['base','patch'])
    def test_bounds_and_chain(self):
        data=archive();struct.pack_into('<q',data,108+16,108)
        with self.assertRaises(ValueError):Archive(io.BytesIO(data))
        with self.assertRaises(ValueError):Archive(io.BytesIO(archive()[:-1]))
    def test_stored_blocks_and_checksum(self):
        blocks=decode_blocks(block()+block(b'def'))
        self.assertEqual([x['data'] for x in blocks],[b'abc',b'def'])
        with self.assertRaises(ValueError):decode_blocks(block()[:-1]+b'x')
        with self.assertRaises(ValueError):decode_blocks(block()+b'junk')
    def test_budget_and_codec_failure(self):
        with self.assertRaises(ValueError):decode_blocks(block(),max_output=2)
        packed=MAGIC+struct.pack('<HBI',2,5,0x80040000)+struct.pack('<III',1,9,3)+struct.pack('<I',zlib.adler32(b'abc',0))+b'abc'
        with self.assertRaises(ValueError):decode_blocks(packed)
        with self.assertRaises(ValueError):decode_blocks(packed,lambda *args:b'bad')
        self.assertEqual(decode_blocks(packed,lambda *args:b'123456789')[0]['data'],b'123456789')
    def test_layout_b(self):
        data=b'abcd';raw=MAGIC+struct.pack('<HBI',2,0,0x40000)+struct.pack('<BII',1,4,4)+struct.pack('<I',zlib.adler32(data,0))+data
        self.assertEqual(decode_blocks(raw)[0]['data'],data)
