# mabinogi_blender_addons

Blender addons for importing Mabinogi character models and animations.

| Addon | File | Imports |
|---|---|---|
| `io_import_mabinogi_frm.py` | `.frm` | Framework (skeleton) as an armature. Can also export `.frm`. |
| `io_import_mabinogi_pmg.py` | `.pmg` | Mesh group, with textures and skinning |
| `io_import_mabinogi_ani.py` | `.ani` | Animation, onto the selected armature |

Tested with Blender 5.2. Drag-and-drop import needs Blender 4.2 or newer.

## Installation

1. In Blender, open **Edit > Preferences > Add-ons**.
2. Choose **Install from Disk** and select each `.py` file.
3. Enable the three Mabinogi addons.

Or copy the `.py` files into your Blender addons folder, for example
`~/.config/blender/<version>/scripts/addons/` on Linux.

## Usage

There are three ways to import:

- **File > Import**, under the Mabinogi entries
- The **Mabinogi** tab in the 3D viewport sidebar (press `N`)
- Dragging a `.frm`, `.pmg` or `.ani` file into the 3D viewport

To build a character:

1. Import the framework, for example `gfx/char/human/female/female_framework.frm`.
2. With the armature selected, import body, face, hair and clothing `.pmg` files.
   They're parented and skinned to the armature.
3. With the armature selected, import an `.ani` file from the `anim` folder.

Each `.pmg` goes into its own collection, inside the armature's collection when
imported onto one. Many files contain several subgroups: variants the game
swaps between, such as hand poses (`fistl`, `palmr`), hair shapes (`h1` to
`h6`) or weapon positions. Only the first is shown. The rest go in a hidden
"variants" collection, which you can show from the Outliner.

Models are converted from Mabinogi's Y-up axis to Blender's Z-up, and scaled
to 0.01. A character comes in about 1.3 m tall. Both options can be changed
in the import dialog.

## Textures

Each `.pmg` stores a texture name for every mesh part. The importer searches
for it in the game's `data/material` folder, which it finds automatically from
the `.pmg`'s location if you import from an extracted `data` folder. You can
also set the folder yourself in the pmg addon's preferences.

## Game materials

With **Game Materials** on (the default), the pmg importer recreates the game's
materials from `data/material/_define`. Each material there lists the
textures that use it and points to a render state, which holds the original
Direct3D 9 setup. The importer rebuilds that as shader nodes:

- The texture stages, such as texture × lighting × 2, then × gloss map × 4.
  Gloss maps from `material/glossmap` are applied like a matcap, which gives
  characters their soft gradient shading.
- Alpha test cutouts, alpha blending and additive blending
- Backface culling

The result is unlit (an Emission shader), as in the game, so scene lights
don't affect it. The lighting term is a single value in the shared
**Mabinogi Light** node group, which sets the brightness of every imported
material. For colours closest to the game, set the scene's
**Color Management > View Transform** to **Standard**.

Turn Game Materials off for a plain Principled BSDF with the texture, which
reacts to Blender's lights.

Many textures, such as hair, clothing and monster skins, are greyscale or
colour masks. The game dyes them at runtime, so they come in grey or pink.
The importer doesn't apply dye colours.

## Credits

Original addons by Tachiorz. Updated for Blender 2.80 and 5.x by CodfishBender.
