# VRGestures fork of CyberpunkVRPort

A personal fork of [dariulone/cyberpunk-vr-port](https://github.com/dariulone/cyberpunk-vr-port) (MIT), kept as
close to upstream as possible. Branch `vrgestures-0.2.0` = upstream 0.2.0 plus the list below, re-fitted:

- **Dropped:** 31 (upstream took the log line out). The save half of 9 (upstream saves `xr_weapon_laser_dot`
  itself; `GetVRLaserSight` stays). The gun's beam of 6 (upstream draws the weapon hand's gun as a dot in both
  eyes); the second dot (`SetVRAuxLaser`: the left gun, the launcher, the blink and knife marks) stays, as a dot
  (`CyberpunkVR_LaserBeam` = 0). 13's beam start has nothing to move; its setting is kept for 15/34/39's anchors.
- **Re-anchored:** 21 (the learner also skips a left-hand weapon now), 45 (after the PSVR2 triangle shift).
- **Build:** cargo is optional (the release zip ships `scc_lib.dll`); MSVC 14.44 crashes optimising the Lua
  host's `VKBindings.cpp`, so that file is built `/Od`. `vrgestures/build_local.ps1` builds,
  `vrgestures/install_local.ps1` installs the release zip with the fork's files over it.
- **52. Mailboxes between CET and the plugin's Lua host** (`VRGMailPut` / `Add` / `Get` / `Take`). 0.2.0 runs the
  port's Lua mods in its own host, out of CET's `GetMod`: VRGestures' wrist rows (50/51) and wrist sliders now go
  through boxes `vrg.wrist.rows`, `vrg.wrist.set` and `vrg.wrist.cfg`.

The list as it was on `vrgestures-0.1.9` (upstream 0.1.9 plus):

1. **Bone limit 800 -> 1024** (`VRIK_MAX_BONES`, `g_VRBoneParent`, the meta-rig copy loop). A rig over the limit is
   refused by `ReadPlayerBinding`, which silently turns off body/arm tracking. Measured in game: bald with arms put
   away 619 bones, with a hair that has physics bones 701, the same hair with Gorilla Arms deployed 849.
   Over-limit rigs are now logged: `VRIK: player meta-rig has N bones, limit is 1024`.
2. **Launcher fires on trigger release** (`vrport_cyberware.reds`), only when the TweakXL flat
   `VRGestures.launcherFireOnRelease` is true (shipped by the VRGestures mod). Off otherwise: upstream behaviour.
3. **Fists/melee (class 5) are not handed to the left hand** by the two-hand carry (`CyberpunkVRPort_Weapon/init.lua`).
4. **Build fix:** upstream's `CMakeLists.txt` adds `tools/rtti_dump`, which is not in the published tree, so a clean
   checkout does not configure. It is now added only when the folder exists.
5. **The left-trigger block also stops the guns** (`src/Hooks/XInput.cpp`). `SetVRLeftTriggerBlock` only zeroed the
   game's aim input; dual wielding and the launcher take the raw left trigger as their fire input, so Sandevistan
   (left palm at the ear + left trigger) also fired the left gun. A blocked trigger is now held off both.
6. **The laser under engine stereo, plus a launcher laser** (`src/Overlay/OverlayDebugDraw.cpp` and friends). 0.1.9's
   engine stereo draws both eyes side by side; the red dot was projected once across the whole frame (it sat at
   the left eye's right edge) and the right eye got none. It is now a beam from the muzzle to the barrel
   raycast's hit, projected per eye into each half. `SetVRAuxLaser(muzzle, hit)` draws a second, cyan beam
   (VRGestures: the projectile launcher), and the barrel raycast also tests the Dynamic group so the beam stops
   on enemies.
7. *(Removed: the temporary dual-wield shot diagnostics.)*
8. **Left-gun shots on the projectile path** (`src/Natives/OrientationProvider.cpp`). With a bullets-as-projectiles mod
   every shot goes through the projectile providers, which only knew the right barrel. A shot taken with the left
   trigger alone, two guns in hand, now starts at the left muzzle and flies along the left barrel (shotgun cone
   centred on it) and kicks the left hand. Both triggers at once still use the right barrel.
9. **The laser sight switch is saved** (`xr_laser_sight` in `vrport.ini`; it was off at every launch) and readable by
   scripts (`GetVRLaserSight`), so VRGestures' left-gun laser follows it.
10. **Both triggers: each gun's projectile leaves its own barrel.** The two guns' shots differ in one attack handle
    (the weapon); single-trigger shots teach which is which, and with both triggers the handle decides.
11. **The launcher aims with the hand.** `VRHandAimRay(side)` returns the controller's aim pose (its pointing ray)
    as a game-world ray; the launcher still spawns at the barrel but flies along it, instead of along two arm
    bones that sway with the animation (`vrport_launcher_aim.reds`, now in the build artifact too).
12. **One recoil latch per hand** on the projectile path, so two guns firing in the same frame (two automatic
    pistols, both triggers) each kick their own hand.
13. **The laser starts past a silencer.** `SetVRLaserStart(metres)` moves the drawn beam's start down the barrel;
    VRGestures sends the silencer length while the right gun is silenced. The shot is unchanged.
14. **No barrel raycast while the laser is off.** Only the laser reads the weapon module's per-frame barrel traces.
15. **Experimental: the launcher out with a gun in the right hand** (only while VRGestures' setting is on). The game's
    launcher equip no longer puts the gun away; the left trigger fires the launcher on its own button (press), the
    right trigger stays the gun's, and the dual-wield trigger merge stays out of it.
16. **Launcher with a gun, first-test fixes:** VRGestures tells the input merge every frame the launcher is out next
    to a gun (the port's cyberware kind is the pistol's then), so the left trigger fires the launcher instead of aiming.
17. **The launcher is not in the weapon cycle.** VRGestures brings it out as left-hand cyberware, which stays out after
    its shots; weapon cycling is the game's own again (dual-wield pairs included).
18. **Launcher with a gun stays out.** In that mode the pistol no longer flickers away when the launcher comes out,
    a right-hand request (the pistol drawn again, a weapon switch) no longer clears the launcher's keep-open (which had
    sent its shot along the head's aim and closed it after the shot), and the switch button switches the gun only.
19. **Launcher with a gun, said directly.** VRGestures tells the scripts the mode is on through the player as well as
    the TweakDB flat; the shot flies along the hand although the port's binding is the gun's; `VrgLauncherState()` reports
    the launcher's state and why it last closed, for VRGestures' log (temporary).
20. **Launcher with a gun, from the patch 19 log.** It no longer fires as it comes out; next to a gun it is not a left
    weapon (the right hand stays in its one-gun state instead of dual-wield); the gadget button's request is ignored
    while it is out, so the trigger fires the hand-aimed shot and the launcher stays out.
21. **The gun hand keeps its grip next to the launcher.** The launcher's animation curled the right hand into a fist
    beside the gun; the right hand's own learned grip is replayed on its fingers while the launcher is out next to a gun.
22. **That grip, learned clean and held throughout.** It is learned only while the right hand holds alone (never the
    launcher's fist), and also held on the passes the launcher's own graph drives once it is ready.
23. **The gun stays in the grip next to the launcher.** The launcher's animation also moved (and briefly hid) the bone
    the gun hangs from; its position, rotation and scale are learned with the grip and held with it.
24. **Temporary: why the gun hand's grip slipped.** Writes `VRGestures_grip_diag.log` (beside the exe) whenever the
    grip was not held, or the launcher graph's arm replay skipped, while the launcher was out next to a gun.
25. **Launcher with a gun through weapon changes.** Drawing a one-handed weapon keeps the launcher; the cancel input
    no longer closes it beside a gun; a launcher that can no longer stay backs out of its equip state instead of hanging.
26. **The grip's gun, seen from the hand slots.** The grip replay checks the right weapon slot instead of the player's
    equipped-weapon property, which read empty for long stretches beside the launcher (the flicker).
27. **The gun beside the launcher, in VRGestures' own word.** `SetVRLauncherWithGun(2)` = out with a gun in the right
    hand; the trigger merge and the grip replay use it, as the port's hand-slot mask also dropped out (the delayed shot).
28. **Temporary: the last equip request.** Recorded with the hand items before and after, for VRGestures' state log
    (a holster draw did nothing with the launcher out).
29. **A holster draw beside the launcher.** The right hand may equip a one-handed weapon while the launcher (arm
    cyberware) is in the left; the game held such an equip back for good.
30. **The temporary diagnostics come out** (24's grip log, 28's equip-request record). `VrgLauncherState()` stays for
    the CET console.
31. **No world-marker log line per head move.** Engine stereo logged each eye's HUD-camera move on every change,
    which is every head move (86,000 flushed lines in 34 minutes, from the HUD upload path); the line is removed.
32. **Two quick taps of X are the quick exit.** Hold X is still the normal exit; two taps inside 350 ms press B for
    350 ms, which a moving car takes as the game's QuickExit and a stopped one as the ordinary exit.
33. **The left stick click sprints again.** A click starts the sprint at once and it lasts while the stick moves; a click
    that becomes a D-pad, cyberware or menu chord is not a sprint. The full-forward gesture is off
    (`CyberpunkVR_SprintOnStickClick = 0` restores it). Shared slot 240 marks the port's own L3 for VRGestures.
34. **A scripted D-pad press.** `VRGPadPress(buttons, ms)` holds D-pad bits down for a moment; VRGestures' heal at
    the mouth presses D-pad up (UseConsumable).
35. **A smaller scanner zone.** The left-ear zone that opens the scanner on a left-grip squeeze is 15 cm instead of
    22 cm, so squeezes at the brow and the mouth no longer open it.
36. **The menu swipe for the left hand.** `VRGLeftSwipe()` reads the VR menu's swipe on the left hand (same distance,
    time, speed, slant and cooldown), unless the right hand dropped with it.
37. **The quickslot wheel.** A new menu module (`modules/quickwheel.lua`, kept whole in `vrgestures/files/`) draws
    Custom Quickslots' slots on a ring at the left hand on the menu's screen and reports the slot under the hand;
    VRGestures opens it on the left swipe and uses the slot the grip is let go over.
38. **A crouch ends the click sprint.** The right stick pushed down ends patch 33's sprint, and its crouch press
    waits (250 ms at most) for the sprint to end, since a crouch in a sprint is a slide.
39. **The dodge button is VRGestures' grip.** The right stick pushed up no longer dodges; `VRGPressDodge(ms)` presses
    the game's Dodge button (pad B) after the port's own B handling, so the game decides the dodge, dash and Air Dash.
41. **The right stick pushed up sprints**, like the left stick click (33). Temporary: a log line per stick-down crouch.
42. Temporary: a log line per hard push down, with every gate of the crouch.
43. **A held left stick click.** Held a full second with no chord, the click passes through to the game as a held L3
    until it is let go (and is not also a sprint).
44. **The stick-down crouch goes as soon as a sprint ends** (not a flat 250 ms later), and a quick push made in a
    sprint is kept instead of lost. The temporary crouch logging of 41 and 42 is removed.
45. **Left grip + left stick = the D-pad**, armed by a squeeze made with the stick at rest; stands aside for a
    two-handed gun, a left-hand carry, ladders, the monowire, cars, menus and cameras.
46. **No left grip + left stick click cyberware**; VRGestures' gestures use the cyberware.
47. **The left-grip D-pad works in cars** whenever the left hand is not at (or holding) the steering wheel.
48. **A wrist display**: scripts post small gauges (VRWristGauge / VRWristHudPlace) and the port draws them as their
    own OpenXR quad in the left controller's aim space (Runtimes/WristHud.cpp, in vrgestures/files/).
49. **The raw right stick Y for scripts** in shared slot 241 (CyberWings boosts while it is held up).
50. **Other mods' rows on the wrist readout**: GetMod("CyberpunkVRPort_WristHud").row(id, label, value, text, r, g, b)
    adds a label / bar / value row under health and RAM; setting(k, v) reads or sets a wrist.cfg value.
51. **Those rows take the buff icons' place** (below them was off the patch); the icons step aside while rows show.

The changes live in `vrgestures/apply_patches.py` as exact text replacements (each must match once), applied
to the untouched upstream files at build time, so a new upstream release only needs that script re-checked.

Build: `.github/workflows/build-dll.yml` (GitHub Actions, windows-2022), against RED4ext.SDK master `5246e659`
(patch 2.5 types). The artifact holds the DLL and the two scripts; install it over the official 0.1.9.
