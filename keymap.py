import bpy

keys = []


def object_mode_hotkeys(kc):
    '''Object Mode Hotkeys'''

    km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
    # menu hotkey 
    kmi = km.keymap_items.new('rotor.set_active_tool', 'X', 'PRESS',  alt=True)
    keys.append((km, kmi))
    
    # ESC to return to previous tool when mirror tool is active
    kmi = km.keymap_items.new('rotor.fallback_tool', 'ESC', 'PRESS')
    kmi.active = True
    keys.append((km, kmi))

def register():
    '''Register Keymaps'''

    wm = bpy.context.window_manager
    active_keyconfig = wm.keyconfigs.active
    addon_keyconfig = wm.keyconfigs.addon

    kc = addon_keyconfig

    object_mode_hotkeys(kc)

    del active_keyconfig
    del addon_keyconfig


def unregister():
    '''Unregister Keymaps'''

    for km, kmi in keys:
        km.keymap_items.remove(kmi)

    keys.clear()
