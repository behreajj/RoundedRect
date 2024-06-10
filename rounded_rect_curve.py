import bpy
from bpy.props import (
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty)

bl_info = {
    "name": "Create Rounded Rect Curve",
    "author": "Jeremy Behreandt",
    "version": (0, 2),
    "blender": (3, 0, 1),
    "category": "Add Curve",
    "description": "Creates a rounded rectangle curve.",
    "tracker_url": "https://github.com/behreajj/RoundedRect"
}


class RndRectCurveMaker(bpy.types.Operator):
    """Creates a rounded rectangle curve"""

    bl_idname = "curve.primitive_rect_curve_add"
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
        subtype="COORDINATES") # type: ignore

    br: FloatVectorProperty(
        name="Bottom Right",
        description="Bottom-right corner",
        default=(1.7777778, -1.0),
        soft_min=-1.7777778,
        soft_max=1.7777778,
        step=1,
        precision=3,
        size=2,
        subtype="COORDINATES") # type: ignore

    rounding: FloatVectorProperty(
        name="Corner",
        description="Corner rounding factor",
        default=(0.25, 0.25, 0.25, 0.25),
        min=0.0,
        max=0.999,
        step=1,
        precision=3,
        size=4) # type: ignore

    # TODO: Support Aligned Type
    straight_edge: EnumProperty(
        items=[
            ("FREE", "Free", "Free", 1),
            ("VECTOR", "Vector", "Vector", 2)],
        name="Handle Type",
        default="FREE",
        description="Handle type to use for straight edges") # type: ignore

    res_u: IntProperty(
        name="Resolution",
        description="Corner resolution",
        min=1,
        soft_max=64,
        default=12) # type: ignore

    fill_mode: EnumProperty(
        items=[
            ("NONE", "None", "None", 1),
            ("BACK", "Back", "Back", 2),
            ("FRONT", "Front", "Front", 3),
            ("BOTH", "Both", "Both", 4)],
        name="Fill Mode",
        default="BOTH",
        description="Fill mode to use") # type: ignore

    extrude_thick: FloatProperty(
        name="Extrude",
        description="Extrusion thickness",
        min=0.0,
        soft_max=1.0,
        step=1,
        precision=3,
        default=0.0) # type: ignore

    extrude_off: FloatProperty(
        name="Offset",
        description="Extrusion offset",
        min=-1.0,
        max=1.0,
        step=1,
        precision=3,
        subtype="FACTOR",
        default=0.0) # type: ignore

    def execute(self, context):
        # TODO: How to support adding to an existing curve
        # while in edit mode?

        # Constants.
        eps = 0.000001
        k = 0.5522847498307936
        o_3 = 1.0 / 3.0
        t_3 = 2.0 / 3.0

        # Unpack corners.
        lbx = self.tl[0]
        lby = self.br[1]
        ubx = self.br[0]
        uby = self.tl[1]

        # Unpack rounding factor.
        tl = self.rounding[0]
        tr = self.rounding[1]
        br = self.rounding[2]
        bl = self.rounding[3]

        straight_edge = self.straight_edge

        # Validate corners.
        lft = min(lbx, ubx)
        rgt = max(lbx, ubx)
        btm = min(lby, uby)
        top = max(lby, uby)

        # Protect from zero dimension curves.
        w = rgt - lft
        h = top - btm
        w_inval = w < eps
        h_inval = h < eps
        if w_inval and h_inval:
            cx = (lft + rgt) * 0.5
            cy = (top + btm) * 0.5
            lft = cx - 1.7777778
            rgt = cx + 1.7777778
            btm = cy - 1.0
            top = cy + 1.0
        elif w_inval:
            cx = (lft + rgt) * 0.5
            h_half = h * 0.5
            lft = cx - h_half
            rgt = cx + h_half
        elif h_inval:
            cy = (top + btm) * 0.5
            w_half = w * 0.5
            btm = cy - w_half
            top = cy + w_half

        # Validate corner insetting.
        # Half the short edge is the maximum size.
        # TODO: Can 1.0 be supported instead of 1.0 - eps,
        # i.e., consolidate knots that would form a circle?
        se = 0.5 * min(rgt - lft, top - btm)
        vtl = se * min(max(tl, 0.0), 1.0 - eps)
        vbl = se * min(max(bl, 0.0), 1.0 - eps)
        vbr = se * min(max(br, 0.0), 1.0 - eps)
        vtr = se * min(max(tr, 0.0), 1.0 - eps)

        # Corners with zero rounding are a special case.
        tl_is_round = vtl > 0.0
        bl_is_round = vbl > 0.0
        br_is_round = vbr > 0.0
        tr_is_round = vtr > 0.0

        # For calculating handle magnitude.
        vtlk = vtl * k
        vbrk = vbr * k
        vblk = vbl * k
        vtrk = vtr * k

        # Calculate insets.
        btm_ins_0 = btm + vbr
        top_ins_0 = top - vtr
        rgt_ins_0 = rgt - vtr
        lft_ins_0 = lft + vtl
        top_ins_1 = top - vtl
        btm_ins_1 = btm + vbl
        lft_ins_1 = lft + vbl
        rgt_ins_1 = rgt - vbr

        # Calculate knot count.
        kn_count = 4
        if tl_is_round:
            kn_count = kn_count + 1
        if bl_is_round:
            kn_count = kn_count + 1
        if br_is_round:
            kn_count = kn_count + 1
        if tr_is_round:
            kn_count = kn_count + 1

        # Initialize arrays.
        cos = [(0.0, 0.0, 0.0)] * kn_count
        fhs = [(0.0, 0.0, 0.0)] * kn_count
        rhs = [(0.0, 0.0, 0.0)] * kn_count
        fh_types = ["FREE"] * kn_count
        rh_types = ["FREE"] * kn_count

        # Might not be worth suporting this, because parity would be
        # difficult in the mesh version anyway...
        cursor = 0
        if tl_is_round:
            cos[cursor] = (lft_ins_0, top, 0.0)
            fhs[cursor] = (lft_ins_0 - vtlk, top, 0.0)
            rhs[cursor] = (t_3 * lft_ins_0 + o_3 * rgt_ins_0, top, 0.0)
            rh_types[cursor] = straight_edge
            cursor = cursor + 1

            cos[cursor] = (lft, top_ins_1, 0.0)
            fhs[cursor] = (lft, t_3 * top_ins_1 + o_3 * btm_ins_1, 0.0)
            rhs[cursor] = (lft, top_ins_1 + vtlk, 0.0)
            fh_types[cursor] = straight_edge
            cursor = cursor + 1
        else:
            cos[cursor] = (lft, top, 0.0)
            fhs[cursor] = (lft, t_3 * top + o_3 * btm_ins_1, 0.0)
            rhs[cursor] = (t_3 * lft + o_3 * rgt_ins_0, top, 0.0)
            fh_types[cursor] = straight_edge
            rh_types[cursor] = straight_edge
            cursor = cursor + 1

        if bl_is_round:
            cos[cursor] = (lft, btm_ins_1, 0.0)
            fhs[cursor] = (lft, btm_ins_1 - vblk, 0.0)
            rhs[cursor] = (lft, t_3 * btm_ins_1 + o_3 * top_ins_1, 0.0)
            rh_types[cursor] = straight_edge
            cursor = cursor + 1

            cos[cursor] = (lft_ins_1, btm, 0.0)
            fhs[cursor] = (t_3 * lft_ins_1 + o_3 * rgt_ins_1, btm, 0.0)
            rhs[cursor] = (lft_ins_1 - vblk, btm, 0.0)
            fh_types[cursor] = straight_edge
            cursor = cursor + 1
        else:
            cos[cursor] = (lft, btm, 0.0)
            fhs[cursor] = (t_3 * lft + o_3 * rgt_ins_1, btm, 0.0)
            rhs[cursor] = (lft, t_3 * btm + o_3 * top_ins_1, 0.0)
            fh_types[cursor] = straight_edge
            rh_types[cursor] = straight_edge
            cursor = cursor + 1

        if br_is_round:
            cos[cursor] = (rgt_ins_1, btm, 0.0)
            fhs[cursor] = (rgt_ins_1 + vbrk, btm, 0.0)
            rhs[cursor] = (t_3 * rgt_ins_1 + o_3 * lft_ins_1, btm, 0.0)
            rh_types[cursor] = straight_edge
            cursor = cursor + 1

            cos[cursor] = (rgt, btm_ins_0, 0.0)
            fhs[cursor] = (rgt, t_3 * btm_ins_0 + o_3 * top_ins_0, 0.0)
            rhs[cursor] = (rgt, btm_ins_0 - vbrk, 0.0)
            fh_types[cursor] = straight_edge
            cursor = cursor + 1
        else:
            cos[cursor] = (rgt, btm, 0.0)
            fhs[cursor] = (rgt, t_3 * btm + o_3 * top_ins_0, 0.0)
            rhs[cursor] = (t_3 * rgt + o_3 * lft_ins_1, btm, 0.0)
            fh_types[cursor] = straight_edge
            rh_types[cursor] = straight_edge
            cursor = cursor + 1

        if tr_is_round:
            cos[cursor] = (rgt, top_ins_0, 0.0)
            fhs[cursor] = (rgt, top_ins_0 + vtrk, 0.0)
            rhs[cursor] = (rgt, t_3 * top_ins_0 + o_3 * btm_ins_0, 0.0)
            rh_types[cursor] = straight_edge
            cursor = cursor + 1

            cos[cursor] = (rgt_ins_0, top, 0.0)
            fhs[cursor] = (t_3 * rgt_ins_0 + o_3 * lft_ins_0, top, 0.0)
            rhs[cursor] = (rgt_ins_0 + vtrk, top, 0.0)
            fh_types[cursor] = straight_edge
            cursor = cursor + 1
        else:
            cos[cursor] = (rgt, top, 0.0)
            fhs[cursor] = (t_3 * rgt + o_3 * lft_ins_0, top, 0.0)
            rhs[cursor] = (rgt, t_3 * top + o_3 * btm_ins_0, 0.0)
            fh_types[cursor] = straight_edge
            rh_types[cursor] = straight_edge
            cursor = cursor + 1

        crv_data = bpy.data.curves.new("Rectangle", "CURVE")
        crv_data.dimensions = "2D"
        crv_data.fill_mode = self.fill_mode
        crv_data.extrude = self.extrude_thick
        crv_data.offset = self.extrude_off
        crv_splines = crv_data.splines
        spline = crv_splines.new("BEZIER")
        spline.use_cyclic_u = True
        spline.resolution_u = self.res_u
        bz_pts = spline.bezier_points

        # Spline already contains one Bezier point.
        bz_pts.add(kn_count - 1)
        knt_index = 0
        for knot in bz_pts:
            knot.handle_left_type = rh_types[knt_index]
            knot.handle_right_type = fh_types[knt_index]
            knot.co = cos[knt_index]
            knot.handle_left = rhs[knt_index]
            knot.handle_right = fhs[knt_index]
            knt_index = knt_index + 1

        crv_obj = bpy.data.objects.new(crv_data.name, crv_data)
        crv_obj.location = context.scene.cursor.location
        context.scene.collection.objects.link(crv_obj)
        return {"FINISHED"}


def menu_func(self, context):
    self.layout.operator(RndRectCurveMaker.bl_idname, icon="META_PLANE")


def register():
    bpy.utils.register_class(RndRectCurveMaker)
    bpy.types.VIEW3D_MT_curve_add.append(menu_func)


def unregister():
    bpy.utils.unregister_class(RndRectCurveMaker)
    bpy.types.VIEW3D_MT_curve_add.remove(menu_func)
