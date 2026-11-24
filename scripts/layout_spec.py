"""Portable certificate layout overrides. Coordinates are percentages of the page."""
import json
import math
import re
from pathlib import Path

KEYS={'heading','group','body','award','members','note','signature'}
def validate(value):
    if not isinstance(value,dict) or value.get('version')!=1 or not isinstance(value.get('layers'),dict):
        raise ValueError('请选择版本 1 的映印布局方案')
    if len(value['layers'])>30:raise ValueError('布局最多 30 个文本块')
    for key,layer in value['layers'].items():
        if key not in KEYS and not re.fullmatch(r'extra_[0-9]{1,8}',key):raise ValueError('未知文本块')
        if not isinstance(layer,dict) or not isinstance(layer.get('text'),str) or len(layer['text'])>4000:raise ValueError('文本内容无效或过长')
        if layer.get('align') not in ('left','center','right') or type(layer.get('visible')) is not bool:raise ValueError('文本对齐或显示设置无效')
        for name,lo,hi in [('x',0,100),('y',0,100),('pt',1,150),('width',1,100)]:
            n=layer.get(name)
            if type(n) not in (int,float) or not math.isfinite(n) or not lo<=n<=hi:raise ValueError('布局数值超出范围：'+name)
    return value

def read(path):
    return validate(json.loads(Path(path).read_text(encoding='utf-8-sig')))
