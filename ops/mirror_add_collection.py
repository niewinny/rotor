import bpy
from bpy.props import CollectionProperty
from mathutils import Matrix, Vector
from ..utils import addon
from .mirror_utils import bisect_object
from .mirror_props import ROTOR_PG_MirrorCollectionItem


class ROTOR_OT_AddMirrorCollection(bpy.types.Operator):
    """Mirror collection"""
    bl_idname = "rotor.add_mirror_collection"
    bl_label = "Rotor Mirror Axis"
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="Axis to toggle",
        items=[('X', 'X', ''), ('Y', 'Y', ''), ('Z', 'Z', '')],
    )
    sign: bpy.props.EnumProperty(
        name="Sign",
        description="Sign (+ or -)",
        items=[('POS', '+', ''), ('NEG', '-', '')],
    )
    
    affected_collections: CollectionProperty(type=ROTOR_PG_MirrorCollectionItem)

    def invoke(self, context, event):
        """Populate the list when operator is invoked"""
        # Clear and populate the list with current selection
        self.affected_collections.clear()
        selected_objs = context.selected_objects
        collections = set()
        for obj in selected_objs:
            for col in getattr(obj, 'users_collection', []):
                # Ignore master collection and hidden/internal ones
                if not col.library and col.name != 'Scene Collection':
                    collections.add(col)
        
        for col in collections:
            item = self.affected_collections.add()
            item.name = col.name
            item.enabled = True
        
        # Continue with normal execution
        return self.execute(context)

    def draw(self, context):
        """Draw checkboxes in the undo panel"""
        layout = self.layout
        
        if hasattr(self, 'affected_collections') and self.affected_collections:
            layout.label(text=f"Affected Collections: {len(self.affected_collections)}")
            # For collections, we'll keep the simple list approach since there's no UIList for collections
            for item in self.affected_collections:
                row = layout.row()
                row.prop(item, "enabled", text=item.name)

    def execute(self, context):
        axis_map = {'X': 0, 'Y': 1, 'Z': 2}
        axis_idx = axis_map[self.axis]
        is_neg = self.sign == 'NEG'

        # Get mirror tool preferences
        pref = addon.pref().tools.mirror
        pivot = pref.pivot
        orientation = pref.orientation
        
        # Get enabled collections
        enabled_collections = []
        if hasattr(self, 'affected_collections') and self.affected_collections:
            for item in self.affected_collections:
                if item.enabled and item.name in bpy.data.collections:
                    col = bpy.data.collections[item.name]
                    enabled_collections.append(col)
        else:
            # First run - get all collections from selected objects
            selected_objs = context.selected_objects
            collections = set()
            for obj in selected_objs:
                for col in getattr(obj, 'users_collection', []):
                    # Ignore master collection and hidden/internal ones
                    if not col.library and col.name != 'Scene Collection':
                        collections.add(col)
            enabled_collections = list(collections)

        # Avoid double instancing
        created = set()
        for col in enabled_collections:
            if col in created:
                continue
            created.add(col)

            # Perform bisect operation if preference is enabled
            if pref.bisect:
                mesh_objects = [obj for obj in col.objects if obj.type == 'MESH']
                for obj in mesh_objects:
                    bisect_object(obj, axis_idx, pivot, orientation, context, is_neg)

            # Create an empty to instance the collection
            empty = bpy.data.objects.new(f"RotorMirrorInstance_{col.name}", None)
            empty.instance_type = 'COLLECTION'
            empty.instance_collection = col
            empty.empty_display_type = 'PLAIN_AXES'

            # Always use -1 scale for mirroring on the selected axis
            scale_vec = [1.0, 1.0, 1.0]
            scale_vec[axis_idx] = -1.0
            mirror_mat = Matrix.Scale(scale_vec[0], 4, Vector((1,0,0))) @ \
                         Matrix.Scale(scale_vec[1], 4, Vector((0,1,0))) @ \
                         Matrix.Scale(scale_vec[2], 4, Vector((0,0,1)))

            if pivot == 'WORLD':
                pivot_point = Vector((0,0,0))
            elif pivot == 'ACTIVE' and context.active_object:
                pivot_point = context.active_object.location.copy()
            elif pivot == 'INDIVIDUAL':
                objs_in_col = [o for o in col.objects if o.type == 'MESH']
                if objs_in_col:
                    locs = [o.location for o in objs_in_col]
                    pivot_point = sum(locs, Vector((0,0,0))) / len(locs)
                else:
                    pivot_point = Vector((0,0,0))
            elif pivot == 'CURSOR':
                pivot_point = context.scene.cursor.location.copy()
            else:
                pivot_point = Vector((0,0,0))

            # Compose the correct transformation: T @ R @ S @ R_inv @ T_inv
            rot_mat = None
            if orientation == 'LOCAL':
                if pivot == 'ACTIVE' and context.active_object:
                    rot_mat = context.active_object.rotation_euler.to_matrix().to_4x4()
                elif pivot == 'INDIVIDUAL':
                    objs_in_col = [o for o in col.objects if o.type == 'MESH']
                    if objs_in_col:
                        mats = [o.rotation_euler.to_matrix().to_4x4() for o in objs_in_col]
                        avg_mat = sum(mats, Matrix()) * (1.0 / len(mats))
                        rot_mat = avg_mat
                elif pivot in ('WORLD', 'CURSOR'):
                    # For LOCAL orientation with WORLD or CURSOR pivot, use collection objects' average rotation
                    objs_in_col = [o for o in col.objects if o.type == 'MESH']
                    if objs_in_col:
                        mats = [o.rotation_euler.to_matrix().to_4x4() for o in objs_in_col]
                        avg_mat = sum(mats, Matrix()) * (1.0 / len(mats))
                        rot_mat = avg_mat
            elif orientation == 'CURSOR':
                # CURSOR orientation uses cursor rotation regardless of pivot
                rot_mat = context.scene.cursor.rotation_euler.to_matrix().to_4x4()
            # For GLOBAL orientation, rot_mat stays None

            T = Matrix.Translation(pivot_point)
            T_inv = Matrix.Translation(-pivot_point)
            S = mirror_mat
            if rot_mat is not None:
                R = rot_mat
                R_inv = rot_mat.inverted()
                mirror_xform = T @ R @ S @ R_inv @ T_inv
            else:
                mirror_xform = T @ S @ T_inv

            empty.matrix_world = mirror_xform
            # Link empty to the Scene Collection, not to the instanced collection
            bpy.context.scene.collection.objects.link(empty)

        # Report success
        if len(created) > 0:
            self.report({'INFO'}, f"Mirrored {len(created)} collections.")
        else:
            self.report({'WARNING'}, "No collections were mirrored.")
        
        # Check if we should return to previous tool
        pref = addon.pref().tools.mirror
        last_tool = context.scene.rotor.ops.last_tool
        if pref.tool_fallback and last_tool:
            # Check if we're currently using the mirror tool
            current_tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
            if current_tool and current_tool.idname == 'rotor.mirror_tool':
                try:
                    bpy.ops.wm.tool_set_by_id(name=last_tool)
                    # Clear the last tool to prevent stale references
                    context.scene.rotor.ops.last_tool = ""
                except:
                    # If switching fails, just continue
                    pass
            
        return {'FINISHED'}


classes = (
    ROTOR_OT_AddMirrorCollection,
)