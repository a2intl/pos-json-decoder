import json
try:
    from functools import cached_property
except:
    cached_property = lambda f: f
import re

class PositionalJSONDecoder:
    """
    # DESCRIPTION
    
    An adaptation of JSONDecoder that records the document position of every JSON element parsed,
    which can be accessed via an attribute `.jsonpos` on the parsed elements, and from the hook
    function parameters.
    
    JSON parsing using this decoder returns elements that are subclassed instances of
    dict/list/str/int/float/bool/None having an additional attribute '.jsonpos' of type `JsonPos`,
    which has the following attributes and methods:
    
        line      : line number of start of element (1-based)
        col       : column number of start of element (1-based)
        char      : character offset of start of element (in entire parsed JSON string) (0-based)
        endline   : line number of end of element (1-based)
        endcol    : column number of end of element (1-based0
        endchar   : character offset of end of element (in entire parsed JSON string) (0-based)
        __str__() : start position as a human-readable string: "line L column C (char P)"
        end       : end position as a human-readable string
    
    Additionally, values retrieved from a `dict` (JSON Object) lookup will have a '.jsonkeypos'
    attribute that gives the position of its key (as looking up a key's value is simple, but
    retrieving a key itself from a `dict` is difficult).

    All parsed elements also have a `.rawval` attribute that returns the "raw" value of the same
    type that would have been returned by `JSONDecoder`.

    The `object_pairs_hook`, `object_hook`, `parse_int`, `parse_float`, and `parse_constant` hooks
    (passed to `json.load/loads` or the `PositionalJSONDecoder` constructor) will be passed
    `JsonPos`-annotated strings. Plain dicts/ints/floats can be returned from these functions, and
    they will be position-annotated in the final returned JSON tree structure, although
    `object_pairs_hook` and `object_hook` should return a `dict` populated with the
    `JsonPos`-annotated objects provided in order to maintain their position info.

    # CAVEATS
    
    The position-annotated `bool` & `None` values emulate their constants imperfectly. They compare
    via `==`, booleanize, and stringize properly, but return `False` when compared using the `is`
    operator to the `True`/`False`/`None` constants. The `.rawval` attribute can be used to obtain
    the "native" value if needed.

    Position-annotated `str` types (`StringPos`) compare equal only with themselves, exact copies of
    themselves, or plain strings with the same string value (so `dict` lookups can still use plain
    strings). This leads to non-obvious behavior if they are mixed with plain strings as `dict` keys,
    and means duplicate object keys in JSON will result in a `dict` with multiple keys with the same
    string value (but different `.jsonpos` values), which requires iteration with `.keys()` or
    `.items()` to retrieve all the duplicate keys.
    
    The line and column numbers are not computed until requested (only the char offset is recorded)
    for some efficiency. The pure-python `json.scanner.py_make_scanner` JSON parser is used, so this
    decoder will be slower than native `JSONDecoder` which uses the C-scanner.

    Copies of the entire parsed JSON string are stored in the `JsonPos` objects, however, they
    should all be refcounted references to only a single copy of the actual string. During parsing,
    many small additional `JsonPos` and wrapper objects are created, so this decoder may not
    suitable for parsing very large JSON, or keeping results from a large number of JSON parses in
    memory simultaneously.

    # USAGE
    
    The usage is nearly identical to JSONDecoder, namely:
     
    tree = json.load(json_file, cls=PositionalJSONDecoder, ...)
    # OR
    tree = json.loads(json_string, cls=PositionalJSONDecoder, ...)
    # OR
    decoder = PositionalJSONDecoder()
    tree = decoder.parse(json_string)
    tree, endpos = decoder.raw_parse(json_string, startpos)

    # EXAMPLE

    import json
    from pos_decoder import PositionalJSONDecoder
    tree = json.loads('{\n"firstkey":"firstval"}', cls=PositionalJSONDecoder)
    kpos = list(tree.keys())[0].jsonpos # awkward way to get dict key position
    print(f"position of firstkey (hard) is {kpos.line=} {kpos.col=} {kpos.char=} / {kpos}")
    kpos = tree["firstkey"].jsonkeypos # easier way to get dict key position
    print(f"position of firstkey (easy) is {kpos.line=} {kpos.col=} {kpos.char=} / {kpos}")
    vpos = tree["firstkey"].jsonpos
    print(f"position of firstval is {vpos.line=} {vpos.col=} {vpos.char=} / {vpos}")
    print(f"extent of tree is {tree.jsonpos} -to- {tree.jsonpos.end}")

    # OUTPUT
    position of firstkey (hard) is kpos.line=2 kpos.col=1 kpos.char=2 / line 2 column 1 (char 2)
    position of firstkey (easy) is kpos.line=2 kpos.col=1 kpos.char=2 / line 2 column 1 (char 2)
    position of firstval is vpos.line=2 vpos.col=12 vpos.char=13 / line 2 column 12 (char 13)
    extent of tree is line 1 column 1 (char 0) -to- line 2 column 22 (char 23)

    """
    
    class JsonPos:
        """ a position object that records start and end positions in a string """
        current_decoder = None
        def __init__(self, s, start, end):
            self.s = s # the entire JSON string that was parsed
            self.startpos = start
            self.endpos = end
            if self.current_decoder:
                self.current_decoder.lastpos = (s,end)

        @cached_property
        def serr(self):
            return json.decoder.JSONDecodeError('', self.s, self.startpos)
        @cached_property
        def eerr(self):
            return json.decoder.JSONDecodeError('', self.s, self.endpos)
        
        def __str__(self):
            return str(self.serr)[2:]
        @property
        def end(self):
            return str(self.eerr)[2:]
        @property
        def line(self):
            return self.serr.lineno
        @property
        def col(self):
            return self.serr.colno
        @property
        def char(self):
            return self.serr.pos
        @property
        def endline(self):
            return self.eerr.lineno
        @property
        def endcol(self):
            return self.eerr.colno
        @property
        def endchar(self):
            return self.eerr.pos

    def init_pos_instance(self, val, pos):
        """ create a (position-wrapped) dict/list instance with the given native value and JsonPos """
        if isinstance(val, self.__class__) and val.jsonpos:
            return val
        super(type(self), self).__init__(val)
        self.jsonpos = pos
        self.jsonkeypos = None
        self.rawval = val
        return self
            
    class DictPos(dict):
        """ a dict (JSON Object) enhanced with JsonPos position information """
        def __init__(self, val, pos):
            PositionalJSONDecoder.init_pos_instance(self, val, pos)
            for k,v in self.items():
                if not v.jsonkeypos and k.jsonpos:
                    v.jsonkeypos = k.jsonpos

    class ArrayPos(list):
        """ a list (JSON Array) enhanced with JsonPos position information """
        def __init__(self, val, pos):
            PositionalJSONDecoder.init_pos_instance(self, val, pos)

    @staticmethod
    def make_pos_instance(cls, val, args, jsonpos):
        """ create an (position-wrapped) immutable instance (str/int/float) with the given value, new-args, and JsonPos """
        if type(val) is cls and val.jsonpos:
            return val
        instance = cls.mro()[1].__new__(cls, *args)
        instance.jsonpos = jsonpos
        instance.jsonkeypos = None
        instance.rawval = val
        return instance
    
    class StringPos(str):
        """ a string enhanced with JsonPos position information """
        def __new__(cls, val, jsonpos):
            return PositionalJSONDecoder.make_pos_instance(cls, val, [val], jsonpos)
        def __add__(self, other):
            """ maintains position info when concatenating strings
                needed because float parsing uses str.__add__ on re.Match.groups
            """
            val = str(self) + str(other)
            start = self.jsonpos.startpos
            jsonpos = PositionalJSONDecoder.JsonPos(self.jsonpos.s, self.jsonpos.startpos, self.jsonpos.endpos+len(other))
            return PositionalJSONDecoder.make_pos_instance(self.__class__, val, [val], jsonpos)
        def __eq__(self, other):
            if self is other:
                return True
            if isinstance(other, PositionalJSONDecoder.StringPos):
                # prevents python from sharing string-value-equal keys between dicts (!)
                return str.__eq__(self, other) and self.jsonpos.startpos==other.jsonpos.startpos and self.jsonpos.s.__hash__()==other.jsonpos.s.__hash__()
            else:
                return str.__eq__(self, other) # enables looking up dict entries by plain string key
        def __hash__(self):
            return str.__hash__(self) # enables looking up dict entries by plain string key
            
            
    class IntPos(int):
        """ an integer enhanced with JsonPos position information """
        def __new__(cls, val, jsonpos):
            return PositionalJSONDecoder.make_pos_instance(cls, val, [val], jsonpos)
        
    class FloatPos(float):
        """ a float enhanced with JsonPos position information """
        def __new__(cls, val, jsonpos):
            return PositionalJSONDecoder.make_pos_instance(cls, val, [val], jsonpos)
        
    class ConstantPos:
        """ an emulation of the None/True/False constants, enhanced with JsonPos position information """
        __bool__   = lambda s: s.rawval.__bool__()
        __hash__   = lambda s: s.rawval.__hash__()
        __str__    = lambda s: s.rawval.__str__()
        __repr__   = lambda s: s.rawval.__repr__()
        __eq__     = lambda s, o: s.rawval.__eq__(o)
        __format__ = lambda s, f: s.rawval.__format__(f)
        def __new__(cls, val, jsonpos):
            r = PositionalJSONDecoder.make_pos_instance(cls, val, [], jsonpos)
            return r

    def parse_obj_wrap(self, wrapped, pos_creator, se, *args, **kwargs):
        """wraps dict and list creation functions JSONObject/JSONArray returning DictPos/ArrayPos objects"""
        s, start = se
        r, end = wrapped(se, *args, **kwargs)
        pos = self.JsonPos(s, start-1, end-1)
        return pos_creator(r, pos), end

    def parse_str_wrap(self, wrapped, s, start, *args, **kwargs):
        """wraps string creation function scan_string returning StringPos objects"""
        r, end = wrapped(s, start, *args, **kwargs)
        pos = self.JsonPos(s, start-1, end-1)
        return self.StringPos(r, pos), end

    """ the position-enhanced immutable-object constructors, indexed by type """
    pos_creators = {
        int        : IntPos,
        float      : FloatPos,
        bool       : ConstantPos,
        type(None) : ConstantPos,
    }
    
    def scan_once_wrap(self, wrapped, s, start):
        """wraps json.scanner.scan_once, to return IntPos/FloatPos/ConstantPos objects"""
        r, end = wrapped(s, start)
        creator = self.pos_creators.get(type(r))
        if creator:
            pos = self.JsonPos(s, start, end-1)
            return creator(r, pos), end
        else:
            return r, end

    class ReMatchPos:
        """ Emulates an `re.Match` object, but returns `StringPos` match groups.
            Needed because float parsing uses `str.__add__` on `re.Match.groups`
        """
        def __init__(self, string, match):
            self.string = string
            self.match = match
        def groups(self, default=None):
            m = self.match
            cls = PositionalJSONDecoder
            return [cls.StringPos(grp, cls.JsonPos(self.string, m.start(idx), m.end(idx)-1))
                    if grp is not default else default for idx, grp in enumerate(m.groups(default))]
        def end(self, *args):
            return self.match.end(*args)

    def match_number_wrap(self, oldmatch, string, idx):
        """ wraps the json.scanner.match_number function to return a ReMatchPos instead of a re.Match """
        m = oldmatch(string, idx)
        return m and self.ReMatchPos(string, m) # returns None if m is None

    def wrap_func(self, wrapper, *firstargs):
        """utility function to create a wrapper function that calls `wrapper` passing additional
           inital arguments `firstargs`, which typically include the "to-be-wrapped" old function
        """
        return lambda *a, **kw: wrapper(*firstargs, *a, **kw)

    def wrap_constant(self, constant):
        """wraps the next-found constant string `NaN/Infinity/-Infinity` with location info for the
           `parse_constant` hook
        """
        lasts, lastend = self.lastpos
        idx = lasts.find(constant, lastend)
        if idx != -1:
            return self.StringPos(constant, self.JsonPos(lasts, idx, idx+len(constant)-1))
        else:
            return constant

    def __init__(self, *args, **kwargs):
        """ creates a new PositionalJSONEncoder, taking all the same arguments as JSONDecoder """
        inner = self.inner     = json.JSONDecoder(*args, **kwargs)
        self.object_hook       = inner.object_hook
        self.parse_float       = inner.parse_float
        self.parse_int         = inner.parse_int
        self.parse_constant    = lambda s: inner.parse_constant(self.wrap_constant(s))
        self.strict            = inner.strict
        self.object_pairs_hook = inner.object_pairs_hook
        self.parse_object      = self.wrap_func(self.parse_obj_wrap, inner.parse_object, self.DictPos)
        self.parse_array       = self.wrap_func(self.parse_obj_wrap, inner.parse_array, self.ArrayPos )
        self.parse_string      = self.wrap_func(self.parse_str_wrap, inner.parse_string)
        self.memo              = inner.memo
        self.scan_once         = json.scanner.py_make_scanner(self)

    class AttrSaver:
        """A context manager that saves and restores the value of an object's attribute.  Also
           provides a settor `mgr.settor(newval)` and the saved value `mgr.saved`.

          myobj.attrname = 7
          with AttrSaver(myobj, 'attrname', lambda oldval: oldval+1):
             print(myobj.attrname) # prints "8"
          print(myobj.attrname) # prints "7"
        """
        def __init__(self, obj, attrname, f=None, newval=None):
            """
                obj     : the base object holding the attribute
                attrname: the attribute name to save, set, and restore
                f       : a function, passed the saved value, returning the new attribute value
                newval  : if `f` not passed, the new attribute value to be set
            """
            self.obj = obj
            self.attrname = attrname
            self.setfunc = f
            self.newval = newval
            self.settor = lambda newval: setattr(self.obj, self.attrname, newval)

        def __enter__(self):
            """ enters the manager context, saving the value of the attribute """
            self.saved = getattr(self.obj, self.attrname)
            if self.setfunc:
                self.settor(self.setfunc(self.saved))
            elif self.newval:
                self.settor(self.newval)
            return self
            
        def __exit__(self, *exception_info):
            """ exits the manager context, restoring the saved value of the attribute """
            self.settor(self.saved)
            return False # re-raise any exceptions thrown

    def find_closure(self, func, name):
        """ Finds a closure by name in a function. `c.cell_contents` is value of the closure """
        try:
            return func.__closure__[func.__code__.co_freevars.index(name)]
        except:
            return None

    def override_closure(self, func, name, newfunc):
        """overrides using `AttrSaver` the closure variable named `name` in `func` replacing it
           with the return value of `newfunc(oldval)`
        """
        return self.AttrSaver(self.find_closure(func, name), 'cell_contents', newfunc)
            
    def decode(self, *args, **kwargs):
        """ the replacement for JSONDecoder.decoder """
        return self.inner.__class__.decode(self, *args, **kwargs)

    def raw_decode(self, s, idx=0):
        """ the replacement for JSONDecoder.raw_decoder """

        # Override some json-internal functions to pass `JsonPos`-enhanced objects to the hooks,
        # restoring the functions to their original values after parsing is finished:
        # * `json.decoder.scanstring`, used to parse `dict` key strings
        # * `scan_once._scan_once`, returns the parsed tokens of types int/float/bool/None
        # * `NUMBER_RE.match` / `_scan_once.match_number`, returns an `re.Match` object for
        #   tokens parsing as `int` or `float` numbers

        with self.AttrSaver(json.decoder, 'scanstring',
                            lambda oldfunc: self.wrap_func(self.parse_str_wrap, oldfunc)), \
             self.override_closure(self.scan_once, '_scan_once',
                                   lambda oldfunc: self.wrap_func(self.scan_once_wrap, oldfunc)) as scan_once_mgr, \
             self.override_closure(scan_once_mgr.saved, 'match_number',
                                   lambda oldfunc: self.wrap_func(self.match_number_wrap, oldfunc)), \
             self.AttrSaver(self.JsonPos, 'current_decoder', newval=self) as cd:
            self.lastpos = (s, idx)
            (val, end) = self.inner.__class__.raw_decode(self, s, idx)
                
            # outermost object returns position off-by-one for some reason
            return val, end
