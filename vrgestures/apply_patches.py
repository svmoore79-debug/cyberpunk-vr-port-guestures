"""VRGestures fork: the fork's changes, applied to an upstream checkout before the build.

Kept as exact text replacements instead of edited copies of upstream files, so a new upstream release
only needs this script re-checked (every replacement asserts it matched exactly once) rather than a
merge of 340 KB of source. Line endings are preserved (a Windows checkout may have CRLF).

    python vrgestures/apply_patches.py            # from the repo root
"""
import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

def patch(rel, pairs):
    p = ROOT / rel
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    s = raw.replace("\r\n", "\n")
    for old, new in pairs:
        n = s.count(old)
        if n != 1:
            sys.exit(f"{rel}: expected 1 match, found {n}: {old[:70]!r}")
        s = s.replace(old, new)
    if crlf:
        s = s.replace("\n", "\r\n")
    p.write_bytes(s.encode("utf-8"))
    print(f"patched {rel} ({len(pairs)} change(s))")

# 1. Bone limit 800 -> 1024. A meta-rig over the limit is refused by ReadPlayerBinding, which silently
#    turns off VRIK and the arm-cyberware handling. Measured: bald/arms away 619, physics hair 701,
#    the same hair with Gorilla Arms deployed 849.
patch("include/Anim/VrikState.hpp", [
    ("inline constexpr int VRIK_MAX_BONES = 800;  // was 256; raised so custom rig bones (WeaponRight1 ~767) fit",
     "inline constexpr int VRIK_MAX_BONES = 1024; // was 256, then 800. [VRGestures fork] 1024: hair with physics bones plus\n"
     "                                            // deployed arm cyberware measured 849 bones (bald, arms away: 619)"),
    ("extern int16_t            g_VRBoneParent[800];",
     "extern int16_t            g_VRBoneParent[VRIK_MAX_BONES];"),
])
patch("src/Natives/NativeState.cpp", [
    ("int16_t            g_VRBoneParent[800] = {0};",
     "int16_t            g_VRBoneParent[VRIK_MAX_BONES] = {0};"),
])
patch("src/Natives/VrikArming.cpp", [
    ("for (uint32_t i = 0; i < copyN && i < 800; ++i)",
     "for (uint32_t i = 0; i < copyN && i < static_cast<uint32_t>(VRIK_MAX_BONES); ++i)"),
    ("static int ArmPlayerLocked() {",
     "// [VRGestures fork] a meta-rig over VRIK_MAX_BONES is refused by ReadPlayerBinding, which silently\n"
     "// stops VRIK and the arm-cyberware handling for that rig. Say so in the log, once per size.\n"
     "extern void Log(const char* fmt, ...);\n"
     "static uint32_t VRGForkRigBoneCount(RED4ext::anim::AnimatedObject* object) {\n"
     "    __try { return (object && object->metaRig) ? object->metaRig->boneNames.Size() : 0u; }\n"
     "    __except(EXCEPTION_EXECUTE_HANDLER) { return 0u; }\n"
     "}\n"
     "static void VRGForkWarnRigSize(RED4ext::anim::AnimatedObject* object) {\n"
     "    static uint32_t s_warned = 0;\n"
     "    const uint32_t n = VRGForkRigBoneCount(object);\n"
     "    if (n > static_cast<uint32_t>(VRIK_MAX_BONES) && n != s_warned) {\n"
     "        s_warned = n;\n"
     "        Log(\"VRIK: player meta-rig has %u bones, limit is %d -- body/arm tracking is off for this rig \"\n"
     "            \"(hair or clothing physics bones plus arm cyberware)\\n\", n, VRIK_MAX_BONES);\n"
     "    }\n"
     "}\n"
     "\n"
     "static int ArmPlayerLocked() {"),
    ("    PlayerBinding binding{};\n    if(!ReadPlayerBinding(animObj,binding))return -1;",
     "    PlayerBinding binding{};\n    VRGForkWarnRigSize(animObj);\n    if(!ReadPlayerBinding(animObj,binding))return -1;"),
])
patch("src/Anim/CharacterRig.cpp", [
    ("    float neutralPos[VRIK_MAX_BONES][3]{},neutralRot[VRIK_MAX_BONES][4]{};",
     "    // [VRGestures fork] static: at VRIK_MAX_BONES=1024 these are ~28 KB, too much for the stack. Rig binding is serialised.\n"
     "    static float neutralPos[VRIK_MAX_BONES][3],neutralRot[VRIK_MAX_BONES][4];\n"
     "    std::memset(neutralPos,0,sizeof(neutralPos));std::memset(neutralRot,0,sizeof(neutralRot));"),
])

# 2. Projectile launcher fires on trigger RELEASE (press = aim), only when the VRGestures mod's TweakXL flat
#    VRGestures.launcherFireOnRelease is true. Without VRGestures this is upstream behaviour.
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_cyberware.reds", [
    ("    return scriptInterface.IsActionJustPressed(n\"RangedAttack\") || scriptInterface.IsActionJustReleased(n\"UseCombatGadget\");\n"
     "  }\n"
     "}\n"
     "\n"
     "public class VrLauncherReadyEvents",
     "    // [VRGestures patch] fire on trigger RELEASE: the press only arms the shot (aim while holding).\n"
     "    // Off unless the VRGestures.launcherFireOnRelease flat (r6/tweaks/VRGestures) is true.\n"
     "    if TweakDBInterface.GetBool(t\"VRGestures.launcherFireOnRelease\", false) {\n"
     "      if scriptInterface.IsActionJustPressed(n\"RangedAttack\") { (scriptInterface.executionOwner as PlayerPuppet).vrgPortFireArmed = true; return false; };\n"
     "      if (scriptInterface.executionOwner as PlayerPuppet).vrgPortFireArmed && scriptInterface.IsActionJustReleased(n\"RangedAttack\") {\n"
     "        (scriptInterface.executionOwner as PlayerPuppet).vrgPortFireArmed = false;\n"
     "        return true;\n"
     "      };\n"
     "      return scriptInterface.IsActionJustReleased(n\"UseCombatGadget\");\n"
     "    };\n"
     "    return scriptInterface.IsActionJustPressed(n\"RangedAttack\") || scriptInterface.IsActionJustReleased(n\"UseCombatGadget\");\n"
     "  }\n"
     "}\n"
     "\n"
     "// [VRGestures patch]\n"
     "@addField(PlayerPuppet) public let vrgPortFireArmed: Bool;\n"
     "\n"
     "public class VrLauncherReadyEvents"),
])

# 3. The two-hand carry never hands fists/melee (class 5) to the left hand.
patch("mods/cet/CyberpunkVRPort_Weapon/init.lua", [
    ("        if VRP_lastClass == 1 then return end\n",
     "        if VRP_lastClass == 1 or VRP_lastClass == 5 then return end   -- [VRGestures fork] fists/melee (class 5) are never handed to the left hand\n"),
])
# 4. Upstream 0.1.9's CMakeLists adds tools/rtti_dump, a patch-day tool that was never committed, so a clean
#    checkout fails to configure. Add it only when the folder is there; the plugin does not need it.
patch("CMakeLists.txt", [
    ("add_subdirectory(tools/rtti_dump)",
     "if(EXISTS \"${CMAKE_CURRENT_SOURCE_DIR}/tools/rtti_dump/CMakeLists.txt\")  # [VRGestures fork] not in the published tree\n"
     "    add_subdirectory(tools/rtti_dump)\n"
     "endif()"),
])
print("all VRGestures fork patches applied")
