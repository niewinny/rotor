'''
Copyright (C) 2015-2024 Team C All Rights Reserved

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

bl_info = {
    'name': "rotor",
    'description': "Mirroring objects easily with a gizmo",
    'author': "ezelar.com",
    'version': (1, 1, 0),
    'blender': (4, 0, 0),
    'location': 'View3D',
    'wiki_url': '',
    'category': '3D View'}

from . import registry, preferences, utils, ops, tools, btypes


def register():
    registry.register()


def unregister():
    registry.unregister()
