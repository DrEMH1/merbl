"""
merbl run - editable CAD export (STEP, B-rep solids).

Uses the same parameters and centre-line as generate.py, but builds real
solids with CadQuery: the track is a profile extruded along the straights
and swept along the turns (like the Sweep feature in Onshape), the funnel is
a revolved profile, the marble is a sphere, the base is an extruded box.

Run:  python3 scripts/generate_step.py      (needs: pip install cadquery)
"""
import os, sys
import numpy as np
import cadquery as cq

sys.path.insert(0, os.path.dirname(__file__))
import generate as g

OUT = os.path.join(os.path.dirname(__file__), "..", "cad")


def profile(p0, tan):
    """Open ring (9 mm ID, 14 mm OD, slot on top) on a plane normal to the path."""
    ro, ri = g.TRACK_OD / 2, g.TRACK_ID / 2
    a0 = np.radians(g.SLOT_HALF_DEG)
    up = cq.Vector(0, 0, 1)
    xd = (up - tan * up.dot(tan)).normalized()
    pl = cq.Plane(origin=p0, xDir=xd, normal=tan)
    P = lambda r, ph: (r * np.cos(ph), r * np.sin(ph))
    return (cq.Workplane(pl).moveTo(*P(ro, a0))
            .threePointArc(P(ro, np.pi), P(ro, 2 * np.pi - a0))
            .lineTo(*P(ri, 2 * np.pi - a0))
            .threePointArc(P(ri, np.pi), P(ri, a0)).close())


def make_track():
    path, _ = g.build_path()
    s = np.diff(path[:, :2], axis=0)
    ang = np.unwrap(np.arctan2(s[:, 1], s[:, 0]))
    bend = np.concatenate([[False], np.abs(np.diff(ang)) > 1e-4, [False]])
    runs, st = [], 0
    for i in range(1, len(path)):
        if bend[i] != bend[st]:
            runs.append((st, i, bend[st])); st = i
    runs.append((st, len(path) - 1, bend[st]))

    solids = []
    for a, b, curved in runs:
        if b - a < 2:
            continue
        seg = [cq.Vector(*path[i]) for i in range(a, b + 1)]
        if not curved:                                   # straight: extrude
            d = seg[-1] - seg[0]
            solids.append(profile(seg[0], d.normalized()).extrude(d.Length))
        else:                                            # turn: sweep
            step = max(1, (len(seg) - 1) // 14)
            pts = seg[::step]
            if pts[-1] != seg[-1]:
                pts.append(seg[-1])
            spl = cq.Edge.makeSpline(pts)
            wire = cq.Workplane(obj=cq.Wire.assembleEdges([spl]))
            solids.append(profile(pts[0], spl.tangentAt(0)).sweep(wire, isFrenet=True))
    track = solids[0]
    for sol in solids[1:]:
        track = track.union(sol)
    return track


def make_funnel():
    a = np.radians(g.F_ANGLE - 90.0)
    top = lambda r: g.F_DROP + (r - g.F_HOLE_R) * np.tan(a)
    under = lambda r: top(r) - g.F_WALL / np.cos(a)
    r_rim = g.F_HOLE_R + g.F_LEN * np.cos(a)
    r_out = r_rim + g.F_WALL
    pts = [(g.F_HOLE_R, 0), (g.F_HOLE_R, g.F_DROP), (r_rim, top(r_rim)),
           (r_rim, top(r_rim) + g.F_RIM_H), (r_out, top(r_rim) + g.F_RIM_H),
           (r_out, under(r_out)), (g.F_HOLE_R + g.F_WALL, under(g.F_HOLE_R + g.F_WALL)),
           (g.F_HOLE_R + g.F_WALL, 0)]
    return (cq.Workplane("XZ").polyline(pts).close()
            .revolve(360, (0, 0, 0), (0, 1, 0)))


def main():
    base = cq.Workplane("XY").box(g.BASE_W, g.BASE_D, g.BASE_T, centered=(True, True, False))
    track = make_track()
    funnel_local = make_funnel()
    funnel = funnel_local.translate((g.F_CENTER[0], g.F_CENTER[1], g.BASE_T))
    marble = cq.Workplane("XY").sphere(g.MARBLE_D / 2).translate((0, 0, g.MARBLE_D / 2))

    parts = {"base": base, "track": track, "funnel": funnel_local, "marble": marble}
    for name, w in parts.items():
        cq.exporters.export(w, os.path.join(OUT, f"{name}.step"))

    asm = (cq.Assembly(name="merbl_run")
           .add(base, name="base", color=cq.Color(0.75, 0.75, 0.78))
           .add(track, name="track", color=cq.Color(0.2, 0.55, 0.9))
           .add(funnel, name="funnel", color=cq.Color(0.2, 0.55, 0.9)))
    asm.save(os.path.join(OUT, "merbl_run_assembly.step"))

    for name, w in {**parts, "funnel_in_place": funnel}.items():
        s = w.val()
        print(f"{name:16s} valid={s.isValid()} solids={len(w.solids().vals())} volume={s.Volume():.0f} mm3")


if __name__ == "__main__":
    main()
