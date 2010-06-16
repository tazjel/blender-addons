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

import bpy
from bpy.props import *
from mathutils import Vector, Matrix
import bgl
import blf

bl_addon_info = {
    'name': '3D View: Measure panel',
    'author': 'Buerbaum Martin (Pontiac)',
    'version': '0.7',
    'blender': (2, 5, 3),
    'location': 'View3D > Properties > Measure',
    'description': '* note: script returns errors but works.',
    'wiki_url': 'http://wiki.blender.org/index.php/Extensions:2.5/Py/' \
        'Scripts/3D_interaction/Panel_Measure',
    'tracker_url': 'https://projects.blender.org/tracker/index.php?'\
        'func=detail&aid=21445&group_id=153&atid=469',
    'category': '3D View'}

# More links:
# http://gitorious.org/blender-scripts/blender-measure-panel-script
# http://blenderartists.org/forum/showthread.php?t=177800

__bpydoc__ = """
Measure panel

This script displays in OBJECT MODE:
* The distance of the 3D cursor to the origin of the
  3D space (if NOTHING is selected).
* The distance of the 3D cursor to the center of an object
  (if exactly ONE object is selected).
* The distance between 2 object centers
  (if exactly TWO objects are selected).
* The surface area of any selected mesh object.

Display in EDIT MODE (Local and Global space supported):
* The distance of the 3D cursor to the origin
  (in Local space it is the object center instead).
* The distance of the 3D cursor to a selected vertex.
* The distance between 2 selected vertices.

Usage:

This functionality can be accessed via the
"Properties" panel in 3D View ([N] key).

It's very helpful to use one or two "Empty" objects with
"Snap during transform" enabled for fast measurement.

Version history:
v0.7 - Initial support for drawing lines.
    (Thanks to Algorith for applying my perspective_matrix patch.)
    The distance value (in BUs) is also drawn in the 3D view now.
    Also fixed some wrong calculations of global/local distances.
    Now it's really "what you see is what is calculated".
    Use bl_addon_info for Add-On information.
    Use "3D View" in category & name
    Renamed reenter_editmode to view3d.reenter_editmode.
    Renamed panel_measure.py into space_view3d_panel_measure.py
    Active object is only used for edit-mode now. Measurement
    with exactly one sel. (but not neccessarily active) object
    now gets the obj via the sel-object array.
    API change Mathutils -> mathutils (r557)
    Deselecting 1 of 2 objects now works correctly (active object is ignored).
    Force a redraw of the area so disabling the "measure_panel_draw"
    checkbox will clear the line/text.
    Only calculate area (CPU heavy) if a "area" checkbox is enabled.
v0.6.4 - Fixed unneeded meshdata duplication (sometimes crashes Blender).
    The script now correctly calculated the surface area (faceAreaGlobal)
    of scaled meshes.
    http://projects.blender.org/tracker/
    ?func=detail&atid=453&aid=21913&group_id=153
v0.6.3 - Added register & unregister functions.
v0.6.2 - Fixed precision of second area property.
    Reduced display precision to 5 (instead of 6).
    Added (commented out code) for shortcut [F5] for
    updating EditMode selection & calculation.
    Changed the script so it can be managed from the "Add-Ons" tab
    in the user preferences.
    Corrected FSF address.
v0.6.1 - Updated reenter_editmode operator description.
    Fixed search for selected mesh objects.
    Added "BU^2" after values that are not yet translated via "unit".
v0.6
    *) Fix:  Removed EditMode/ObjectMode toggle stuff. This causes all the
       crashes and is generally not stable.
       Instead I've added a manual "refresh" button.
       I registered a new operator OBJECT_OT_reenter_editmode for this.
    *) Use "unit" settings (i.e. none/metric/imperial)
    *) Fix: Only display surface area (>=3 objects) if return value is >=0.
    *) Minor: Renamed objectFaceArea to objectSurfaceArea
    *) Updated Vector() and tuple() usage.
    *) Fixed some comments.
v0.5 - Global surface area (object mode) is now calculated as well.
    Support area calculation for face selection.
    Also made measurement panel closed by default. (Area calculation
    may use up a lot of CPU/RAM in extreme cases)
v0.4.1 - Various cleanups.
    Using the shorter "scene" instead of "context.scene"
    New functions measureGlobal() and measureLocal() for
    user-friendly access to the "space" setting.
v0.4 - Calculate & display the surface area of mesh
    objects (local space only right now).
    Expanded global/local switch.
    Made "local" option for 3Dcursor-only in edit mode actually work.
    Fixed local/global calculation for 3Dcursor<->vertex in edit mode.
v0.3.2 - Fixed calculation & display of local/global coordinates.
    The user can now select via dropdown which space is wanted/needed
    Basically this is a bugfix and new feature at the same time :-)
v0.3.1 - Fixed bug where "measure_panel_dist" wasn't defined
    before it was used.
    Also added the distance calculation "origin -> 3D cursor" for edit mode.
v0.3 - Support for mesh edit mode (1 or 2 selected vertices)
v0.2.1 - Small fix (selecting nothing didn't calculate the distance
    of the cursor from the origin anymore)
v0.2 - Distance value is now displayed via a FloatProperty widget (and
    therefore saved to file too right now [according to ideasman42].
    The value is save inside the scene right now.)
    Thanks goes to ideasman42 (Campbell Barton) for helping me out on this.
v0.1 - Initial revision. Seems to work fine for most purposes.

TODO:

There is a random segmentation fault when moving the 3D cursor in edit mode.
Mainly this happens when clicking inside the white circle of the translation
manipulator. There may be other cases though.

See the other "todo" comments below.
"""

# Precicion for display of float values.
PRECISION = 4

# Name of the custom properties as stored in the scene.
COLOR_LOCAL = (1.0, 0.0, 0.0, 0.8)
COLOR_GLOBAL = (0.0, 0.0, 1.0, 0.8)


# Returns a single selected object.
# Returns None if more than one (or nothing) is selected.
# Note: Ignores the active object.
def getSingleObject(context):
    if len(context.selected_objects) == 1:
        return context.selected_objects[0]

    return None


# Returns a list with 2 3D points (Vector) and a color (RGBA)
# depending on the current view mode and the selection.
def getMeasurePoints(context):
    sce = context.scene

    # Get a single selected object (or nothing).
    obj = getSingleObject(context)

    if (context.mode == 'EDIT_MESH'):
        obj = context.active_object

        if (obj and obj.type == 'MESH' and obj.data):
            # Get mesh data from Object.
            mesh = obj.data

            # Get transformation matrix from object.
            ob_mat = obj.matrix
            # Also make an inversed copy! of the matrix.
            ob_mat_inv = ob_mat.copy()
            Matrix.invert(ob_mat_inv)

            # Get the selected vertices.
            # @todo: Better (more efficient) way to do this?
            verts_selected = [v for v in mesh.verts if v.selected == 1]

            if len(verts_selected) == 0:
                # Nothing selected.
                # We measure the distance from...
                # local  ... the object center to the 3D cursor.
                # global ... the origin to the 3D cursor.
                cur_loc = sce.cursor_location
                obj_loc = obj.location.copy()

                # Convert to local space, if needed.
                if measureLocal(sce):
                    p1 = cur_loc
                    p2 = obj_loc
                    return (p1, p2, COLOR_GLOBAL)

                else:
                    p1 = Vector((0.0, 0.0, 0.0))
                    p2 = cur_loc
                    return (p1, p2, COLOR_GLOBAL)

            elif len(verts_selected) == 1:
                # One vertex selected.
                # We measure the distance from the
                # selected vertex object to the 3D cursor.
                cur_loc = sce.cursor_location
                vert_loc = verts_selected[0].co.copy()
                obj_loc = obj.location.copy()

                # Convert to local or global space.
                if measureLocal(sce):
                    p1 = obj_loc + vert_loc
                    p2 = cur_loc
                    return (p1, p2, COLOR_LOCAL)

                else:
                    p1 = vert_loc * ob_mat + obj_loc
                    p2 = cur_loc
                    return (p1, p2, COLOR_GLOBAL)

            elif len(verts_selected) == 2:
                # Two vertices selected.
                # We measure the distance between the
                # two selected vertices.
                obj_loc = obj.location.copy()
                vert1_loc = verts_selected[0].co.copy()
                vert2_loc = verts_selected[1].co.copy()

                # Convert to local or global space.
                if measureLocal(sce):
                    p1 = obj_loc + vert1_loc
                    p2 = obj_loc + vert2_loc
                    return (p1, p2, COLOR_LOCAL)

                else:
                    p1 = obj_loc + vert1_loc * ob_mat
                    p2 = obj_loc + vert2_loc * ob_mat
                    return (p1, p2, COLOR_GLOBAL)

            else:
                return None

    elif (context.mode == 'OBJECT'):
        # We are working on object mode.

        if len(context.selected_objects) > 2:
            return None
        elif len(context.selected_objects) == 2:
            # 2 objects selected.
            # We measure the distance between the 2 selected objects.
            obj1, obj2 = context.selected_objects
            obj1_loc = obj1.location.copy()
            obj2_loc = obj2.location.copy()
            return (obj1_loc, obj2_loc, COLOR_GLOBAL)

        elif (obj):
            # One object selected.
            # We measure the distance from the object to the 3D cursor.
            cur_loc = sce.cursor_location
            obj_loc = obj.location.copy()
            return (obj_loc, cur_loc, COLOR_GLOBAL)

        elif not context.selected_objects:
            # Nothing selected.
            # We measure the distance from the origin to the 3D cursor.
            p1 = Vector((0.0, 0.0, 0.0))
            p2 = sce.cursor_location
            return (p1, p2, COLOR_GLOBAL)

        else:
            return None


# Return the area of a face (in global space).
# @note Copies the functionality of the following functions,
# but also respects the scaling (via the "obj.matrix" parameter):
# @sa: rna_mesh.c:rna_MeshFace_area_get
# @sa: math_geom.c:area_quad_v3
# @sa: math_geom.c:area_tri_v3
def faceAreaGlobal(face, obj):
    area = 0.0

    mat = obj.matrix

    if len(face.verts) == 4:
        # Quad

        # Get vertex indices
        v1, v2, v3, v4 = face.verts

        # Get vertex data
        v1 = obj.data.verts[v1]
        v2 = obj.data.verts[v2]
        v3 = obj.data.verts[v3]
        v4 = obj.data.verts[v4]

        # Apply transform matrix to vertex coordinates.
        v1 = v1.co * mat
        v2 = v2.co * mat
        v3 = v3.co * mat
        v4 = v4.co * mat

        vec1 = v2 - v1
        vec2 = v4 - v1

        n = vec1.cross(vec2)

        area = n.length / 2.0

        vec1 = v4 - v3
        vec2 = v2 - v3

        n = vec1.cross(vec2)

        area += n.length / 2.0

    elif len(face.verts) == 3:
        # Triangle

        # Get vertex indices
        v1, v2, v3 = face.verts

        # Get vertex data
        v1 = obj.data.verts[v1]
        v2 = obj.data.verts[v2]
        v3 = obj.data.verts[v3]

        # Apply transform matrix to vertex coordinates.
        v1 = v1.co * mat
        v2 = v2.co * mat
        v3 = v3.co * mat

        vec1 = v3 - v2
        vec2 = v1 - v2

        n = vec1.cross(vec2)

        area = n.length / 2.0

    return area


# Calculate the surface area of a mesh object.
# *) Set selectedOnly=1 if you only want to count selected faces.
# *) Set globalSpace=1 if you want to calculate
#    the global surface area (object mode).
# Note: Be sure you have updated the mesh data before
#       running this with selectedOnly=1!
# @todo Support other object types (surfaces, etc...)?
def objectSurfaceArea(obj, selectedOnly, globalSpace):
    if (obj and obj.type == 'MESH' and obj.data):
        areaTotal = 0

        mesh = obj.data

        # Count the area of all the faces.
        for face in mesh.faces:
            if not selectedOnly or face.selected:
                if globalSpace:
                    areaTotal += faceAreaGlobal(face, obj)
                else:
                    areaTotal += face.area

        return areaTotal

    # We can not calculate an area for this object.
    return -1


# User friendly access to the "space" setting.
def measureGlobal(sce):
    return (sce.measure_panel_transform == "measure_global")


# User friendly access to the "space" setting.
def measureLocal(sce):
    return (sce.measure_panel_transform == "measure_local")


# Converts 3D coordinates in a 3DRegion
# into 2D screen coordinates for that region.
def region3d_get_2d_coordinates(context, loc_3d):
    # Get screen information
    mid_x = context.region.width / 2.0
    mid_y = context.region.height / 2.0
    width = context.region.width
    height = context.region.height

    # Get matrices
    view_mat = context.space_data.region_3d.perspective_matrix
    total_mat = view_mat

    # order is important
    vec = total_mat * Vector((loc_3d[0], loc_3d[1], loc_3d[2], 1.0))

    # dehomogenise
    vec = Vector((
        vec[0] / vec[3],
        vec[1] / vec[3],
        vec[2] / vec[3]))

    x = int(mid_x + vec[0] * width / 2.0)
    y = int(mid_y + vec[1] * height / 2.0)

    return Vector((x, y, 0))


def draw_measurements_callback(self, context):
    sce = context.scene

    draw = 0
    if hasattr(sce, "measure_panel_draw"):
        draw = sce.measure_panel_draw

    # 2D drawing code example
    #bgl.glBegin(bgl.GL_LINE_STRIP)
    #bgl.glVertex2i(0, 0)
    #bgl.glVertex2i(80, 100)
    #bgl.glEnd()

    # Get measured 3D points and colors.
    line = getMeasurePoints(context)
    if (line and draw):
        p1, p2, color = line

        # Get and convert the Perspective Matrix of the current view/region.
        view3d = bpy.context.space_data
        region = view3d.region_3d
        perspMatrix = region.perspective_matrix
        tempMat = [perspMatrix[i][j] for i in range(4) for j in range(4)]
        perspBuff = bgl.Buffer(bgl.GL_FLOAT, 16, tempMat)

        # ---
        # Store previous OpenGL settings.
        # Store MatrixMode
        MatrixMode_prev = bgl.Buffer(bgl.GL_INT, [1])
        bgl.glGetIntegerv(bgl.GL_MATRIX_MODE, MatrixMode_prev)
        MatrixMode_prev = MatrixMode_prev[0]

        # Store projection matrix
        ProjMatrix_prev = bgl.Buffer(bgl.GL_DOUBLE, [16])
        bgl.glGetFloatv(bgl.GL_PROJECTION_MATRIX, ProjMatrix_prev)

        # Store Line width
        lineWidth_prev = bgl.Buffer(bgl.GL_FLOAT, [1])
        bgl.glGetFloatv(bgl.GL_LINE_WIDTH, lineWidth_prev)
        lineWidth_prev = lineWidth_prev[0]

        # Store GL_BLEND
        blend_prev = bgl.Buffer(bgl.GL_BYTE, [1])
        bgl.glGetFloatv(bgl.GL_BLEND, blend_prev)
        blend_prev = blend_prev[0]

        # Store glColor4f
        color_prev = bgl.Buffer(bgl.GL_FLOAT, [4])
        bgl.glGetFloatv(bgl.GL_COLOR, color_prev)

        # ---
        # Prepare for 3D drawing
        bgl.glLoadIdentity()
        bgl.glMatrixMode(bgl.GL_PROJECTION)
        bgl.glLoadMatrixf(perspBuff)

        bgl.glColor4f(color[0], color[1], color[2], color[3])
        bgl.glEnable(bgl.GL_BLEND)

        # ---
        # Draw 3D stuff.
        width = 2
        bgl.glLineWidth(width)
        bgl.glBegin(bgl.GL_LINE_STRIP)
        bgl.glVertex3f(p1[0], p1[1], p1[2])
        bgl.glVertex3f(p2[0], p2[1], p2[2])
        bgl.glEnd()

        # ---
        # Restore previous OpenGL settings
        bgl.glLoadIdentity()
        bgl.glMatrixMode(MatrixMode_prev)
        bgl.glLoadMatrixf(ProjMatrix_prev)
        bgl.glLineWidth(lineWidth_prev)
        if not blend_prev:
            bgl.glDisable(bgl.GL_BLEND)
        bgl.glColor4f(color_prev[0],
            color_prev[1],
            color_prev[2],
            color_prev[3])

        # ---
        # Draw (2D) text
        # We do this after drawing the lines so
        # we can draw it OVER the line.
        coord_2d = region3d_get_2d_coordinates(context, p2 + (p1 - p2) * 0.5)
        offset = 10  # Offset the text a bit to the right.
        blf.position(coord_2d[0] + offset, coord_2d[1], 0)

        dist = (p1 - p2).length
        text = "Distance: " + str(round(dist, PRECISION)) + " BU"
        # @todo Get user pref for text color in 3D View
        bgl.glColor4f(1.0, 1.0, 1.0, 1.0)
        blf.size(12, 72)  # Prevent font size to randomly change.
        blf.draw(text)


class VIEW3D_OT_display_measurements(bpy.types.Operator):
    '''Display the measurements made in the 'Measure' panel'''
    bl_idname = "view3d.display_measurements"
    bl_label = "Display the measurements made in the" \
        " 'Measure' panel in the 3D View."
    bl_options = {'REGISTER'}

    def modal(self, context, event):
        context.area.tag_redraw()

        return {'FINISHED'}

    def execute(self, context):
        if context.area.type == 'VIEW_3D':
            if not self.bl_label in context.manager.operators.keys():
                # Add the region OpenGL drawing callback
                for WINregion in context.area.regions:
                    if WINregion.type == 'WINDOW':
                        break

                context.manager.add_modal_handler(self)
                self._handle = WINregion.callback_add(
                    draw_measurements_callback,
                    (self, context),
                    'POST_PIXEL')

                print("Measure panel display callback added")

            return {'RUNNING_MODAL'}

        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


class VIEW3D_OT_reenter_editmode(bpy.types.Operator):
    bl_label = "Re-enter EditMode"
    bl_idname = "view3d.reenter_editmode"
    bl_description = "Update mesh data of an active mesh object." \
        " This is done by exiting and re-entering mesh edit mode."
    bl_options = {'REGISTER'}

    def invoke(self, context, event):

        # Get the active object.
        obj = context.active_object

        if (obj and obj.type == 'MESH' and context.mode == 'EDIT_MESH'):
            # Exit and re-enter mesh EditMode.
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.mode_set(mode='EDIT')
            return {'FINISHED'}

        return {'CANCELLED'}


class VIEW3D_PT_measure(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_label = "Measure"
    bl_default_closed = True

    def poll(self, context):
        # Only display this panel in the object and edit mode 3D view.
        if (context.area.type == 'VIEW_3D' and
            (context.mode == 'EDIT_MESH'
            or context.mode == 'OBJECT')):
            return 1

        return 0

    def draw_header(self, context):
        layout = self.layout
        sce = context.scene

        # Execute operator (this adds the callback)
        # if it wasn't done yet.
        bpy.ops.view3d.display_measurements()

        # Define property for the draw setting.
        sce.BoolProperty(
            attr="measure_panel_draw",
            description="Draw distances in 3D View",
            default=1)

        # Define property for the calc-area setting.
        # @todo prevent double calculations for each refresh automatically?
        sce.BoolProperty(
            attr="measure_panel_calc_area",
            description="Calculate mesh surface area (heavy CPU" \
                " usage on bigger meshes)",
            default=0)

        layout.prop(sce, "measure_panel_draw")

    def draw(self, context):
        layout = self.layout
        sce = context.scene

        # Force a redraw.
        # This prevents the lines still be drawn after
        # disabling the "measure_panel_draw" checkbox.
        # @todo Better solution?
        context.area.tag_redraw()

        # Get a single selected object (or nothing).
        obj = getSingleObject(context)

        # Define a temporary attribute for the distance value
        sce.FloatProperty(
            name="Distance",
            attr="measure_panel_dist",
            precision=PRECISION,
            unit="LENGTH")
        sce.FloatProperty(
            attr="measure_panel_area1",
            precision=PRECISION,
            unit="AREA")
        sce.FloatProperty(
            attr="measure_panel_area2",
            precision=PRECISION,
            unit="AREA")

        TRANSFORM = [
            ("measure_global", "Global",
                "Calculate values in global space."),
            ("measure_local", "Local",
                "Calculate values inside the local object space.")]

        # Define dropdown for the global/local setting
        bpy.types.Scene.EnumProperty(
            attr="measure_panel_transform",
            name="Space",
            description="Choose in which space you want to measure.",
            items=TRANSFORM,
            default='measure_global')

        if (context.mode == 'EDIT_MESH'):
            obj = context.active_object

            if (obj and obj.type == 'MESH' and obj.data):
                # "Note: a Mesh will return the selection state of the mesh
                # when EditMode was last exited. A Python script operating
                # in EditMode must exit EditMode before getting the current
                # selection state of the mesh."
                # http://www.blender.org/documentation/249PythonDoc/
                # /Mesh.MVert-class.html#sel
                # We can only provide this by existing & re-entering EditMode.
                # @todo: Better way to do this?

                # Get mesh data from Object.
                mesh = obj.data

                # Get transformation matrix from object.
                ob_mat = obj.matrix
                # Also make an inversed copy! of the matrix.
                ob_mat_inv = ob_mat.copy()
                Matrix.invert(ob_mat_inv)

                # Get the selected vertices.
                # @todo: Better (more efficient) way to do this?
                verts_selected = [v for v in mesh.verts if v.selected == 1]

                if len(verts_selected) == 0:
                    # Nothing selected.
                    # We measure the distance from...
                    # local  ... the object center to the 3D cursor.
                    # global ... the origin to the 3D cursor.

                    # Get the 2 measure points
                    line = getMeasurePoints(context)
                    if line != 0:
                        dist_vec = line[0] - line[1]

                    sce.measure_panel_dist = dist_vec.length

                    row = layout.row()
                    row.prop(sce, "measure_panel_dist")

                    row = layout.row()
                    row.label(text="", icon='CURSOR')
                    row.label(text="", icon='ARROW_LEFTRIGHT')
                    if measureLocal(sce):
                        row.label(text="Obj. Center")
                    else:
                        row.label(text="Origin [0,0,0]")

                    row = layout.row()
                    row.operator("view3d.reenter_editmode",
                        text="Update selection & distance")
#                       @todo
#                        description="The surface area value can" \
#                            " not be updated in mesh edit mode" \
#                            " automatically. Press this button" \
#                            " to do this manually, after you changed" \
#                            " the selection.")

                    row = layout.row()
                    row.prop(sce,
                        "measure_panel_transform",
                        expand=True)

                elif len(verts_selected) == 1:
                    # One vertex selected.
                    # We measure the distance from the
                    # selected vertex object to the 3D cursor.

                    # Get the 2 measure points
                    line = getMeasurePoints(context)
                    if line != 0:
                        dist_vec = line[0] - line[1]

                    sce.measure_panel_dist = dist_vec.length

                    row = layout.row()
                    row.prop(sce, "measure_panel_dist")

                    row = layout.row()
                    row.label(text="", icon='CURSOR')
                    row.label(text="", icon='ARROW_LEFTRIGHT')
                    row.label(text="", icon='VERTEXSEL')

                    row = layout.row()
                    row.operator("view3d.reenter_editmode",
                        text="Update selection & distance")

                    row = layout.row()
                    row.prop(sce,
                        "measure_panel_transform",
                        expand=True)

                elif len(verts_selected) == 2:
                    # Two vertices selected.
                    # We measure the distance between the
                    # two selected vertices.

                    # Get the 2 measure points
                    line = getMeasurePoints(context)
                    if line != 0:
                        dist_vec = line[0] - line[1]

                    sce.measure_panel_dist = dist_vec.length

                    row = layout.row()
                    row.prop(sce, "measure_panel_dist")

                    row = layout.row()
                    row.label(text="", icon='VERTEXSEL')
                    row.label(text="", icon='ARROW_LEFTRIGHT')
                    row.label(text="", icon='VERTEXSEL')

                    row = layout.row()
                    row.operator("view3d.reenter_editmode",
                        text="Update selection & distance")

                    row = layout.row()
                    row.prop(sce,
                        "measure_panel_transform",
                        expand=True)

                else:
                    row = layout.row()
                    row.prop(sce, "measure_panel_calc_area",
                        text="Surface area (selected faces):")

                    if (sce.measure_panel_calc_area):
                        # Get selected faces
                        # @todo: Better (more efficient) way to do this?
                        faces_selected = [f for f in mesh.faces
                            if f.selected == 1]

                        if len(faces_selected) > 0:
                            area = objectSurfaceArea(obj, True,
                                measureGlobal(sce))
                            if (area >= 0):
                                row = layout.row()
                                row.label(
                                    text=str(len(faces_selected)),
                                    icon='FACESEL')
                                sce.measure_panel_area1 = area
                                row.prop(sce, "measure_panel_area1")

                                row = layout.row()
                                row.operator("view3d.reenter_editmode",
                                    text="Update selection & area")

                                row = layout.row()
                                row.prop(sce,
                                    "measure_panel_transform",
                                    expand=True)

                        else:
                            row = layout.row()
                            row.label(text="Selection not supported.",
                                icon='INFO')

                            row = layout.row()
                            row.operator("view3d.reenter_editmode",
                                text="Update selection")

                    else:
                        row = layout.row()
                        row.operator("view3d.reenter_editmode",
                            text="Update selection")

        elif (context.mode == 'OBJECT'):
            # We are working on object mode.

            if len(context.selected_objects) > 2:
                # We have more that 2 objects selected...

                row = layout.row()
                row.prop(sce, "measure_panel_calc_area",
                        text="Surface area (selected faces):")

                if (sce.measure_panel_calc_area):

                    mesh_objects = [o for o in context.selected_objects
                        if (o.type == 'MESH')]

                    if (len(mesh_objects) > 0):
                        # ... and at least one of them is a mesh.

                        # Calculate and display surface area of the objects.
                        # @todo: Convert to scene units! We do not have a
                        # FloatProperty field here for automatic conversion.

                        row = layout.row()
                        for o in mesh_objects:
                            area = objectSurfaceArea(o, False,
                                measureGlobal(sce))
                            if (area >= 0):
                                row = layout.row()
                                row.label(text=o.name, icon='OBJECT_DATA')
                                row.label(text=str(round(area, PRECISION))
                                    + " BU^2")

                        row = layout.row()
                        row.prop(sce,
                            "measure_panel_transform",
                            expand=True)

            elif len(context.selected_objects) == 2:
                # 2 objects selected.
                # We measure the distance between the 2 selected objects.

                obj1, obj2 = context.selected_objects

                # Get the 2 measure points
                line = getMeasurePoints(context)
                if line != 0:
                    dist_vec = line[0] - line[1]

                sce.measure_panel_dist = dist_vec.length

                row = layout.row()
                row.prop(sce, "measure_panel_dist")

                row = layout.row()
                row.label(text="", icon='OBJECT_DATA')
                row.prop(obj1, "name", text="")

                row.label(text="", icon='ARROW_LEFTRIGHT')

                row.label(text="", icon='OBJECT_DATA')
                row.prop(obj2, "name", text="")

                row = layout.row()
                row.prop(sce, "measure_panel_calc_area",
                    text="Surface area:")

                if (sce.measure_panel_calc_area):
                    # Calculate and display surface area of the objects.
                    area1 = objectSurfaceArea(obj1, False, measureGlobal(sce))
                    area2 = objectSurfaceArea(obj2, False, measureGlobal(sce))
                    if (area1 >= 0 or area2 >= 0):
                        if (area1 >= 0):
                            row = layout.row()
                            row.label(text=obj1.name, icon='OBJECT_DATA')
                            sce.measure_panel_area1 = area1
                            row.prop(sce, "measure_panel_area1")

                        if (area2 >= 0):
                            row = layout.row()
                            row.label(text=obj2.name, icon='OBJECT_DATA')
                            sce.measure_panel_area2 = area2
                            row.prop(sce, "measure_panel_area2")

                        row = layout.row()
                        row.prop(sce,
                            "measure_panel_transform",
                            expand=True)

            elif (obj):
                # One object selected.
                # We measure the distance from the object to the 3D cursor.

                # Get the 2 measure points
                line = getMeasurePoints(context)
                if line != 0:
                    dist_vec = line[0] - line[1]

                sce.measure_panel_dist = dist_vec.length

                row = layout.row()
                #row.label(text=str(dist_vec.length))
                row.prop(sce, "measure_panel_dist")

                row = layout.row()
                row.label(text="", icon='CURSOR')

                row.label(text="", icon='ARROW_LEFTRIGHT')

                row.label(text="", icon='OBJECT_DATA')
                row.prop(obj, "name", text="")

                row = layout.row()
                row.prop(sce, "measure_panel_calc_area",
                    text="Surface area:")

                if (sce.measure_panel_calc_area):
                    # Calculate and display surface area of the object.
                    area = objectSurfaceArea(obj, False, measureGlobal(sce))
                    if (area >= 0):
                        row = layout.row()
                        row.label(text=obj.name, icon='OBJECT_DATA')
                        sce.measure_panel_area1 = area
                        row.prop(sce, "measure_panel_area1")

                        row = layout.row()
                        row.prop(sce,
                            "measure_panel_transform",
                            expand=True)

            elif not context.selected_objects:
                # Nothing selected.
                # We measure the distance from the origin to the 3D cursor.

                # Get the 2 measure points
                line = getMeasurePoints(context)
                if line != 0:
                    dist_vec = line[0] - line[1]

                sce.measure_panel_dist = dist_vec.length

                row = layout.row()
                row.prop(sce, "measure_panel_dist")

                row = layout.row()
                row.label(text="", icon='CURSOR')
                row.label(text="", icon='ARROW_LEFTRIGHT')
                row.label(text="Origin [0,0,0]")

            else:
                row = layout.row()
                row.label(text="Selection not supported.",
                    icon='INFO')


def register():
    bpy.types.register(VIEW3D_PT_measure)
    bpy.types.register(VIEW3D_OT_reenter_editmode)
    bpy.types.register(VIEW3D_OT_display_measurements)


def unregister():
    bpy.types.unregister(VIEW3D_PT_measure)
    bpy.types.unregister(VIEW3D_OT_reenter_editmode)
    bpy.types.unregister(VIEW3D_OT_display_measurements)

if __name__ == "__main__":
    register()
