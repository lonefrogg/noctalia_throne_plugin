"""Execute Lua-compatible Luau entries against a mock host, without a desktop."""
import ctypes
import ctypes.util
from pathlib import Path
import tomllib
import unittest

ROOT=Path(__file__).resolve().parents[1]


class NativeTests(unittest.TestCase):
    def test_entries_settings_actions_icons_search_and_scroll_constraints(self):
        name=ctypes.util.find_library('lua5.4')
        if not name: self.skipTest('liblua5.4 is not installed')
        lib=ctypes.CDLL(name)
        lib.luaL_newstate.restype=ctypes.c_void_p
        lib.luaL_openlibs.argtypes=[ctypes.c_void_p]
        lib.luaL_loadbufferx.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_char_p]
        lib.luaL_loadbufferx.restype=ctypes.c_int
        lib.lua_pcallk.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_longlong,ctypes.c_void_p]
        lib.lua_pcallk.restype=ctypes.c_int
        lib.lua_tolstring.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p]
        lib.lua_tolstring.restype=ctypes.c_char_p
        lib.lua_close.argtypes=[ctypes.c_void_p]
        path=str(ROOT/'throne-vpn')
        # Lua long strings avoid interpreting backslashes in filesystem paths.
        plugin_id=tomllib.loads((ROOT/'throne-vpn/plugin.toml').read_text())['id']
        code=(ROOT/'tests/native_host_test.lua').read_text().replace('"__PLUGIN_ROOT__/"','[=['+path+'/]=]').replace('__PLUGIN_ID__',plugin_id)
        vm=lib.luaL_newstate()
        try:
            lib.luaL_openlibs(vm);raw=code.encode()
            status=lib.luaL_loadbufferx(vm,raw,len(raw),b'host-test',None)
            if status==0: status=lib.lua_pcallk(vm,0,0,0,0,None)
            self.assertEqual(status,0,(lib.lua_tolstring(vm,-1,None) or b'').decode())
        finally: lib.lua_close(vm)
