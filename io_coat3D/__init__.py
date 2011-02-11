# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "3D-Coat Applink",
    "author": "Kalle-Samuli Riihikoski (haikalle)",
    "version": (1, 70),
    "blender": (2, 5, 6),
    "api": 34481,
    "location": "Scene > 3D-Coat Applink",
    "description": "Transfer data between 3D-Coat/Blender",
    "warning": "",
    "wiki_url": "http://wiki.blender.org/index.php/Extensions:2.5/Py/" \
        "Scripts/Import-Export/3dcoat_applink",
    "tracker_url": "https://projects.blender.org/tracker/?"\
        "func=detail&aid=24446",
    "category": "Import-Export"}



if "bpy" in locals():
    import imp
    imp.reload(coat)
    imp.reload(tex)
else:
    from . import coat
    from . import tex

import bpy
from bpy.props import *

    
def register():
    bpy.utils.register_module(__name__)


    bpy.coat3D = dict()
    bpy.coat3D['active_coat'] = ''
    bpy.coat3D['status'] = 0
    bpy.coat3D['kuva'] = 1
    
    class coat3D(bpy.types.IDPropertyGroup):
        pass
        
    bpy.types.Object.coat3D= PointerProperty(
        name= "Applink Variables",
        type=  coat3D,
        description= "Applink variables"
    )

    coat3D.objpath = StringProperty(
        name="Object_Path",
        default= ""
    )

    coat3D.coatpath = StringProperty(
        name="Coat_Path",
        default= ""
    )

    coat3D.objectdir = StringProperty(
        name="ObjectPath",
        subtype="FILE_PATH",
        default= ""
    )

    coat3D.texturefolder = StringProperty(
        name="Texture folder:",
        subtype="DIR_PATH",
        default= ""
    )

    coat3D.path3b = StringProperty(
        name="3B Path",
        subtype="FILE_PATH",
        default= ""
    )


    class coat3D(bpy.types.IDPropertyGroup):
        pass

    bpy.types.Scene.coat3D= PointerProperty(
        name= "Applink Variables",
        type=  coat3D,
        description= "Applink variables"
    )

    coat3D.exchangedir = StringProperty(
        name="FilePath",
        subtype="DIR_PATH",
        default= ""
    )

    coat3D.wasactive = StringProperty(
        name="Pass active object",
        default= ""
    )

    coat3D.import_box = BoolProperty(
        name="Import window",
        description="Allows to skip import dialog.",
        default= True
    )

    coat3D.export_box = BoolProperty(
        name="Export window",
        description="Allows to skip export dialog.",
        default= True
    )

    coat3D.export_color = BoolProperty(
        name="Export color",
        description="Export color texture.",
        default= True
    )

    coat3D.export_spec = BoolProperty(
        name="Export specular",
        description="Export specular texture.",
        default= True
    )

    coat3D.export_normal = BoolProperty(
        name="Export Normal",
        description="Export normal texture.",
        default= True
    )

    coat3D.export_disp = BoolProperty(
        name="Export Displacement",
        description="Export displacement texture.",
        default= True
    )

    coat3D.export_position = BoolProperty(
        name="Export Source Position",
        description="Export source position.",
        default= True
    )

    coat3D.export_zero_layer = BoolProperty(
        name="Export from Layer 0",
        description="Export mesh from Layer 0",
        default= True
    )

    coat3D.export_coarse = BoolProperty(
        name="Export Coarse",
        description="Export Coarse.",
        default= True
    )
    

    coat3D.export_on = BoolProperty(
        name="Export_On",
        description="Add Modifiers and export.",
        default= False
    )

    coat3D.smooth_on = BoolProperty(
        name="Auto Smooth",
        description="Add Modifiers and export.",
        default= True
    )

    coat3D.exportfile = BoolProperty(
        name="No Import File",
        description="Add Modifiers and export.",
        default= False
    )

    coat3D.importmod = BoolProperty(
        name="Remove Modifiers",
        description="Import and add modifiers.",
        default= True
    )

    coat3D.exportmod = BoolProperty(
        name="Modifiers",
        description="Export modifiers.",
        default= False
    )

    coat3D.export_pos = BoolProperty(
        name="Remember Position",
        description="Remember position.",
        default= True
    )

    coat3D.importtextures = BoolProperty(
        name="Bring Textures",
        description="Import Textures.",
        default= True
    )

    coat3D.exportover = BoolProperty(
        name="Export Obj",
        description="Import Textures.",
        default= False
    )

    coat3D.importmesh = BoolProperty(
        name="Mesh",
        description="Import Mesh.",
        default= True
    )

    #copy location

    coat3D.cursor = FloatVectorProperty(
        name="Cursor",
        description="Location.",
        subtype="XYZ",
        default=(0.0, 0.0, 0.0)
    )

    coat3D.loca = FloatVectorProperty(
        name="location",
        description="Location.",
        subtype="XYZ",
        default=(0.0, 0.0, 0.0)
    )

    coat3D.rota = FloatVectorProperty(
        name="location",
        description="Location.",
        subtype="EULER",
        default=(0.0, 0.0, 0.0)
    )

    coat3D.scal = FloatVectorProperty(
        name="location",
        description="Location.",
        subtype="XYZ",
        default=(0.0, 0.0, 0.0)
    )

    coat3D.dime = FloatVectorProperty(
        name="dimension",
        description="Dimension.",
        subtype="XYZ",
        default=(0.0, 0.0, 0.0)
    )

    coat3D.type = EnumProperty( name= "Export Type",
    description= "Diffrent Export Types.",
    items=(
        ("ppp",   "Per-Pixel Painting", ""),
        ("mv",   "Microvertex Painting", ""),
        ("ptex",   "Ptex Painting", ""),
        ("uv",   "UV-Mapping", ""),
        ("ref",  "Reference Mesh", ""),
        ("retopo",  "Retopo mesh as new layer", ""),
        ("vox",  "Mesh As Voxel Object", ""),
        ("alpha",  "Mesh As New Pen Alpha", ""),
        ("prim",  "Mesh As Voxel Primitive", ""),
        ("curv", "Mesh As a Curve Profile", ""),
        ("autopo",  "Mesh For Auto-retopology", ""),
    ),
    default= "ppp"
    )


def unregister():
    bpy.utils.unregister_module(__name__)

    import bpy

    del bpy.types.Object.coat3D
    del bpy.types.Scene.coat3D
    del bpy.coat3D
    


if __name__ == "__main__":
    register()



