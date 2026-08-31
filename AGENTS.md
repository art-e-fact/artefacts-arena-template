Source the python venv with `source setup.sh`
/submodules/* are third-party. Don't edit them unless the user asks you to.
Keep the implementation as consise and readable as possible. Add short comments to where it helps the understanding.

## Layout

`arena_composer/` is a mixed maturin project: Python under `python/`, Rust under `src/`,
one package. **Python owns everything that needs OpenUSD** — Arena's registries and placement
solver, plus reading the assets' geometry and materials. **Rust owns the Bevy viewer** and
opens no USD at all. The contract between them is the MessagePack payload
`arena_composer.payload` packs.

```bash
arena-view environments/tasks/banana_in_bowl.yaml   # resolve a layout and look at it
```

Iterating on the viewer alone is much faster through a packed payload, which skips Arena's
import, the solve and the USD reads:

```bash
arena-resolve-layout environments/tasks/banana_in_bowl.yaml --payload scene.msgpack
cd arena_composer && cargo run --bin arena-viewer -- ../scene.msgpack
```

`--output` still writes the resolver's JSON dump. That stays the human- and agent-readable
artifact; the payload is the renderer's, and carries a strict subset of its fields.

### The payload

MessagePack, not JSON: the geometry is megabytes of float arrays, and JSON spends ~760 ms
formatting them as decimal text against ~2 ms for `bin` blobs. Arrays travel as little-endian
`f32`/`u32` and are cast back with one copy (`bytemuck::pod_collect_to_vec` — a `bin` payload
lands at an arbitrary offset, so it cannot be assumed aligned). Everything around them stays
an ordinary map, so unknown keys are ignored and absent ones default, exactly as the JSON did.

Geometry arrives in **Arena's frame** — Z-up, metres — with the transforms already baked into
the vertex positions. That is what lets the Rust side hold no USD conventions: no up-axis, no
unit scale, no xform-op ordering, no shared matrix convention (USD composes row-vector
transforms, glam column-vector ones). The cost is that a mesh repeated inside one asset is
emitted twice, and that nothing can move at runtime; assets sharing a USD are still extracted
once. Revisit both when the viewer needs to animate.

### Extraction (`python/arena_composer/usd/`)

`extract.py` draws only the stage's **default prim** subtree, which is what Isaac Lab composes
in when it spawns an asset — Kit-authored assets keep viewport cameras, render settings and
the odd 50 m collision ground plane outside it. It also unbakes the default prim's own
`xformOp:scale` (Isaac Lab's spawner ignores it, and the resolver's bounding boxes are
computed the same way), treats an **unauthored** `upAxis`/`metersPerUnit` as Z-up metres
rather than USD's Y-up centimetres, and descends into instance proxies.

`material.py` resolves texture paths through `Sdf.AssetPath.resolvedPath`, never the authored
string, and drops paths that do not exist — which is what keeps the viewer's asset server from
logging a miss per texture. Every field is a list of input names tried in order, because these
assets mix `UsdPreviewSurface`, OmniPBR/OmniSurface MDL, per-material bespoke MDL modules
(the galileo backgrounds' PascalCase `AlbedoTexture`/`MainNormalInput`) and bare `displayColor`.
Names go in a slot's list only once an asset proves the mapping — a texture named for its own
channel layout, or a filename suffix that says what it is. Guessing costs more than it saves:
handing a single-channel OmniPBR `metallic_texture` to Bevy's glTF-packed
`metallic_roughness` slot makes it read roughness out of a metallic map's green channel.
Maps that genuinely pack occlusion/roughness/metallic in glTF's channel order feed the
`metallic_roughness` and `occlusion` slots from the same file.

`mesh.py` flattens everything to face corners (no interpolation branches downstream), flips V
into the renderer's convention (USD's `st` origin is bottom-left, glTF's and Bevy's is top
left) and splits `GeomSubset` bindings into a piece apiece — Isaac's robots shade per face
subset, and reading only the gprim's own binding leaves every link untextured. Normals come
from `primvars:normals` before the `normals` attribute, which is both USD's precedence rule
and the only way to read the exporters that write nothing else. Primvars are taken by name
*and* type, and authored values are checked for NaN: assets in this library do author a
`token[]` where a float array belongs, and NaN UVs that spread through tangent generation.
`shapes.py` tessellates the analytic gprims; not optional, since the maple table is a `Cube`
on four `Cylinder`s.

What still doesn't draw: MDL materials whose look lives in the `.mdl` file rather than in USD
inputs (the maple table authors only `project_uvw` and `world_or_object`), prims that bind no
material at all (~13% of the galileo backgrounds), and lights authored inside an asset. The
separate single-channel OmniPBR `metallic_texture`/`reflectionroughness_texture` pair is read
as its scalar constants instead; packing the two into one image needs a texture cache.

Sweeping the whole local asset cache is the cheap way to find these — extraction needs only
`usd-core`, so a few hundred assets go through `extract()` in a couple of minutes with no Kit
bootstrap, and the failures sort themselves into "renders nothing", "renders grey" and
"crashes". A `payloads/*.usda` fragment that yields no nodes is not a bug: those are
materials-only or physics-only sublayers that mean nothing opened standalone.

### Tests

`cargo test` covers the payload decode, mesh/material building and the frame conventions, with
no fixtures needed. One `#[ignore]`d test runs the whole draw path against a real packed scene:

```bash
arena-resolve-layout environments/tasks/droid_banana_on_plate_maple_table.yaml --payload scene.msgpack
cd arena_composer && ARENA_COMPOSER_PAYLOAD=../scene.msgpack cargo test -- --ignored
```

`pytest arena_composer/tests` covers the USD side against minimal USDAs written inline:
`test_usd_material.py` for the shading dialects, `test_usd_mesh.py` for the geometry reader.
Each fixture there is a reduction of something a real asset authors, so the comments name the
asset — several of them look like mistakes in the fixture until you meet them in the wild. See
the TODO at the top of each file for what is still uncovered.
