# VRGestures fork of CyberpunkVRPort

A personal fork of [dariulone/cyberpunk-vr-port](https://github.com/dariulone/cyberpunk-vr-port) (MIT), kept as
close to upstream as possible. Branch `vrgestures-0.1.9` = upstream 0.1.9 plus:

1. **Bone limit 800 -> 1024** (`VRIK_MAX_BONES`, `g_VRBoneParent`, the meta-rig copy loop). A rig over the limit is
   refused by `ReadPlayerBinding`, which silently turns off body/arm tracking. Measured in game: bald with arms put
   away 619 bones, with a hair that has physics bones 701, the same hair with Gorilla Arms deployed 849.
   Over-limit rigs are now logged: `VRIK: player meta-rig has N bones, limit is 1024`.
2. **Launcher fires on trigger release** (`vrport_cyberware.reds`), only when the TweakXL flat
   `VRGestures.launcherFireOnRelease` is true (shipped by the VRGestures mod). Off otherwise: upstream behaviour.
3. **Fists/melee (class 5) are not handed to the left hand** by the two-hand carry (`CyberpunkVRPort_Weapon/init.lua`).

The changes live in `vrgestures/apply_patches.py` as exact text replacements (each must match once), applied
to the untouched upstream files at build time, so a new upstream release only needs that script re-checked.

Build: `.github/workflows/build-dll.yml` (GitHub Actions, windows-2022), against RED4ext.SDK master `5246e659`
(patch 2.5 types). The artifact holds the DLL and the two scripts; install it over the official 0.1.9.
