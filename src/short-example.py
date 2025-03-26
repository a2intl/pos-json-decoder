import json
from pos_json_decoder import PositionalJSONDecoder
tree = json.loads('{\n"firstkey":"firstval"}', cls=PositionalJSONDecoder)
kpos = list(tree.keys())[0].jsonpos # awkward way to get dict key position
print(f"position of firstkey (hard) is {kpos.line=} {kpos.col=} {kpos.char=} / {kpos}")
kpos = tree["firstkey"].jsonkeypos # easier way to get dict key position
print(f"position of firstkey (easy) is {kpos.line=} {kpos.col=} {kpos.char=} / {kpos}")
vpos = tree["firstkey"].jsonpos
print(f"position of firstval is {vpos.line=} {vpos.col=} {vpos.char=} / {vpos}")
print(f"extent of tree is {tree.jsonpos} -to- {tree.jsonpos.end}")
