"""Recovered metadata-keyed body tree removal.

Evidence: LINK_SOLVER.md, Body metadata tree removal.
"""
import struct


def _i(raw,offset):return struct.unpack_from('<i',raw,offset)[0]
def _u(raw,offset):return struct.unpack_from('<I',raw,offset)[0]
def _q(raw,offset):return struct.unpack_from('<Q',raw,offset)[0]
def _set(raw,offset,value):struct.pack_into('<i',raw,offset,value)


class _Tree:
    def __init__(self,descriptor,nodes):
        self.d=descriptor;self.n=nodes
    def link(self,index,offset):return _i(self.n,index*32+offset)
    def write(self,index,offset,value):_set(self.n,index*32+offset,value)
    def color(self,index):return self.n[index*32+12] if index!=-1 else 0
    def paint(self,index,color):self.n[index*32+12]=color
    def rotate(self,index,left):
        side=4 if left else 0;opposite=0 if left else 4
        pivot=self.link(index,side);middle=self.link(pivot,opposite);parent=self.link(index,8)
        self.write(index,8,pivot);self.write(index,side,middle)
        self.write(pivot,opposite,index);self.write(pivot,8,parent)
        if parent==-1:_set(self.d,0x14,pivot)
        else:self.write(parent,0 if self.link(parent,0)==index else 4,pivot)
        if middle!=-1:self.write(middle,8,index)

    def unlink(self,index):
        child=self.link(index,0)
        if child==-1:child=self.link(index,4)
        parent=self.link(index,8)
        if parent==-1:_set(self.d,0x14,child)
        else:self.write(parent,0 if self.link(parent,0)==index else 4,child)
        if child!=-1:self.write(child,8,parent)
        if self.color(index)!=0:return
        if child!=-1:
            self.paint(child,0);return
        while parent!=-1:
            sibling=self.link(parent,4 if child==self.link(parent,0) else 0)
            if self.color(sibling)==1:
                self.paint(parent,1);self.paint(sibling,0)
                self.rotate(parent,child==self.link(parent,0))
                sibling=self.link(parent,4 if child==self.link(parent,0) else 0)
            left=self.color(self.link(sibling,0));right=self.color(self.link(sibling,4))
            pc=self.color(parent)
            if pc==0 and left==0 and right==0:
                self.paint(sibling,1);child=parent;parent=self.link(parent,8);continue
            if pc==1 and left==0 and right==0:
                self.paint(sibling,1);self.paint(parent,0);return
            if child==self.link(parent,0) and left==1 and right==0:
                self.paint(sibling,1);self.paint(self.link(sibling,0),0);self.rotate(sibling,False)
            elif child==self.link(parent,4) and right==1 and left==0:
                self.paint(sibling,1);self.paint(self.link(sibling,4),0);self.rotate(sibling,True)
            sibling=self.link(parent,4 if child==self.link(parent,0) else 0)
            self.paint(sibling,self.color(parent));self.paint(parent,0)
            if child==self.link(parent,0):
                self.paint(self.link(sibling,4),0);self.rotate(parent,True)
            else:
                self.paint(self.link(sibling,0),0);self.rotate(parent,False)
            return

    def remove(self,index):
        original=index
        if self.link(index,0)!=-1 and self.link(index,4)!=-1:
            index=self.link(index,0)
            while self.link(index,4)!=-1:index=self.link(index,4)
            self.n[original*32+24:original*32+28]=self.n[index*32+24:index*32+28]
            self.n[original*32+16:original*32+24]=self.n[index*32+16:index*32+24]
        self.unlink(index)
        active=_i(self.d,8);free=_i(self.d,12)
        if index<active+free-1:
            self.n[index*32+13]=1
            head=_i(self.d,0x18)
            self.write(index,4,head);self.write(index,0,-1)
            if head!=-1:self.write(head,0,index)
            _set(self.d,12,free+1);_set(self.d,8,active-1);_set(self.d,0x18,index)
        else:
            if free:
                tail=index-1
                while tail>=0 and self.n[tail*32+13]:
                    following=self.link(tail,4);previous=self.link(tail,0)
                    if following!=-1:self.write(following,0,previous)
                    if previous!=-1:self.write(previous,4,following)
                    else:_set(self.d,0x18,following)
                    _set(self.d,12,_i(self.d,12)-1);tail-=1
            _set(self.d,8,active-1)


def remove_pose_tree_body(descriptor,body_token,*,bodies,metadata,node_arrays,destroy):
    """Find body.metadata54, remove its node, destroy the original nonnull value.

    destroy(value_token,1) supplies virtual destruction. Missing keys are a no-op.
    Nodes are32 bytes: left/right/parent at0/4/8, red byte12, free byte13,
    value16 and uint32 key24. Descriptor has pointer0, active8, free12, root20,
    free-list head24. Remaining bytes and retired node payloads are preserved.
    """
    key=_u(metadata[_q(bodies[body_token],0x30)],0x54)
    index=_i(descriptor,0x14)
    if index==-1:return
    nodes=node_arrays[_q(descriptor,0)];tree=_Tree(descriptor,nodes)
    while index!=-1:
        node_key=_u(nodes,index*32+24)
        if key==node_key:
            value=_q(nodes,index*32+16)
            tree.remove(index)
            if value:destroy(value,1)
            return
        index=tree.link(index,0 if key<node_key else 4)
