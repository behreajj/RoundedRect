import bpy
import math
import bmesh
from bpy.props import (
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntVectorProperty)

bl_info = {
    "name": "Create Rounded Rect Mesh",
    "author": "Jeremy Behreandt",
    "version": (0, 1),
    "blender": (3, 0, 1),
    "category": "Add Mesh",
    "description": "Creates a rounded rectangle mesh.",
    "tracker_url": "https://github.com/behreajj/RoundedRect"
}


class RndRectMeshMaker(bpy.types.Operator):
    """Creates a rounded rectangle mesh"""

    bl_idname = "mesh.primitive_rect_mesh_add"
    bl_label = "Rectangle"
    bl_options = {"REGISTER", "UNDO"}

    tl: FloatVectorProperty(
        name="Top Left",
        description="Top-left corner",
        default=(-1.7777778, 1.0),
        soft_min=-1.7777778,
        soft_max=1.7777778,
        step=1,
        precision=3,
        size=2,
        subtype="COORDINATES")

    br: FloatVectorProperty(
        name="Bottom Right",
        description="Bottom-right corner",
        default=(1.7777778, -1.0),
        soft_min=-1.7777778,
        soft_max=1.7777778,
        step=1,
        precision=3,
        size=2,
        subtype="COORDINATES")

    rounding: FloatVectorProperty(
        name="Corner",
        description="Corner rounding factor",
        default=(0.25, 0.25, 0.25, 0.25),
        min=0.001,
        max=0.999,
        step=1,
        precision=3,
        size=4)

    sectors: IntVectorProperty(
        name="Resolution",
        description="Corner resolution",
        default=(8, 8, 8, 8),
        min=0,
        soft_max=32,
        size=4)

    poly_type: EnumProperty(
        items=[
            ("NGON", "Ngon", "Ngon", 1),
            ("QUAD", "Quadrilateral", "Quadrilateral", 2),
            ("TRI", "Triangle", "Triangle", 3)],
        name="Polygon Type",
        default="QUAD",
        description="Polygon type to use")

    extrude_thick: FloatProperty(
        name="Extrude",
        description="Extrusion thickness",
        min=0.0,
        soft_max=1.0,
        step=1,
        precision=3,
        default=0.0)

    extrude_off: FloatProperty(
        name="Offset",
        description="Extrusion offset",
        min=-1.0,
        max=1.0,
        step=1,
        precision=3,
        default=0.0)

    def execute(self, context):
        tl_res = self.sectors[0]
        tr_res = self.sectors[1]
        br_res = self.sectors[2]
        bl_res = self.sectors[3]

        use_smooth = tl_res > 0 \
            or tr_res > 0 \
            or br_res > 0 \
            or bl_res > 0

        data = RndRectMeshMaker.create_rect_mesh(
            lbx=self.tl[0], lby=self.br[1],
            ubx=self.br[0], uby=self.tl[1],
            tl=self.rounding[0], tr=self.rounding[1],
            br=self.rounding[2], bl=self.rounding[3],
            tl_res=tl_res, tr_res=tr_res,
            br_res=br_res, bl_res=bl_res,
            poly=self.poly_type)

        bm = RndRectMeshMaker.mesh_data_to_bmesh(
            vs=data["vs"],
            vts=data["vts"],
            vns=data["vns"],
            v_indices=data["v_indices"],
            vt_indices=data["vt_indices"],
            vn_indices=data["vn_indices"],
            use_smooth_shading=use_smooth)

        mesh_data = bpy.data.meshes.new("Rectangle")
        mesh_data.use_auto_smooth = use_smooth
        mesh_data.auto_smooth_angle = 0.523599
        
        bm.to_mesh(mesh_data)
        bm.free()
        mesh_obj = bpy.data.objects.new(mesh_data.name, mesh_data)
        mesh_obj.location = context.scene.cursor.location

        if self.extrude_thick > 0.0:
            ext_mod = mesh_obj.modifiers.new("Solidify", "SOLIDIFY")
            ext_mod.thickness = self.extrude_thick
            ext_mod.offset = self.extrude_off
            ext_mod.show_in_editmode = False

        context.scene.collection.objects.link(mesh_obj)
        return {"FINISHED"}

    @classmethod
    def poll(cls, context):
        return context.area.type == "VIEW_3D"

    @staticmethod
    def mesh_data_to_bmesh(
            vs, vts, vns,
            v_indices, vt_indices, vn_indices,
            use_smooth_shading=True):

        bm = bmesh.new()

        # Create BM vertices.
        len_vs = len(vs)
        bm_verts = [None] * len_vs
        for i in range(0, len_vs):
            bm_verts[i] = bm.verts.new(vs[i])

        # Create BM faces.
        len_v_indices = len(v_indices)
        bm_faces = [None] * len_v_indices
        uv_layer = bm.loops.layers.uv.verify()

        for i in range(0, len_v_indices):
            v_loop = v_indices[i]
            vt_loop = vt_indices[i]
            vn_loop = vn_indices[i]

            # Find list of vertices per face.
            len_v_loop = len(v_loop)
            face_verts = [None] * len_v_loop
            for j in range(0, len_v_loop):
                face_verts[j] = bm_verts[v_loop[j]]

            # Create BM face.
            bm_face = bm.faces.new(face_verts)
            bm_faces[i] = bm_face
            bm_face.smooth = use_smooth_shading
            bm_face_loops = list(bm_face.loops)

            # Assign texture coordinates and normals.
            for k in range(0, len_v_loop):
                bm_face_loop = bm_face_loops[k]
                bm_face_loop[uv_layer].uv = vts[vt_loop[k]]
                bm_face_loop.vert.normal = vns[vn_loop[k]]

        return bm

    @staticmethod
    def create_rect_mesh(
            lbx=-1.7777778, lby=-1.0,
            ubx=1.7777778, uby=1.0,
            tl=0.25, tr=0.25,
            br=0.25, bl=0.25,
            tl_res=16, tr_res=16,
            br_res=16, bl_res=16,
            poly="QUAD"):

        # Constants.
        eps = 0.000001
        half_pi = math.pi * 0.5

        # Validate corners.
        lft = min(lbx, ubx)
        rgt = max(lbx, ubx)
        btm = min(lby, uby)
        top = max(lby, uby)

        # Protect from zero dimension meshes.
        w_inval = abs(rgt - lft) < eps
        h_inval = abs(top - btm) < eps
        if w_inval and h_inval:
            cx = (lft + rgt) * 0.5
            cy = (top + btm) * 0.5
            lft = cx - 1.7777778
            rgt = cx + 1.7777778
            btm = cy - 1.0
            top = cy + 1.0
        elif w_inval:
            cx = (lft + rgt) * 0.5
            hh = (top - btm) * 0.5
            lft = cx - hh
            rgt = cx + hh
        elif h_inval:
            cy = (top + btm) * 0.5
            wh = (rgt - lft) * 0.5
            btm = cy - wh
            top = cy + wh

        # Calculate width and height for vts.
        w = rgt - lft
        h = top - btm
        w_inv = 1.0 / w
        h_inv = 1.0 / h

        # Validate corner insetting.
        # Half the short edge is the maximum size.
        se = 0.5 * min(w, h)
        vtl = se * min(max(tl, eps), 1.0 - eps)
        vtr = se * min(max(tr, eps), 1.0 - eps)
        vbr = se * min(max(br, eps), 1.0 - eps)
        vbl = se * min(max(bl, eps), 1.0 - eps)

        # Validate corner resolution.
        v_tl_res = max(tl_res, 0)
        v_tr_res = max(tr_res, 0)
        v_br_res = max(br_res, 0)
        v_bl_res = max(bl_res, 0)

        # Calculate insets.
        btm_ins_0 = btm + vbr
        top_ins_0 = top - vtr
        rgt_ins_0 = rgt - vtr
        lft_ins_0 = lft + vtl
        top_ins_1 = top - vtl
        btm_ins_1 = btm + vbl
        lft_ins_1 = lft + vbl
        rgt_ins_1 = rgt - vbr

        # Initialize data arrays.
        # For QUAD and TRI, add 4 in-corner points.
        len_vs = 8 + v_tl_res + v_bl_res + v_br_res + v_tr_res
        if poly != "NGON":
            len_vs = len_vs + 4
        vs = [(0.0, 0.0, 0.0)] * len_vs
        vts = [(0.5, 0.5)] * len_vs
        vns = [(0.0, 0.0, 1.0)]

        # Calculate index offsets.
        tl_crnr_idx_start = 0
        tl_crnr_idx_end = tl_crnr_idx_start + 1 + v_tl_res
        bl_crnr_idx_start = tl_crnr_idx_end + 1
        bl_crnr_idx_end = bl_crnr_idx_start + 1 + v_bl_res
        br_crnr_idx_start = bl_crnr_idx_end + 1
        br_crnr_idx_end = br_crnr_idx_start + 1 + v_br_res
        tr_crnr_idx_start = br_crnr_idx_end + 1
        tr_crnr_idx_end = tr_crnr_idx_start + 1 + v_tr_res

        # Coordinate corners at start and end of arc.
        vs[tl_crnr_idx_start] = (lft_ins_0, top, 0.0)
        vs[tl_crnr_idx_end] = (lft, top_ins_1, 0.0)
        vs[bl_crnr_idx_start] = (lft, btm_ins_1, 0.0)
        vs[bl_crnr_idx_end] = (lft_ins_1, btm, 0.0)
        vs[br_crnr_idx_start] = (rgt_ins_1, btm, 0.0)
        vs[br_crnr_idx_end] = (rgt, btm_ins_0, 0.0)
        vs[tr_crnr_idx_start] = (rgt, top_ins_0, 0.0)
        vs[tr_crnr_idx_end] = (rgt_ins_0, top, 0.0)

        # Texture coordinate corners at start and end of arc.
        vts[tl_crnr_idx_start] = (vtl * w_inv, 1.0)
        vts[tl_crnr_idx_end] = (0.0, (top_ins_1 - btm) * h_inv)
        vts[bl_crnr_idx_start] = (0.0, vbl * h_inv)
        vts[bl_crnr_idx_end] = (vbl * w_inv, 0.0)
        vts[br_crnr_idx_start] = ((rgt_ins_1 - lft) * w_inv, 0.0)
        vts[br_crnr_idx_end] = (1.0, vbr * h_inv)
        vts[tr_crnr_idx_start] = (1.0, (top_ins_0 - btm) * h_inv)
        vts[tr_crnr_idx_end] = ((rgt_ins_0 - lft) * w_inv, 1.0)

        # Find conversion from resolution to theta.
        tl_to_theta = half_pi / (v_tl_res + 1.0)
        bl_to_theta = half_pi / (v_bl_res + 1.0)
        br_to_theta = half_pi / (v_br_res + 1.0)
        tr_to_theta = half_pi / (v_tr_res + 1.0)

        # Top-left arc.
        tl_range = range(0, v_tl_res)
        for i in tl_range:
            # Reverse order.
            j = v_tl_res - 1 - i
            theta = (j + 1.0) * tl_to_theta
            x = lft_ins_0 - vtl * math.cos(theta)
            y = top_ins_1 + vtl * math.sin(theta)
            vs[tl_crnr_idx_start + 1 + i] = (x, y, 0.0)
            vts[tl_crnr_idx_start + 1 + i] = (
                (x - lft) * w_inv,
                (y - btm) * h_inv)

        # Bottom-left arc.
        bl_range = range(0, v_bl_res)
        for i in bl_range:
            theta = (i + 1.0) * bl_to_theta
            x = lft_ins_1 - vbl * math.cos(theta)
            y = btm_ins_1 - vbl * math.sin(theta)
            vs[bl_crnr_idx_start + 1 + i] = (x, y, 0.0)
            vts[bl_crnr_idx_start + 1 + i] = (
                (x - lft) * w_inv,
                (y - btm) * h_inv)

        # Bottom-right arc.
        br_range = range(0, v_br_res)
        for i in br_range:
            # Reverse order.
            j = v_br_res - 1 - i
            theta = (j + 1.0) * br_to_theta
            x = rgt_ins_1 + vbr * math.cos(theta)
            y = btm_ins_0 - vbr * math.sin(theta)
            vs[br_crnr_idx_start + 1 + i] = (x, y, 0.0)
            vts[br_crnr_idx_start + 1 + i] = (
                (x - lft) * w_inv,
                (y - btm) * h_inv)

        # Top-right arc.
        tr_range = range(0, v_tr_res)
        for i in tr_range:
            theta = (i + 1.0) * tr_to_theta
            x = rgt_ins_0 + vtr * math.cos(theta)
            y = top_ins_0 + vtr * math.sin(theta)
            vs[tr_crnr_idx_start + 1 + i] = (x, y, 0.0)
            vts[tr_crnr_idx_start + 1 + i] = (
                (x - lft) * w_inv,
                (y - btm) * h_inv)

        if poly == "NGON":
            v_arr = [0] * len_vs
            vn_arr = [0] * len_vs

            i_range = range(0, len_vs)
            for i in i_range:
                v_arr[i] = i

            v_indices = [tuple(v_arr)]
            vn_indices = [tuple(vn_arr)]
        else:
            # Insert inner vertices for quad and tri.
            tl_tn_crnr_idx = len_vs - 4
            bl_in_crnr_idx = len_vs - 3
            br_in_crnr_idx = len_vs - 2
            tr_in_crnr_idx = len_vs - 1

            # Inner coordinate corners.
            vs[tl_tn_crnr_idx] = (lft_ins_0, top_ins_1, 0.0)
            vs[bl_in_crnr_idx] = (lft_ins_1, btm_ins_1, 0.0)
            vs[br_in_crnr_idx] = (rgt_ins_1, btm_ins_0, 0.0)
            vs[tr_in_crnr_idx] = (rgt_ins_0, top_ins_0, 0.0)

            # Inner texture coordinate corners.
            vts[tl_tn_crnr_idx] = (vtl * w_inv, (top_ins_1 - btm) * h_inv)
            vts[bl_in_crnr_idx] = (vbl * w_inv, vbl * h_inv)
            vts[br_in_crnr_idx] = ((rgt_ins_1 - lft) * w_inv, vbr * h_inv)
            vts[tr_in_crnr_idx] = ((rgt_ins_0 - lft) *
                                   w_inv, (top_ins_0 - btm) * h_inv)

            # Sum the number of vertices per arc.
            # For n vertices, there are n + 1 faces.
            v_res_total = v_tl_res + v_tr_res + v_br_res + v_bl_res
            f_res_total = v_res_total + 4

            # Assign to three tuples. For poly type quads, some
            # will be replaced by four tuples.
            len_indices = 0
            non_corner_faces = 0
            v_indices = []
            vn_indices = []

            # Create non-corner faces: center, left, bottom, right, top.
            if poly == "QUAD":
                non_corner_faces = 5
                len_indices = non_corner_faces + f_res_total
                v_indices = [(0, 0, 0)] * len_indices
                vn_indices = [(0, 0, 0)] * len_indices

                v_indices[0] = (tl_tn_crnr_idx, bl_in_crnr_idx,
                                br_in_crnr_idx, tr_in_crnr_idx)
                v_indices[1] = (tl_crnr_idx_end, bl_crnr_idx_start,
                                bl_in_crnr_idx, tl_tn_crnr_idx)
                v_indices[2] = (bl_in_crnr_idx, bl_crnr_idx_end,
                                br_crnr_idx_start, br_in_crnr_idx)
                v_indices[3] = (tr_in_crnr_idx, br_in_crnr_idx,
                                br_crnr_idx_end, tr_crnr_idx_start)
                v_indices[4] = (tl_crnr_idx_start, tl_tn_crnr_idx,
                                tr_in_crnr_idx, tr_crnr_idx_end)

                vn_indices[0] = (0, 0, 0, 0)
                vn_indices[1] = (0, 0, 0, 0)
                vn_indices[2] = (0, 0, 0, 0)
                vn_indices[3] = (0, 0, 0, 0)
                vn_indices[4] = (0, 0, 0, 0)
            else:
                non_corner_faces = 10
                len_indices = non_corner_faces + f_res_total
                v_indices = [(0, 0, 0)] * len_indices
                vn_indices = [(0, 0, 0)] * len_indices

                v_indices[0] = (tl_tn_crnr_idx, bl_in_crnr_idx, tr_in_crnr_idx)
                v_indices[1] = (bl_in_crnr_idx, br_in_crnr_idx, tr_in_crnr_idx)
                v_indices[2] = (tl_crnr_idx_end,
                                bl_crnr_idx_start, tl_tn_crnr_idx)
                v_indices[3] = (bl_crnr_idx_start,
                                bl_in_crnr_idx, tl_tn_crnr_idx)
                v_indices[4] = (
                    bl_in_crnr_idx, bl_crnr_idx_end, br_in_crnr_idx)
                v_indices[5] = (bl_crnr_idx_end,
                                br_crnr_idx_start, br_in_crnr_idx)
                v_indices[6] = (tr_in_crnr_idx, br_in_crnr_idx,
                                tr_crnr_idx_start)
                v_indices[7] = (br_in_crnr_idx, br_crnr_idx_end,
                                tr_crnr_idx_start)
                v_indices[8] = (tl_crnr_idx_start,
                                tl_tn_crnr_idx, tr_crnr_idx_end)
                v_indices[9] = (tl_tn_crnr_idx, tr_in_crnr_idx,
                                tr_crnr_idx_end)

            # Create corner faces:
            # Top-left, Bottom-left, Bottom-right, Top-right.

            # Face count.
            f_tl_res = v_tl_res + 1
            f_bl_res = v_bl_res + 1
            f_br_res = v_br_res + 1
            f_tr_res = v_tr_res + 1

            # Index offsets.
            fs_tl_idx_start = non_corner_faces
            fs_bl_idx_start = fs_tl_idx_start + f_tl_res
            fs_br_idx_start = fs_bl_idx_start + f_bl_res
            fs_tr_idx_start = fs_br_idx_start + f_br_res

            # Top-left corner.
            ftl_range = range(0, f_tl_res)
            for i in ftl_range:
                j = fs_tl_idx_start + i
                b = tl_crnr_idx_start + i
                c = b + 1
                v_indices[j] = (tl_tn_crnr_idx, b, c)

            # Bottom-left corner.
            fbl_range = range(0, f_bl_res)
            for i in fbl_range:
                j = fs_bl_idx_start + i
                b = bl_crnr_idx_start + i
                c = b + 1
                v_indices[j] = (bl_in_crnr_idx, b, c)

            # Bottom-right corner.
            fbr_range = range(0, f_br_res)
            for i in fbr_range:
                j = fs_br_idx_start + i
                b = br_crnr_idx_start + i
                c = b + 1
                v_indices[j] = (br_in_crnr_idx, b, c)

            # Top-right corner.
            ftr_range = range(0, f_tr_res)
            for i in ftr_range:
                j = fs_tr_idx_start + i
                b = tr_crnr_idx_start + i
                c = b + 1
                v_indices[j] = (tr_in_crnr_idx, b, c)

        # Return a dictionary containing data.
        return {"vs": vs,
                "vts": vts,
                "vns": vns,
                "v_indices": v_indices,
                "vt_indices": v_indices.copy(),
                "vn_indices": vn_indices}


def menu_func(self, context):
    self.layout.operator(RndRectMeshMaker.bl_idname, icon="META_PLANE")


def register():
    bpy.utils.register_class(RndRectMeshMaker)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)


def unregister():
    bpy.utils.unregister_class(RndRectMeshMaker)
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)
