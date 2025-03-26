import unittest
import json
from pos_json_decoder import PositionalJSONDecoder

def lcc(pos):
    return (pos.line, pos.col, pos.char)

def elcc(pos):
    return(pos.endline, pos.endcol, pos.endchar)
    
class TestPositionalJSONDecoder(unittest.TestCase):

    def test_simple_object(self):
        json_data = '{"key":\n"value"}'
        tree = json.loads(json_data, cls=PositionalJSONDecoder)
        key_pos = list(tree.keys())[0].jsonpos
        value_pos = tree["key"].jsonpos
        
        self.assertEqual(lcc(key_pos), (1,2,1))
        self.assertEqual(elcc(key_pos), (1,6,5))
        self.assertEqual(lcc(value_pos), (2,1,8))
        self.assertEqual(elcc(value_pos), (2,7,14))
        self.assertEqual(lcc(tree.jsonpos), (1,1,0))
        self.assertEqual(elcc(tree.jsonpos), (2,8,15))
    
    def test_everything_object(self):
        json_data = '''{
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
            "arraykey" :["a",1,NaN,true],
            "nankey2"  :NaN
        }'''
        tree = json.loads(json_data, cls=PositionalJSONDecoder)

        for i,(k,v) in enumerate(tree.items()):
            self.assertEqual(k.jsonpos.line, i+2)
            self.assertEqual(k.jsonpos.col, 13)
            self.assertEqual(k.jsonpos.endline, i+2)
            self.assertEqual(k.jsonpos.endcol, 13+len(k)+1)
            self.assertEqual(v.jsonkeypos, k.jsonpos)
            self.assertEqual(v.jsonpos.line, i+2)
            self.assertEqual(v.jsonpos.col, 25)
            self.assertEqual(v.jsonpos.endline, i+2)
            self.assertEqual(json_data[v.jsonpos.endchar+1], ',' if k != 'nankey2' else '\n')
    
    def test_array(self):
        json_data = '[10, 20, 30]'
        tree = json.loads(json_data, cls=PositionalJSONDecoder)
        
        self.assertEqual(lcc(tree[0].jsonpos), (1,2,1))
        self.assertEqual(elcc(tree[0].jsonpos), (1,3,2))
        self.assertEqual(lcc(tree[1].jsonpos), (1,6,5))
        self.assertEqual(elcc(tree[1].jsonpos), (1,7,6))
        self.assertEqual(lcc(tree[2].jsonpos), (1,10,9))
        self.assertEqual(elcc(tree[2].jsonpos), (1,11,10))
    
    def test_complex_structure(self):
        json_data = '{"data": [{"id": 1}, {"id": 2}, {"id": 3}]}'
        tree = json.loads(json_data, cls=PositionalJSONDecoder)
        
        self.assertEqual(tree["data"][0]["id"].jsonpos.endcol, 18)
        self.assertEqual(tree["data"][1]["id"].jsonpos.endcol, 29)
        self.assertEqual(tree["data"][2]["id"].jsonkeypos.endcol, 37)

    def test_dupe_keys(self):
        json_data = '{"data": 2, "data": 7}'
        tree = json.loads(json_data, cls=PositionalJSONDecoder)

        self.assertEqual(tree["data"], 2)
        self.assertEqual(len(tree.keys()), 2)
        i = iter(tree.items())
        self.assertEqual(next(i), ("data", 2))
        self.assertEqual(next(i), ("data", 7))

    def test_string_concatenation(self):
        json_data = '{"greeting": "Hello"}'
        tree = json.loads(json_data, cls=PositionalJSONDecoder)
        greeting = tree["greeting"] + " World"
        
        self.assertEqual(greeting, "Hello World")
        self.assertEqual(tree["greeting"].jsonpos.col, 14)
        self.assertEqual(tree["greeting"].jsonpos.endcol, 20)
        self.assertEqual(greeting.jsonpos.col, 14)
        self.assertEqual(greeting.jsonpos.endcol, 26)
        
if __name__ == '__main__':
    unittest.main()
