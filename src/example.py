import json
from pos_json_decoder import PositionalJSONDecoder

def pairs_hook(pairs):
    for k,v in pairs:
        print(f"hook: {k=:10} {str(v)=:12} {str(k.jsonpos)=:28} {str(v.jsonpos)=:28}")
    return dict(pairs)

def num_hook(conv,num):
    print(f"num_hook: {conv.__name__} {num=} {num.jsonpos} -to- {num.jsonpos.end}")
    return conv(num)

def const_hook(str):
    print(f"const_hook: {str=} {str.jsonpos} -to- {str.jsonpos.end}")
    return float(str.lower()[0:(4 if str[0]=="-" else 3)])

JSON = '''{
    "firstkey" :"firstval",
    "intkey"   :7,
    "floatkey" :7.5,
    "nankey"   :NaN,
    "infkey"   :Infinity,
    "-infkey"  :-Infinity,
    "truekey"  :true,
    "falsekey" :false,
    "nullkey"  :null,
    "objkey"   :{"a": 1},
    "arraykey" :["element1"],
    "nankey2"  :NaN
}'''

tree = json.loads(JSON, cls=PositionalJSONDecoder, object_pairs_hook=pairs_hook,
                  parse_int=lambda s: num_hook(int,s), parse_float=lambda s: num_hook(float,s), parse_constant=const_hook)

kpos = list(tree.keys())[0].jsonpos # awkward way to get dict key position
print(f"position of firstkey (hard) is {kpos.line=} {kpos.col=} {kpos.char=} / {kpos}")
kpos = tree["firstkey"].jsonkeypos # easier way to get dict key position
print(f"position of firstkey (easy) is {kpos.line=} {kpos.col=} {kpos.char=} / {kpos}")
print(f"extent of tree is {tree.jsonpos} -to- {tree.jsonpos.end}")
for k, v in tree.items():
    print(f"{k=:10} {str(v.jsonpos)=:28} {str(v.jsonpos.end)=:28}")
for k, v in tree.items():
    print(f"{k=:10} {str(v.jsonkeypos)=:28} {str(v.jsonkeypos.end)=:28}")
    
nullval=tree["nullkey"]
print(f"nullval (None-ish) properties: {(nullval is None)=}, {(nullval==None)=}, {(nullval or 7)=}")
print(f"{str(nullval)=}, {nullval=}, {type(nullval)=}")

def pairs_hook2(pairs):
    for k,v in pairs:
        print(f"hook: {k=:10} {str(v)=:12} {type(k)=} {type(v)=}")
    return dict(pairs)

def num_hook2(conv,num):
    print(f"num_hook: {conv.__name__} {type(num)=}")
    return conv(num)

json.loads(JSON, object_pairs_hook=pairs_hook2, parse_int=lambda s: num_hook2(int,s), parse_float=lambda s: num_hook2(float,s))
