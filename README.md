[README.md](https://github.com/user-attachments/files/33594047/README.md)
# merbl run

A 3D-printable marble race built from the parts taught in the [merbl guide](https://github.com/karnxx/merbl/blob/main/guide.md) (Half Life, week 2: CAD).

![preview](images/preview.png)

## What it is

An 8 mm marble enters the high end of an open-top track, rolls down three lanes (two 180° switchbacks), then a final turn drops it onto a funnel where it circles and falls through the hole.

## Parts

| File (`cad/`) | What | Key dimensions |
|---|---|---|
| `base.stl` | Flat base | 140 x 140 x 3 mm (limit: 150 x 150 x 4) |
| `track_assembled_position.stl` | Track swept along a 3D path | 9 mm inner / 14 mm outer diameter, 2.5 mm wall, 5° downhill, bends of 13.5 mm radius (guide minimum: above 12 mm), 369 mm long |
| `funnel.stl` | Custom track: funnel | 10 mm hole, 20 mm drop, 95° wall, 3 mm walls, 12 mm rim |
| `marble.stl` | The marble | 8 mm diameter |
| `assembly.stl` | Base + track + funnel in place | Reference only, do not print |

`track_assembled_position.stl` and `funnel.stl` keep their assembled coordinates, so slice each with its own orientation. In the assembly the funnel sits at x = 35, y = -35 on top of the base.

## Printing

- Use thin tree supports in the slicer, as the guide recommends. They hold the track up and double as its mounting.
- Before printing, check the support preview: supports may touch the outside of the track but never the inside where the marble rolls.
- After printing, roll the marble through to test.

## Rebuild or change it

`python3 scripts/generate.py` regenerates every STL from the parameters at the top of the file (slope, lane gap, funnel size...). It needs `numpy` and `trimesh`.

## Design checks

- Base under 150 x 150 x 4 mm: yes (140 x 140 x 3).
- Bend radius above 12 mm: yes (13.5 mm, measured from the path).
- Track clears the funnel rim wall: yes (track underside 38.8 mm, rim top 37.3 mm).
- All parts are watertight meshes.

## Known limitations

- The funnel is printed standing on the base, so the marble ends up resting in the drop tube above the base. Lift the funnel to take it out.
- Parts are STL meshes, not a parametric Onshape model.

## Process and credits

- Design follows the merbl guide by karnxx.
- The models and generator script were produced with help from an AI assistant (Claude).
- Time log: add your Hackatime or Lapse screenshots here.
