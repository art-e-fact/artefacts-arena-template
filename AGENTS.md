Source the python venv with `source setup.sh`
/submodules/* are third-party. Don't edit them unless the user asks you to.
Keep the implementation as consise and readable as possible. Add short comments to where it helps the understanding.

## Layout

`arena_composer/` is a mixed maturin project: Python under `python/`, Rust under `src/`,
one package. Python owns Arena (registries, USD reads, the placement solver); Rust owns the
Bevy viewer. The contract between them is the scene JSON `resolve_layout` produces — nothing
in the Rust half imports Arena.

```bash
arena-view environments/tasks/banana_in_bowl.yaml   # resolve a layout and look at it
```

Iterating on the viewer alone is much faster through the JSON, which skips Arena's import and
the solve:

```bash
arena-resolve-layout environments/tasks/banana_in_bowl.yaml --output scene.json
cd arena_composer && cargo run --bin arena-viewer -- ../scene.json
```

### Projection

`spawn.rs` draws only the stage's **default prim** subtree, which is what Isaac Lab composes
in when it spawns an asset. Some Kit-authored assets keep viewport cameras, render settings
and a 50 m collision ground plane outside it.

`material.rs` installs a `SchemaRegistry` that replaces `usd_bevy`'s material route, for two
things the Arena assets need: texture paths taken from openusd's *resolved* value rather than
the string as authored, and `GeomSubset` bindings split into a mesh apiece (Isaac's robots
shade per face subset). It mirrors `SchemaRegistry::builtin()`'s list, so a `usd_bevy` bump
should be checked against it.

What still doesn't draw: MDL materials whose look lives in the `.mdl` file rather than in USD
inputs (the maple table), and instanceable prims reached through a payload, which openusd
composes into an empty prototype (the robot's stand).

`cargo test` covers the frame conventions and material routing; the two `#[ignore]`d tests
project real cached assets and need `arena-resolve-layout` to have run first
(`cargo test -- --ignored`).
