"""Versioned JSON resource registry with explicit evidence and replacement policy."""
import copy
import hashlib
import json
CATEGORIES={'synthetic','asset-decoded','binary-derived','video-estimated','studio-authored-substitute'}
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
class ResourceStore:
    def __init__(self):self._resources={};self.generation=0
    def add(self,record,replace=False):
        record=copy.deepcopy(record)
        if set(record)!={'id','kind','category','data'}:raise ValueError("Resource needs id, kind, category, data")
        if not isinstance(record['id'],str) or not record['id']:raise ValueError("Resource id required")
        if record['category'] not in CATEGORIES:raise ValueError("Evidence category required")
        canonical(record)
        if record['id'] in self._resources and not replace:raise ValueError("Duplicate resource id")
        self._resources[record['id']]=record;self.generation+=1
        return digest(record)
    def get(self,key):
        if key not in self._resources:raise KeyError(f"Unresolved resource: {key}")
        return copy.deepcopy(self._resources[key])
    def export(self):return dict(schema_version=1,generation=self.generation,resources=copy.deepcopy(self._resources))
