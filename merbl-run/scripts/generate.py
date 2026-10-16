"""
merbl run - parametric generator.

Builds the same parts the guide teaches (base, swept track, funnel, marble)
and exports printable STL files into ../cad/.

All units are millimetres. Z is up. Base top surface is at z = BASE_T.
Run:  python3 scripts/generate.py
"""
import os
import numpy as np
import trimesh

OUT = os.path.join(os.path.dirname(__file__), "..", "cad")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- parameters
MARBLE_D = 8.0
TRACK_ID = 9.0            # inner diameter (marble + 1 mm slack)
TRACK_OD = 14.0           # outer diameter (2.5 mm wall)
SLOT_HALF_DEG = 40.0      # open slot on top, half angle
BASE_W = BASE_D = 140.0   # under the 150 x 150 limit
BASE_T = 3.0              # under the 4 mm limit
SLOPE_DEG = 5.0           # downhill angle of the track
LANE_GAP = 27.0           # centre to centre distance of lanes
TURN_R = LANE_GAP / 2.0   # 13.5 mm -> above the 12 mm fillet minimum
STEP = 1.0                # centreline sample spacing

# funnel (guide: 10 mm hole, 20 mm drop, 95 deg wall, 3 mm walls, 12 mm rim)
F_HOLE_R = 5.0
F_DROP = 20.0
F_ANGLE = 95.0
F_LEN = 26.0
F_WALL = 3.0
F_RIM_H = 12.0
F_CENTER = np.array([35.0, -35.0])


# ------------------------------------------------------------- centreline
def build_path():
    """2D plan path made of straights and tangent arcs, then lifted with a
    constant downhill slope. Returns Nx3 points (z is the tube centre)."""
    pts = []

    def line(p0, p1):
        p0, p1 = np.array(p0, float), np.array(p1, float)
        n = max(2, int(np.linalg.norm(p1 - p0) / STEP))
        for t in np.linspace(0, 1, n, endpoint=False):
            pts.append(p0 + (p1 - p0) * t)

    def arc(c, r, a0, a1):
        n = max(4, int(abs(a1 - a0) * r / STEP))
        for a in np.linspace(a0, a1, n, endpoint=False):
            pts.append(np.array(c) + r * np.array([np.cos(a), np.sin(a)]))

    X = 48.0
    y1, y2, y3 = 54.0, 27.0, 0.0
    fx = F_CENTER[0] - 20.0                    # entry lane, 20 mm from funnel axis
    x3 = fx - TURN_R
    line((-X, y1), (X, y1))
    arc((X, y1 - TURN_R), TURN_R, np.pi / 2, -np.pi / 2)        # clockwise
    line((X, y2), (-X, y2))
    arc((-X, y2 - TURN_R), TURN_R, np.pi / 2, 3 * np.pi / 2)    # counter-clockwise
    line((-X, y3), (x3, y3))
    arc((x3, y3 - TURN_R), TURN_R, np.pi / 2, 0.0)              # clockwise to -y
    line((fx, y3 - TURN_R), (fx, F_CENTER[1] + 2.0))
    pts.append(np.array([fx, F_CENTER[1] + 2.0]))
    p2 = np.array(pts)

    seg = np.linalg.norm(np.diff(p2, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    total = s[-1]
    # funnel rim crossing: tube floor must clear the rim wall top
    z_end = rim_top_z() + TRACK_OD / 2 + 1.5
    z = z_end + (total - s) * np.tan(np.radians(SLOPE_DEG))
    return np.column_stack([p2, z]), total


def rim_top_z():
    tan_a = np.tan(np.radians(F_ANGLE - 90.0))
    z_rim = BASE_T + F_DROP + (F_LEN * np.cos(np.radians(F_ANGLE - 90.0))) * tan_a
    return z_rim + F_RIM_H


# ------------------------------------------------------------- track sweep
def sweep_track(path):
    """Sweep the open ring profile (9 mm ID, 14 mm OD, slot on top) along path."""
    ro, ri = TRACK_OD / 2, TRACK_ID / 2
    m = 24
    phis = np.radians(np.linspace(SLOT_HALF_DEG, 360 - SLOT_HALF_DEG, m + 1))
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1)[:, None]
    up = np.array([0, 0, 1.0])
    N = up - (T @ up)[:, None] * T
    N /= np.linalg.norm(N, axis=1)[:, None]
    B = np.cross(T, N)

    verts, per = [], 2 * (m + 1)
    for i in range(len(path)):
        for r in (ro, ri):
            for ph in phis:
                verts.append(path[i] + r * (np.cos(ph) * N[i] + np.sin(ph) * B[i]))
    verts = np.array(verts)

    def vid(i, ring, k):               # ring 0 = outer, 1 = inner
        return i * per + ring * (m + 1) + k

    faces = []
    for i in range(len(path) - 1):
        for k in range(m):
            for ring in (0, 1):
                a, b = vid(i, ring, k), vid(i, ring, k + 1)
                c, d = vid(i + 1, ring, k + 1), vid(i + 1, ring, k)
                faces += [[a, b, c], [a, c, d]]
        for k in (0, m):               # flat lips of the slot
            a, b = vid(i, 0, k), vid(i, 1, k)
            c, d = vid(i + 1, 1, k), vid(i + 1, 0, k)
            faces += [[a, b, c], [a, c, d]]
    for i in (0, len(path) - 1):       # end caps
        for k in range(m):
            a, b = vid(i, 0, k), vid(i, 0, k + 1)
            c, d = vid(i, 1, k + 1), vid(i, 1, k)
            faces += [[a, b, c], [a, c, d]]
    mesh = trimesh.Trimesh(verts, faces, process=True)
    trimesh.repair.fix_winding(mesh)
    trimesh.repair.fix_normals(mesh)
    return mesh


# ------------------------------------------------------------------ funnel
def make_funnel():
    a = np.radians(F_ANGLE - 90.0)
    tan_a, cos_a = np.tan(a), np.cos(a)
    top = lambda r: F_DROP + (r - F_HOLE_R) * tan_a
    under = lambda r: top(r) - F_WALL / cos_a
    r_rim = F_HOLE_R + F_LEN * cos_a
    r_out = r_rim + F_WALL
    prof = [
        (F_HOLE_R, 0), (F_HOLE_R, F_DROP), (r_rim, top(r_rim)),
        (r_rim, top(r_rim) + F_RIM_H), (r_out, top(r_rim) + F_RIM_H),
        (r_out, under(r_out)), (F_HOLE_R + F_WALL, under(F_HOLE_R + F_WALL)),
        (F_HOLE_R + F_WALL, 0),
    ]
    prof = np.array(prof, float)
    sections = 120
    n = len(prof)
    verts = []
    for j in range(sections):
        th = 2 * np.pi * j / sections
        for r, z in prof:
            verts.append([r * np.cos(th), r * np.sin(th), z])
    faces = []
    for j in range(sections):
        j2 = (j + 1) % sections
        for i in range(n):
            i2 = (i + 1) % n
            a_, b_ = j * n + i, j * n + i2
            c_, d_ = j2 * n + i2, j2 * n + i
            faces += [[a_, b_, c_], [a_, c_, d_]]
    mesh = trimesh.Trimesh(np.array(verts), faces, process=True)
    trimesh.repair.fix_winding(mesh)
    trimesh.repair.fix_normals(mesh)
    return mesh, r_out


def main():
    path, total = build_path()
    track = sweep_track(path)

    funnel, r_out = make_funnel()
    funnel_local = funnel.copy()
    funnel.apply_translation([F_CENTER[0], F_CENTER[1], BASE_T])

    base = trimesh.creation.box([BASE_W, BASE_D, BASE_T])
    base.apply_translation([0, 0, BASE_T / 2])

    marble = trimesh.creation.icosphere(subdivisions=3, radius=MARBLE_D / 2)

    marble_print = marble.copy()
    marble_print.apply_translation([0, 0, MARBLE_D / 2])
    export = {
        "base.stl": base,
        "track_assembled_position.stl": track,
        "funnel.stl": funnel_local,
        "marble.stl": marble_print,
    }
    for name, m in export.items():
        m.export(os.path.join(OUT, name))

    asm = trimesh.util.concatenate([base, track, funnel])
    asm.export(os.path.join(OUT, "assembly.stl"))

    # ---- report
    s = np.diff(path[:, :2], axis=0)
    ang = np.arctan2(s[:, 1], s[:, 0])
    dang = np.abs(np.diff(np.unwrap(ang)))
    seglen = np.linalg.norm(s, axis=1)[1:]
    kappa = dang / np.maximum(seglen, 1e-9)
    curved = kappa[kappa > 1e-3]
    min_r = 1.0 / curved.max() if len(curved) else float("inf")
    print(f"path length            : {total:.1f} mm")
    print(f"slope                  : {SLOPE_DEG} deg")
    print(f"track start z / end z  : {path[0,2]:.1f} / {path[-1,2]:.1f} mm")
    print(f"min bend radius        : {min_r:.1f} mm (must be > 12)")
    print(f"track lowest underside : {path[:,2].min() - TRACK_OD/2:.1f} mm (base top = {BASE_T})")
    print(f"funnel outer radius    : {r_out:.1f} mm, centre {F_CENTER.tolist()}")
    print(f"assembly bounds        : {asm.bounds.round(1).tolist()}")
    for name, m in {"track": track, "funnel": funnel, "base": base, "marble": marble}.items():
        print(f"{name:7s} watertight={m.is_watertight} volume={m.volume:.0f} mm3")


if __name__ == "__main__":
    main()
