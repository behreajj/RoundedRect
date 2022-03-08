import bpy
import math
from bpy.props import (
    IntProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty)

bl_info = {
    "name": "Create Rounded Rect Curve",
    "author": "Jeremy Behreandt",
    "version": (0, 1),
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

    res_u: IntProperty(
        name="Resolution",
        description="Corner resolution",
        min=1,
        soft_max=64,
        default=12)

    fill_mode: EnumProperty(
        items=[
            ("NONE", "None", "None", 1),
            ("BACK", "Back", "Back", 2),
            ("FRONT", "Front", "Front", 3),
            ("BOTH", "Both", "Both", 4)],
        name="Fill Mode",
        default="BOTH",
        description="Fill mode to use")

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

        # Validate corners.
        lft = min(lbx, ubx)
        rgt = max(lbx, ubx)
        btm = min(lby, uby)
        top = max(lby, uby)

        # Protect from zero dimension curves.
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

        # Validate corner insetting.
        # Half the short edge is the maximum size.
        se = 0.5 * min(rgt - lft, top - btm)
        vtl = se * min(max(tl, eps), 1.0 - eps)
        vtr = se * min(max(tr, eps), 1.0 - eps)
        vbr = se * min(max(br, eps), 1.0 - eps)
        vbl = se * min(max(bl, eps), 1.0 - eps)

        # For calculating handle magnitude.
        vtlk = vtl * k
        vblk = vbl * k
        vbrk = vbr * k
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

        # Knot coordinates.
        cos = [
            (lft_ins_0, top, 0.0),
            (lft, top_ins_1, 0.0),
            (lft, btm_ins_1, 0.0),
            (lft_ins_1, btm, 0.0),
            (rgt_ins_1, btm, 0.0),
            (rgt, btm_ins_0, 0.0),
            (rgt, top_ins_0, 0.0),
            (rgt_ins_0, top, 0.0)]

        # Fore-handles.
        fhs = [
            (lft_ins_0 - vtlk, top, 0.0),
            (lft, t_3 * top_ins_1 + o_3 * btm_ins_1, 0.0),
            (lft, btm_ins_1 - vblk, 0.0),
            (t_3 * lft_ins_1 + o_3 * rgt_ins_1, btm, 0.0),
            (rgt_ins_1 + vbrk, btm, 0.0),
            (rgt, t_3 * btm_ins_0 + o_3 * top_ins_0, 0.0),
            (rgt, top_ins_0 + vtrk, 0.0),
            (t_3 * rgt_ins_0 + o_3 * lft_ins_0, top, 0.0)]

        # Rear-handles.
        rhs = [
            (t_3 * lft_ins_0 + o_3 * rgt_ins_0, top, 0.0),
            (lft, top_ins_1 + vtlk, 0.0),
            (lft, t_3 * btm_ins_1 + o_3 * top_ins_1, 0.0),
            (lft_ins_1 - vblk, btm, 0.0),
            (t_3 * rgt_ins_1 + o_3 * lft_ins_1, btm, 0.0),
            (rgt, btm_ins_0 - vbrk, 0.0),
            (rgt, t_3 * top_ins_0 + o_3 * btm_ins_0, 0.0),
            (rgt_ins_0 + vtrk, top, 0.0)]

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
        bz_pts.add(7)
        knt_index = 0
        for knot in bz_pts:
            knot.handle_left_type = "FREE"
            knot.handle_right_type = "FREE"
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
