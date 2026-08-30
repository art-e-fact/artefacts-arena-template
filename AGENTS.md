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
assets mix `UsdPreviewSurface`, OmniPBR/OmniSurface MDL and bare `displayColor`.

`mesh.py` flattens everything to face corners (no interpolation branches downstream) and
splits `GeomSubset` bindings into a piece apiece — Isaac's robots shade per face subset, and
reading only the gprim's own binding leaves every link untextured. `shapes.py` tessellates the
analytic gprims; not optional, since the maple table is a `Cube` on four `Cylinder`s.

What still doesn't draw: MDL materials whose look lives in the `.mdl` file rather than in USD
inputs (the maple table), and lights authored inside an asset.

### Tests

`cargo test` covers the payload decode, mesh/material building and the frame conventions, with
no fixtures needed. One `#[ignore]`d test runs the whole draw path against a real packed scene:

```bash
arena-resolve-layout environments/tasks/droid_banana_on_plate_maple_table.yaml --payload scene.msgpack
cd arena_composer && ARENA_COMPOSER_PAYLOAD=../scene.msgpack cargo test -- --ignored
```

`pytest arena_composer/tests` covers the USD side against minimal USDAs written inline — see
the TODO at the top of `test_usd_material.py` for what is still uncovered.
