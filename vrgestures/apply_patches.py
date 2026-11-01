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
    # 0.2.0: redscript's compiler (scc_lib.dll) is built with cargo, and configure fails without Rust. The release
    # zip already ships the same scc_lib.dll beside the plugin, so without cargo it is simply not built or copied.
    ("find_program(CVR_CARGO cargo HINTS \"$ENV{USERPROFILE}/.cargo/bin\" REQUIRED)\n",
     "find_program(CVR_CARGO cargo HINTS \"$ENV{USERPROFILE}/.cargo/bin\")   # [VRGestures fork] optional\n"
     "if(CVR_CARGO)\n"),
    ("add_custom_target(cvr_scc_lib ALL DEPENDS ${CVR_SCC_LIB})\n",
     "add_custom_target(cvr_scc_lib ALL DEPENDS ${CVR_SCC_LIB})\n"
     "else()\n"
     "  message(STATUS \"[VRGestures fork] no cargo: scc_lib.dll is not built (use the release zip's)\")\n"
     "endif()\n"),
    ("add_dependencies(cyberpunkvrport_stereo cvr_scc_lib)\n"
     "add_custom_command(TARGET cyberpunkvrport_stereo POST_BUILD\n"
     "    COMMAND ${CMAKE_COMMAND} -E make_directory \"$<TARGET_FILE_DIR:cyberpunkvrport_stereo>/redscript\"\n"
     "    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${CVR_SCC_LIB} \"$<TARGET_FILE_DIR:cyberpunkvrport_stereo>/redscript/scc_lib.dll\"\n",
     "if(CVR_CARGO)   # [VRGestures fork] the compiler only when cargo built it\n"
     "add_dependencies(cyberpunkvrport_stereo cvr_scc_lib)\n"
     "add_custom_command(TARGET cyberpunkvrport_stereo POST_BUILD\n"
     "    COMMAND ${CMAKE_COMMAND} -E copy_if_different ${CVR_SCC_LIB} \"$<TARGET_FILE_DIR:cyberpunkvrport_stereo>/redscript/scc_lib.dll\")\n"
     "endif()\n"
     "add_custom_command(TARGET cyberpunkvrport_stereo POST_BUILD\n"
     "    COMMAND ${CMAKE_COMMAND} -E make_directory \"$<TARGET_FILE_DIR:cyberpunkvrport_stereo>/redscript\"\n"),
])
#    0.2.0: MSVC 14.44 (VS 2022 17.14) crashes in code generation on the Lua host's VKBindings.cpp (CET's hotkeys;
#    access violation, every time, alone or in a batch). That one file is built unoptimised; it only runs on key presses.
patch("src/Lua/CMakeLists.txt", [
    ("target_precompile_headers(cvr_lua PRIVATE \"${CMAKE_CURRENT_SOURCE_DIR}/cet/stdafx.h\")\n",
     "target_precompile_headers(cvr_lua PRIVATE \"${CMAKE_CURRENT_SOURCE_DIR}/cet/stdafx.h\")\n"
     "# [VRGestures fork] MSVC 14.44's optimiser crashes on this file\n"
     "set_source_files_properties(\"${CMAKE_CURRENT_SOURCE_DIR}/cet/VKBindings.cpp\" PROPERTIES COMPILE_OPTIONS \"/Od\")\n"),
])
# 5. The left-trigger block (SetVRLeftTriggerBlock) also holds the left trigger off the guns. Upstream it only
#    zeroes the game's LT (aim); dual wielding turns the raw left trigger into the fire action, and the launcher
#    into RT, so a blocked trigger still fired. VRGestures blocks it while the left palm is at the ear, where the
#    left trigger is the Sandevistan gesture.
patch("src/Hooks/XInput.cpp", [
    ("    BYTE lt = FloatToBYTE(vr.leftTrigger);",
     "    // [VRGestures fork] a blocked left trigger is held off the dual-wield fire and the launcher below too\n"
     "    BYTE lt = GetTickCount64() < CyberpunkVR_LeftTriggerBlockUntil ? 0 : FloatToBYTE(vr.leftTrigger);"),
    ("        pState->Gamepad.bRightTrigger=FloatToBYTE(vr.leftTrigger);",
     "        pState->Gamepad.bRightTrigger=lt;   // [VRGestures fork] lt: honours the left-trigger block"),
])

# 6. THE LASER under ENGINE STEREO, and a second one for the projectile launcher.
#    0.1.9's engine stereo renders both eyes side by side in one backbuffer with MAIN at the head centre. The red
#    barrel dot was still projected once across the whole width (it landed in the middle of the frame: the left
#    eye's right edge) and handed to a second eye through VRCAM, which this mode never renders. It is now a beam
#    from the muzzle to where the barrel line hits, with the dot at the hit, projected from each eye through that
#    eye's own window into its half -- one line both eyes see, so they fuse it with depth. SetVRAuxLaser(muzzle,
#    hit) draws a second, cyan one (VRGestures: the launcher), not tied to a gun being equipped; the camera frame
#    is published without a barrel so it works with empty hands. The weapon module's barrel raycast also takes
#    the Dynamic group (NPCs, props), so the beam stops on an enemy instead of passing through to the wall.
LASER_CODE = """// [VRGestures fork] ENGINE STEREO (Stereo/EngineStereo.hpp): the backbuffer is BOTH eyes side by side, MAIN
// sits at the head centre and the engine places the eyes +-sep/2 along the camera's right. A point projected
// once across the whole width lands in the middle of the frame -- the left eye's right edge -- and the old
// second-eye hand-off went through VRCAM, which this mode never renders. So the laser is projected from each
// eye, through that eye's own window (the world markers' EngineEyeWindow), into its own half.
static bool EngineStereoActiveForDots() {
    return cvr::engine_stereo::Enabled() && !cvr::engine_stereo::OnePicture();
}

// The window an eye renders with, in tangent units and ADS-zoomed: NDC = x / (forward * half) + shift.
struct EngineEyeView { float shiftX = 0.0f, shiftY = 0.0f, halfX = 0.0f, halfY = 0.0f; };
static bool EngineEyeViewOf(int eye, const ImVec2& display, EngineEyeView* v) {
    if (display.x <= 2.0f || display.y <= 1.0f) return false;
    cvr::projection::ViewWindow centre{};
    if (cvr::projection::ViewWindowOf(0, &centre)) {
        v->shiftX = centre.shiftX; v->shiftY = centre.shiftY; v->halfX = centre.halfX; v->halfY = centre.halfY;
        cvr::engine_stereo::EyeProjection own{};
        if (cvr::engine_stereo::EyeWindow(eye, &own)) { v->shiftX = own.shiftX; v->shiftY = own.shiftY; v->halfX = own.aspect * centre.halfY; }
    } else {
        // the engine's centred frustum: the horizontal fov over one eye's half, the vertical from its aspect
        float hfov = GetGameRenderFovDeg();
        if (hfov <= 1.0f) hfov = OpenXRManager::Get().GetRuntimeHorizontalFovDeg();
        if (hfov <= 1.0f) hfov = 100.0f;
        v->shiftX = v->shiftY = 0.0f;
        v->halfX = tanf(hfov * 0.5f * (3.1415926535f / 180.0f));
        v->halfY = v->halfX * (display.y / (display.x * 0.5f));
    }
    const float ads = CyberpunkVR_MainAdsZoomFactor;
    if (std::isfinite(ads) && ads > 0.05f) { v->halfX /= ads; v->halfY /= ads; }
    return v->halfX > 0.0001f && v->halfY > 0.0001f;
}

// A world point in one eye's camera axes (X right, Y forward, Z up). Eye 0 is the left.
static void EngineEyeLocal(int eye, const float p[3], const float cam[3], const float q[4], float l[3]) {
    const float rgt[3] = {
        1.0f - 2.0f * (q[1] * q[1] + q[2] * q[2]),
        2.0f * (q[0] * q[1] + q[2] * q[3]),
        2.0f * (q[0] * q[2] - q[1] * q[3])
    };
    const float sep = cvr::engine_stereo::EyeSeparation();
    const float half = ((sep > 0.001f && sep < 0.2f) ? 0.5f * sep : 0.0325f) * (eye ? +1.0f : -1.0f);
    RotateVectorByQuaternion(p[0] - (cam[0] + rgt[0] * half), p[1] - (cam[1] + rgt[1] * half),
                             p[2] - (cam[2] + rgt[2] * half), -q[0], -q[1], -q[2], q[3], &l[0], &l[1], &l[2]);
}

static ImVec2 EngineEyeScreen(int eye, const float l[3], const EngineEyeView& v, const ImVec2& display) {
    const float eyeW = display.x * 0.5f;
    const float ndcX = l[0] / (l[1] * v.halfX) + v.shiftX;
    const float ndcY = l[2] / (l[1] * v.halfY) + v.shiftY;
    return ImVec2(float(eye) * eyeW + (ndcX * 0.5f + 0.5f) * eyeW, (-ndcY * 0.5f + 0.5f) * display.y);
}

// THE LASER: a beam from the muzzle `a` to where it hits `b`, the dot at the hit, in each eye's half by that eye's
// own projection -- a line both eyes see, which they fuse into one beam with depth, rather than two dots they
// have to agree on. It ends AT the hit, the first surface the ray met, so nothing lies in front of its end for it
// to pass through. Cut at the near plane and clipped to the eye's half, so a muzzle close to the face cannot throw
// the line into the other eye.
// 0.2.0: the dot alone by default -- the port draws the weapon hand's gun as a dot in both eyes itself now, and the
// second dot (the left gun, the launcher) matches it.
extern "C" __declspec(dllexport) int32_t CyberpunkVR_LaserBeam = 0;   // 1 = the beam too
static void DrawEngineStereoLaser(const float a[3], const float b[3], const float cam[3], const float q[4],
                                  ImU32 colour, float rad) {
    const ImVec2 display = ImGui::GetIO().DisplaySize;
    ImDrawList* dl = ImGui::GetBackgroundDrawList();
    if (!dl) return;
    const float eyeW = display.x * 0.5f;
    const float nearY = 0.05f;
    for (int eye = 0; eye < 2; ++eye) {
        EngineEyeView v{};
        if (!EngineEyeViewOf(eye, display, &v)) continue;
        float la[3], lb[3];
        EngineEyeLocal(eye, a, cam, q, la);
        EngineEyeLocal(eye, b, cam, q, lb);
        if (lb[1] <= nearY) continue;   // the hit is behind this eye: nothing to mark
        if (la[1] < nearY) {
            const float t = (nearY - la[1]) / (lb[1] - la[1]);
            for (int i = 0; i < 3; ++i) la[i] += (lb[i] - la[i]) * t;
        }
        const ImVec2 sa = EngineEyeScreen(eye, la, v, display);
        const ImVec2 sb = EngineEyeScreen(eye, lb, v, display);
        dl->PushClipRect(ImVec2(float(eye) * eyeW, 0.0f), ImVec2(float(eye + 1) * eyeW, display.y), false);
        if (CyberpunkVR_LaserBeam) dl->AddLine(sa, sb, (colour & 0x00FFFFFFu) | (150u << 24), 2.0f);
        dl->AddCircleFilled(sb, rad, colour);
        dl->PopClipRect();
    }
}

// THE AUX LASER (SetVRAuxLaser): muzzle and hit of a second beam, in its own colour -- the projectile launcher's,
// fed by VRGestures. Independent of the gun's, so a gun in the other hand keeps its own; gone 150 ms after the
// caller stops. In the port's own stereo (MAIN + VRCAM) only its dot is drawn, and in MAIN's eye only: the
// second-eye hand-off below carries the gun's dot.
extern "C" __declspec(dllexport) float CyberpunkVR_AuxLaser[6] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
extern "C" __declspec(dllexport) volatile uint64_t CyberpunkVR_AuxLaserTick = 0;

static void DrawAuxLaser() {
    const uint64_t tick = CyberpunkVR_AuxLaserTick;
    if (!tick || GetTickCount64() - tick > 150) return;
    cvr::camera::BarrelFrame bf{};
    if (!cvr::camera::BarrelFrameRead(&bf)) return;
    const float cam[3] = {
        static_cast<float>(g_lastLocatePosFP[0]) / 131072.0f,
        static_cast<float>(g_lastLocatePosFP[1]) / 131072.0f,
        static_cast<float>(g_lastLocatePosFP[2]) / 131072.0f
    };
    if (cam[0] * cam[0] + cam[1] * cam[1] + cam[2] * cam[2] <= 1.0f) return;
    const float a[3] = { CyberpunkVR_AuxLaser[0], CyberpunkVR_AuxLaser[1], CyberpunkVR_AuxLaser[2] };
    const float b[3] = { CyberpunkVR_AuxLaser[3], CyberpunkVR_AuxLaser[4], CyberpunkVR_AuxLaser[5] };
    const ImU32 colour = IM_COL32(60, 200, 255, 255);
    if (EngineStereoActiveForDots()) { DrawEngineStereoLaser(a, b, cam, bf.camQuat, colour, 3.0f); return; }
    ImDrawList* dl = ImGui::GetBackgroundDrawList();
    if (!dl) return;
    const float* q = bf.camQuat;
    const float rgt[3] = {
        1.0f - 2.0f * (q[1] * q[1] + q[2] * q[2]),
        2.0f * (q[0] * q[1] + q[2] * q[3]),
        2.0f * (q[0] * q[2] - q[1] * q[3])
    };
    float halfIpd = CyberpunkVRPort_HalfIpd();
    if (!(halfIpd > 0.0001f)) halfIpd = 0.0325f;
    const float s = (CyberpunkVR_BarrelDotEyeSign >= 0) ? +1.0f : -1.0f;   // MAIN's side, as the barrel dot
    float lx = 0.0f, ly = 0.0f, lz = 0.0f;
    RotateVectorByQuaternion(b[0] - (cam[0] + rgt[0] * halfIpd * s), b[1] - (cam[1] + rgt[1] * halfIpd * s),
                             b[2] - (cam[2] + rgt[2] * halfIpd * s), -q[0], -q[1], -q[2], q[3], &lx, &ly, &lz);
    ImVec2 sc{};
    if (ProjectHeadSpacePointToScreen(lx, lz, -ly, ImGui::GetIO().DisplaySize, &sc)) dl->AddCircleFilled(sc, 3.0f, colour);
}

void DrawBarrelCrosshair() {
    DrawAuxLaser();   // [VRGestures fork] its own gates: it is not the gun's laser
    // Invalidate the second-eye/mirror publication before any early return.
"""
patch("src/Overlay/OverlayDebugDraw.cpp", [
    ('#include "Hooks/SightLine.hpp"\n',
     '#include "Hooks/SightLine.hpp"\n'
     '#include "Runtimes/AsymmetricProjection.hpp"   // [VRGestures fork] the eye windows, for the laser\n'
     '#include "Stereo/EngineStereo.hpp"             // [VRGestures fork]\n'
     'extern volatile float    g_provAimHit[3];        // [VRGestures fork] the barrel raycast (SetVRAimHit)\n'
     'extern volatile uint64_t g_provAimHitStampMs;\n'),
    ("void DrawBarrelCrosshair() {\n    // Invalidate the second-eye/mirror publication before any early return.\n",
     LASER_CODE),
    # 0.2.0: the gun's own dot is upstream's (both eyes); only the second dot is drawn here
])
patch("src/Hooks/FinalCamera.cpp", [
    ("                if (s_muzzleFwd[0] * s_muzzleFwd[0] +\n"
     "                    s_muzzleFwd[1] * s_muzzleFwd[1] +\n"
     "                    s_muzzleFwd[2] * s_muzzleFwd[2] > 0.25f) {\n",
     "                // [VRGestures fork] published without a barrel as well: the aux laser (SetVRAuxLaser) needs\n"
     "                // only the camera, and DrawBarrelCrosshair already refuses a zero direction.\n"
     "                {\n"),
])
patch("src/Natives/OrientationProvider.cpp", [
    ("    ++g_provAimHitSeq;\n    g_provAimHitStampMs = GetTickCount64();\n}\n",
     "    ++g_provAimHitSeq;\n    g_provAimHitStampMs = GetTickCount64();\n}\n\n"
     "// [VRGestures fork] THE AUX LASER: a draw-only beam, muzzle to hit, in its own colour (Overlay/OverlayDebugDraw.cpp\n"
     "// DrawAuxLaser). VRGestures feeds it the projectile launcher's every frame while the launcher is out; it feeds\n"
     "// nothing else, so the gun's laser and the shot are untouched. A point within 1 m of the origin clears it.\n"
     "extern \"C\" float CyberpunkVR_AuxLaser[6];\n"
     "extern \"C\" volatile uint64_t CyberpunkVR_AuxLaserTick;\n"
     "void SetVRAuxLaser(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t) {\n"
     "    float v[6] = {0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};\n"
     "    for (float& f : v) RED4ext::GetParameter(aFrame, &f);\n"
     "    aFrame->code++;\n"
     "    if (!(v[3]*v[3] + v[4]*v[4] + v[5]*v[5] >= 1.0f) || !(v[0]*v[0] + v[1]*v[1] + v[2]*v[2] >= 1.0f)) {\n"
     "        CyberpunkVR_AuxLaserTick = 0; return;\n"
     "    }\n"
     "    for (int i = 0; i < 6; ++i) CyberpunkVR_AuxLaser[i] = v[i];\n"
     "    CyberpunkVR_AuxLaserTick = GetTickCount64();\n"
     "}\n"),
])
patch("include/Natives/NativeFunctions.hpp", [
    ("void SetVRAimHit(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);\n",
     "void SetVRAimHit(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);\n"
     "void SetVRAuxLaser(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork]\n"),
])
patch("src/Natives/Registration.cpp", [
    ("    rtti->RegisterFunction(fAimHit);\n",
     "    rtti->RegisterFunction(fAimHit);\n\n"
     "    // [VRGestures fork] the aux laser (the launcher's, from VRGestures): muzzle, then hit\n"
     "    auto fAuxLaser = RED4ext::CGlobalFunction::Create(\"SetVRAuxLaser\", \"SetVRAuxLaser\", &SetVRAuxLaser);\n"
     "    fAuxLaser->flags = flags;\n"
     "    fAuxLaser->AddParam(\"Float\", \"mx\"); fAuxLaser->AddParam(\"Float\", \"my\"); fAuxLaser->AddParam(\"Float\", \"mz\");\n"
     "    fAuxLaser->AddParam(\"Float\", \"hx\"); fAuxLaser->AddParam(\"Float\", \"hy\"); fAuxLaser->AddParam(\"Float\", \"hz\");\n"
     "    rtti->RegisterFunction(fAuxLaser);\n"),
])
patch("mods/cet/CyberpunkVRPort_Weapon/init.lua", [
    ("local staticGroup = nil\n",
     "local staticGroup = nil\n"
     "local dynamicGroup = nil   -- [VRGestures fork] the barrel raycast's second group\n"),
    ("    local ok, res = sq:SyncRaycastByCollisionGroup(o, far, staticGroup, false, false)\n",
     "    local ok, res = sq:SyncRaycastByCollisionGroup(o, far, staticGroup, false, false)\n"
     "    -- [VRGestures fork] and the Dynamic group (NPCs, props), so the laser stops on an enemy rather than passing\n"
     "    -- through to the wall: the nearer hit wins. Started 30 cm down the barrel, clear of the gun and the hands.\n"
     "    dynamicGroup = dynamicGroup or CName.new(\"Dynamic\")\n"
     "    local o2 = Vector4.new(x + f.x * 0.30, y + f.y * 0.30, z + f.z * 0.30, 1)\n"
     "    local okD, resD = sq:SyncRaycastByCollisionGroup(o2, far, dynamicGroup, false, false)\n"
     "    if okD and resD and resD.position then\n"
     "        local function d2(p) return (p.x - x)^2 + (p.y - y)^2 + (p.z - z)^2 end\n"
     "        if not (ok and res and res.position) or d2(resD.position) < d2(res.position) then ok, res = okD, resD end\n"
     "    end\n"),
])

# 8. LEFT-GUN SHOTS ON THE PROJECTILE PATH. With a mod that turns bullets into projectiles every player shot comes
#    through the orientation provider's launch slot and the position provider (measured: 20 of 20 dual-wield shots,
#    none through the hitscan hook), and both only knew the RIGHT barrel, so a left-gun round flew down the right
#    gun's line. Upstream's left-gun handling (WaLeftGunFired) lives on the hitscan path only. A shot taken with the
#    LEFT trigger alone, two guns in hand, now starts at the left muzzle and leaves along the left barrel (a shotgun's
#    cone centred on it), kicks the left hand, and skips the sight line (that is the right gun's). Both triggers at
#    once stay on the right barrel for now.
patch("src/Natives/OrientationProvider.cpp", [
    ("static uintptr_t __fastcall PosProvStub33(",
     "// [VRGestures fork] WHICH GUN, ON THE PROJECTILE PATH. Two guns in hand (kDualWieldActive, set by the input merge\n"
     "// from the reload mod's report) and the left barrel published (SetVRLeftMuzzle): a shot taken with the left\n"
     "// trigger alone is the left gun's -- the port routes each trigger to its own gun (vrport_dual_wield.reds), the\n"
     "// same fallback the hitscan hook uses when the shot's record cannot tell the guns apart. Both triggers held:\n"
     "// the right gun, as before. Out: the left muzzle and the left barrel's unit forward.\n"
     "extern \"C\" void RecoilOnShotLeft();\n"
     "static uint32_t s_vrgDeltaSide = 0;   // which gun the cached cone delta (g_provDeltaQ) belongs to: 1 = left\n"
     "static bool VrgLeftGunShot(float pos[3], float fwd[3]) {\n"
     "    if (!g_pSharedHands) return false;\n"
     "    if (g_pSharedHands[vrshared::kDualWieldActive] < 0.5f || g_pSharedHands[vrshared::kLeftMuzzleValid] < 0.5f)\n"
     "        return false;\n"
     "    const bool lt = g_pSharedHands[vrshared::kLeftTriggerAnalog] > 0.2f;\n"
     "    const bool rt = g_pSharedHands[vrshared::kRightTriggerAnalog] > 0.2f;\n"
     "    if (!lt || rt) return false;\n"
     "    const float* p = &g_pSharedHands[vrshared::kLeftMuzzlePos];\n"
     "    const float* f = &g_pSharedHands[vrshared::kLeftMuzzleFwd];\n"
     "    const float l2 = f[0]*f[0] + f[1]*f[1] + f[2]*f[2];\n"
     "    const float p2 = p[0]*p[0] + p[1]*p[1] + p[2]*p[2];\n"
     "    if (!(l2 > 0.25f) || !std::isfinite(p2) || !(p2 > 1.0f)) return false;\n"
     "    const float inv = 1.0f / std::sqrt(l2);\n"
     "    pos[0] = p[0]; pos[1] = p[1]; pos[2] = p[2];\n"
     "    fwd[0] = f[0] * inv; fwd[1] = f[1] * inv; fwd[2] = f[2] * inv;\n"
     "    return true;\n"
     "}\n\n"
     "static uintptr_t __fastcall PosProvStub33("),
    ("    if (cvr::sight::SightLineOffset(forward, lift)) {\n        p[0] += lift[0]; p[1] += lift[1]; p[2] += lift[2];\n    }\n",
     "    if (cvr::sight::SightLineOffset(forward, lift)) {\n        p[0] += lift[0]; p[1] += lift[1]; p[2] += lift[2];\n    }\n"
     "    // [VRGestures fork] a left-gun shot starts at the LEFT muzzle (no sight line: that is the right gun's)\n"
     "    float vrgLeftFwd[3];\n"
     "    (void)VrgLeftGunShot(p, vrgLeftFwd);\n"),
    ("                    if (S == 30 && ProvIsPlayersAttack(C, rcx)) {\n",
     "                    if (S == 30 && ProvIsPlayersAttack(C, rcx)) {\n"
     "                        float vrgShotPos[3], vrgShotFwd[3];   // [VRGestures fork] which gun fired: that hand kicks\n"
     "                        const bool vrgLeftShot = VrgLeftGunShot(vrgShotPos, vrgShotFwd);\n"),
    ("                            RecoilOnShot();\n",
     "                            if (vrgLeftShot) RecoilOnShotLeft(); else RecoilOnShot();   // [VRGestures fork] the gun that fired\n"),
    ("                        float mq[4]={g_provMuzzleQ[0],g_provMuzzleQ[1],g_provMuzzleQ[2],g_provMuzzleQ[3]};\n"
     "                        if (mq[0]*mq[0]+mq[1]*mq[1]+mq[2]*mq[2]+mq[3]*mq[3] > 0.5f) {\n"
     "                            if (g_provDeltaSeq != g_provMuzzleSeq) {   // recompute once per frame (first pellet)\n",
     "                        float mq[4]={g_provMuzzleQ[0],g_provMuzzleQ[1],g_provMuzzleQ[2],g_provMuzzleQ[3]};\n"
     "                        // [VRGestures fork] a left-gun shot: the cone is centred on the LEFT barrel instead, and the\n"
     "                        // cached delta is recomputed whenever the gun changes, not only once per frame.\n"
     "                        float vrgLeftPos[3], vrgLeftFwd[3];\n"
     "                        const bool vrgLeft = sharedOn && VrgLeftGunShot(vrgLeftPos, vrgLeftFwd);\n"
     "                        if (vrgLeft) BuildOrientFromFwd(vrgLeftFwd[0], vrgLeftFwd[1], vrgLeftFwd[2], 1, mq);\n"
     "                        if (mq[0]*mq[0]+mq[1]*mq[1]+mq[2]*mq[2]+mq[3]*mq[3] > 0.5f) {\n"
     "                            if (g_provDeltaSeq != g_provMuzzleSeq || s_vrgDeltaSide != (vrgLeft ? 1u : 0u)) {   // recompute once per frame (first pellet)\n"),
    ("                                g_provDeltaSeq = g_provMuzzleSeq;\n",
     "                                g_provDeltaSeq = g_provMuzzleSeq;\n"
     "                                s_vrgDeltaSide = vrgLeft ? 1u : 0u;   // [VRGestures fork]\n"),
])

# 9. THE LASER SIGHT SWITCH IS SAVED, AND SCRIPTS CAN READ IT. "Weapon Aim laser dot" was a bare checkbox outside
#    the live controls: off at every launch, never written to vrport.ini. It is now xr_laser_sight in vrport.ini
#    (read with the rest of the file, written with every save, saved when it is ticked), and GetVRLaserSight()
#    returns it, so VRGestures shows the left gun's laser only when it is on (the launcher's stays always on).
# 0.2.0: upstream saves the switch itself (xr_weapon_laser_dot), so only the script read is kept.
patch("src/Natives/OrientationProvider.cpp", [
    ("    for (int i = 0; i < 6; ++i) CyberpunkVR_AuxLaser[i] = v[i];\n"
     "    CyberpunkVR_AuxLaserTick = GetTickCount64();\n"
     "}\n",
     "    for (int i = 0; i < 6; ++i) CyberpunkVR_AuxLaser[i] = v[i];\n"
     "    CyberpunkVR_AuxLaserTick = GetTickCount64();\n"
     "}\n\n"
     "// [VRGestures fork] THE LASER SIGHT SWITCH (\"Weapon Aim laser dot\", vrport.ini xr_laser_sight), for scripts: VRGestures\n"
     "// shows the left gun's laser only while it is on.\n"
     "namespace overlay { extern bool g_drawBarrelCross; }\n"
     "void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n"
     "    aFrame->code++;\n"
     "    if (aOut) *aOut = overlay::g_drawBarrelCross;\n"
     "}\n"),
])
patch("include/Natives/NativeFunctions.hpp", [
    ("void SetVRAuxLaser(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork]\n",
     "void SetVRAuxLaser(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork]\n"
     "void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t);   // [VRGestures fork]\n"),
])
patch("src/Natives/Registration.cpp", [
    ("    rtti->RegisterFunction(fAuxLaser);\n",
     "    rtti->RegisterFunction(fAuxLaser);\n"
     "    // [VRGestures fork] the laser sight switch, for scripts\n"
     "    auto fLaserSight = RED4ext::CGlobalFunction::Create(\"GetVRLaserSight\", \"GetVRLaserSight\", &GetVRLaserSight);\n"
     "    fLaserSight->flags = flags; fLaserSight->SetReturnType(\"Bool\"); rtti->RegisterFunction(fLaserSight);\n"),
])

# 10. BOTH TRIGGERS: EACH GUN'S PROJECTILE LEAVES ITS OWN BARREL. Measured (with logging since removed): both triggers
#     squeezed, the two guns' projectiles carry two different attack objects, the same two every shot, and those
#     differ in exactly one of the four handles the player test reads (attack+0xD8) -- the weapon -- while the game's
#     own spawn point is the same for both (0.73 m from either muzzle) and tells nothing. So a single-trigger shot,
#     whose gun is certain, teaches which handle is which gun, and with both triggers (or neither: a shot fired on the
#     release) the handle decides. Not learned yet: the right gun, as before.
patch("src/Natives/OrientationProvider.cpp", [
    ("static bool VrgLeftGunShot(float pos[3], float fwd[3]) {\n",
     "// [VRGestures fork] THE WEAPON A PROJECTILE CAME FROM: the fourth handle of its attack record (attack+0xD8). With\n"
     "// both triggers squeezed each gun's shots carry their own attack object, and the two differ in exactly this handle\n"
     "// (the other three, the player among them, are the same). 0 when it cannot be read.\n"
     "static uintptr_t VrgAttackWeapon(uintptr_t provider, int srcOffset) {\n"
     "    if (!ProvPlausiblePtr(provider)) return 0;\n"
     "    uintptr_t w = 0;\n"
     "    __try {\n"
     "        const uintptr_t src = *reinterpret_cast<uintptr_t*>(provider + srcOffset);\n"
     "        if (!ProvPlausiblePtr(src)) return 0;\n"
     "        const uintptr_t atk = *reinterpret_cast<uintptr_t*>(src + 0x10);\n"
     "        if (!ProvPlausiblePtr(atk)) return 0;\n"
     "        w = reinterpret_cast<const uintptr_t*>(atk)[0xD8 / 8];\n"
     "    } __except (EXCEPTION_EXECUTE_HANDLER) { return 0; }\n"
     "    return ProvPlausiblePtr(w) ? w : 0;\n"
     "}\n"
     "// Which weapon handle is which gun, learned from shots fired with one trigger alone.\n"
     "static volatile uintptr_t s_vrgLeftWeapon = 0, s_vrgRightWeapon = 0;\n\n"
     "static bool VrgLeftGunShot(float pos[3], float fwd[3], uintptr_t weapon = 0) {\n"),
    ("    if (!lt || rt) return false;\n",
     "    // One trigger: the gun is certain, and the shot teaches which weapon handle it is. Both (or neither: a shot\n"
     "    // fired on the release): the handle decides once learned; otherwise the right gun, as before.\n"
     "    bool left = false;\n"
     "    if (lt != rt) {\n"
     "        left = lt;\n"
     "        if (weapon) { if (left) s_vrgLeftWeapon = weapon; else s_vrgRightWeapon = weapon; }\n"
     "    } else {\n"
     "        left = weapon && weapon == s_vrgLeftWeapon && weapon != s_vrgRightWeapon;\n"
     "    }\n"
     "    if (!left) return false;\n"),
    ("    (void)VrgLeftGunShot(p, vrgLeftFwd);\n",
     "    (void)VrgLeftGunShot(p, vrgLeftFwd, VrgAttackWeapon(rcx, 0x88));\n"),
    ("                        const bool vrgLeftShot = VrgLeftGunShot(vrgShotPos, vrgShotFwd);\n",
     "                        const bool vrgLeftShot = VrgLeftGunShot(vrgShotPos, vrgShotFwd, C == 2 ? VrgAttackWeapon(rcx, 0x78) : 0);\n"),
    ("                        const bool vrgLeft = sharedOn && VrgLeftGunShot(vrgLeftPos, vrgLeftFwd);\n",
     "                        const bool vrgLeft = sharedOn && VrgLeftGunShot(vrgLeftPos, vrgLeftFwd, C == 2 ? VrgAttackWeapon(rcx, 0x78) : 0);\n"),
])

# 11. THE LAUNCHER AIMS WITH THE HAND. Its shot left along two bones of the animated arm (VRCyberwarePoint 0 -> 1),
#     which sway with the arm animation and the body solve, so the shot and its laser waggled. The controller's own
#     AIM pose -- the runtime's pointing ray, along the index finger -- is raw tracking with none of that. It is now
#     kept head-relative beside the grip pose every frame, and VRHandAimRay(side) returns it as a game-world ray
#     (origin, direction) through the game camera, which under engine stereo sits at the head centre. The launcher
#     still SPAWNS at the barrel; it flies along the hand's ray. VRGestures draws its laser the same way.
patch("include/Runtimes/OpenXRManager.hpp", [
    ("    bool GetHandPose(int handIndex, OpenXRHeadPose* out) const;\n",
     "    bool GetHandPose(int handIndex, OpenXRHeadPose* out) const;\n"
     "    // [VRGestures fork] the controller's AIM pose (the pointing ray), head-relative like GetHandPose's grip pose\n"
     "    bool GetHandAimPose(int handIndex, OpenXRHeadPose* out) const;\n"),
    ("    OpenXRHeadPose m_hands[2]{};\n",
     "    OpenXRHeadPose m_hands[2]{};\n"
     "    OpenXRHeadPose m_handAim[2]{};   // [VRGestures fork] the aim pose, head-relative, under m_handMutex\n"),
])
patch("src/Runtimes/OpenXRManager.cpp", [
    ("bool OpenXRManager::GetHandPose(int handIndex, OpenXRHeadPose* out) const {\n",
     "bool OpenXRManager::GetHandAimPose(int handIndex, OpenXRHeadPose* out) const {   // [VRGestures fork]\n"
     "    if (!out || handIndex < 0 || handIndex > 1) return false;\n"
     "    std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(m_handMutex));\n"
     "    *out = m_handAim[handIndex];\n"
     "    return out->valid;\n"
     "}\n\n"
     "bool OpenXRManager::GetHandPose(int handIndex, OpenXRHeadPose* out) const {\n"),
])
patch("src/Runtimes/OpenXRFrameLoop.cpp", [
    ("                    m_hands[i].valid = false;\n",
     "                    m_hands[i].valid = false;\n"
     "                    m_handAim[i].valid = false;   // [VRGestures fork]\n"),
    ("                        if (XR_SUCCEEDED(xrLocateSpace(m_handAimSpaces[i], m_localSpace, handLocateTime, &aimLoc)) &&\n"
     "                            (aimLoc.locationFlags & XR_SPACE_LOCATION_ORIENTATION_VALID_BIT)) {\n",
     "                        if (XR_SUCCEEDED(xrLocateSpace(m_handAimSpaces[i], m_localSpace, handLocateTime, &aimLoc)) &&\n"
     "                            (aimLoc.locationFlags & XR_SPACE_LOCATION_ORIENTATION_VALID_BIT)) {\n"
     "                            // [VRGestures fork] the whole aim pose, head-relative on the same head as the grip pose\n"
     "                            if (aimLoc.locationFlags & XR_SPACE_LOCATION_POSITION_VALID_BIT) {\n"
     "                                const XrQuaternionf aimHeadInv = ConjugateQuat(headForHands.orientation);\n"
     "                                XrVector3f aimRel{aimLoc.pose.position.x - headForHands.position.x,\n"
     "                                                  aimLoc.pose.position.y - headForHands.position.y,\n"
     "                                                  aimLoc.pose.position.z - headForHands.position.z};\n"
     "                                aimRel = RotateVector(aimHeadInv, aimRel);\n"
     "                                const XrQuaternionf aimOri = MultiplyQuat(aimHeadInv, aimLoc.pose.orientation);\n"
     "                                m_handAim[i].posX = aimRel.x; m_handAim[i].posY = aimRel.y; m_handAim[i].posZ = aimRel.z;\n"
     "                                m_handAim[i].oriX = aimOri.x; m_handAim[i].oriY = aimOri.y;\n"
     "                                m_handAim[i].oriZ = aimOri.z; m_handAim[i].oriW = aimOri.w;\n"
     "                                m_handAim[i].valid = true;\n"
     "                            }\n"),
])
patch("src/Natives/OrientationProvider.cpp", [
    ("void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n",
     "// [VRGestures fork] THE HAND'S AIM RAY in the game world: [0] origin (W 1), [1] unit direction (W 0); empty when\n"
     "// unknown. The controller's aim pose is head-relative in OpenXR axes (X right, Y up, -Z forward); the game camera\n"
     "// is at the head (MAIN at the head centre under engine stereo) in game axes (X right, Y forward, Z up), so the\n"
     "// pose goes through (x, -z, y) and the camera's rotation and position. side: 0 left, 1 right.\n"
     "extern volatile int32_t g_lastLocatePosFP[3];\n"
     "static void VrgRotate(const float q[4], const float v[3], float o[3]) {\n"
     "    const float tx = 2.0f * (q[1] * v[2] - q[2] * v[1]);\n"
     "    const float ty = 2.0f * (q[2] * v[0] - q[0] * v[2]);\n"
     "    const float tz = 2.0f * (q[0] * v[1] - q[1] * v[0]);\n"
     "    o[0] = v[0] + q[3] * tx + (q[1] * tz - q[2] * ty);\n"
     "    o[1] = v[1] + q[3] * ty + (q[2] * tx - q[0] * tz);\n"
     "    o[2] = v[2] + q[3] * tz + (q[0] * ty - q[1] * tx);\n"
     "}\n"
     "void VRHandAimRay(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, RED4ext::DynArray<RED4ext::Vector4>* aOut, int64_t) {\n"
     "    int32_t side = 0;\n"
     "    RED4ext::GetParameter(aFrame, &side);\n"
     "    aFrame->code++;\n"
     "    if (!aOut) return;\n"
     "    aOut->Clear();\n"
     "    OpenXRHeadPose aim{};\n"
     "    if (side < 0 || side > 1 || !OpenXRManager::Get().GetHandAimPose(side, &aim)) return;\n"
     "    cvr::camera::BarrelFrame bf{};\n"
     "    if (!cvr::camera::BarrelFrameRead(&bf)) return;\n"
     "    const float cam[3] = { static_cast<float>(g_lastLocatePosFP[0]) / 131072.0f,\n"
     "                           static_cast<float>(g_lastLocatePosFP[1]) / 131072.0f,\n"
     "                           static_cast<float>(g_lastLocatePosFP[2]) / 131072.0f };\n"
     "    if (!(cam[0] * cam[0] + cam[1] * cam[1] + cam[2] * cam[2] > 1.0f)) return;\n"
     "    const float qa[4] = { aim.oriX, aim.oriY, aim.oriZ, aim.oriW };\n"
     "    const float back[3] = { 0.0f, 0.0f, -1.0f };\n"
     "    float fx[3];\n"
     "    VrgRotate(qa, back, fx);                                           // the aim forward, head frame (OpenXR)\n"
     "    const float pLocal[3] = { aim.posX, -aim.posZ, aim.posY };         // -> camera axes\n"
     "    const float dLocal[3] = { fx[0], -fx[2], fx[1] };\n"
     "    float p[3], d[3];\n"
     "    VrgRotate(bf.camQuat, pLocal, p);\n"
     "    VrgRotate(bf.camQuat, dLocal, d);\n"
     "    const float dl = std::sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);\n"
     "    if (!(dl > 0.5f) || !std::isfinite(dl)) return;\n"
     "    RED4ext::Vector4 o{ cam[0] + p[0], cam[1] + p[1], cam[2] + p[2], 1.0f };\n"
     "    RED4ext::Vector4 v{ d[0] / dl, d[1] / dl, d[2] / dl, 0.0f };\n"
     "    aOut->PushBack(o);\n"
     "    aOut->PushBack(v);\n"
     "}\n\n"
     "void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n"),
    ("#include \"Utils/SharedSlots.hpp\"   // CyberpunkVR_Hands_Shared slot map (single source of truth)\n",
     "#include \"Utils/SharedSlots.hpp\"   // CyberpunkVR_Hands_Shared slot map (single source of truth)\n"
     "#include \"Camera/CameraLink.hpp\"   // [VRGestures fork] cvr::camera::BarrelFrameRead, for VRHandAimRay\n"),
])
patch("include/Natives/NativeFunctions.hpp", [
    ("void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t);   // [VRGestures fork]\n",
     "void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t);   // [VRGestures fork]\n"
     "void VRHandAimRay(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, RED4ext::DynArray<RED4ext::Vector4>* aOut, int64_t);   // [VRGestures fork]\n"),
])
patch("src/Natives/Registration.cpp", [
    ("    fLaserSight->flags = flags; fLaserSight->SetReturnType(\"Bool\"); rtti->RegisterFunction(fLaserSight);\n",
     "    fLaserSight->flags = flags; fLaserSight->SetReturnType(\"Bool\"); rtti->RegisterFunction(fLaserSight);\n"
     "    // [VRGestures fork] the hand's aim ray (origin, direction) in the game world\n"
     "    auto fHandAim = RED4ext::CGlobalFunction::Create(\"VRHandAimRay\", \"VRHandAimRay\", &VRHandAimRay);\n"
     "    fHandAim->flags = flags; fHandAim->AddParam(\"Int32\", \"side\"); fHandAim->SetReturnType(\"array:Vector4\");\n"
     "    rtti->RegisterFunction(fHandAim);\n"),
])
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_launcher_aim.reds", [
    ("public native func VRLauncherControllerAim() -> Bool;\n",
     "public native func VRLauncherControllerAim() -> Bool;\n"
     "// [VRGestures fork] the left (0) / right (1) controller's aim ray in the world: [0] origin, [1] direction\n"
     "public native func VRHandAimRay(side: Int32) -> array<Vector4>;\n"),
    ("  direction = Vector4.Normalize(end - muzzle);\n",
     "  direction = Vector4.Normalize(end - muzzle);\n"
     "  // [VRGestures fork] FLY ALONG THE HAND, NOT THE BONES: the barrel's two bones sway with the arm animation and\n"
     "  // the body solve; the controller's aim ray does not. The shot still spawns at the barrel.\n"
     "  let handRay = VRHandAimRay(0);\n"
     "  if ArraySize(handRay) >= 2 && Vector4.Length(handRay[1]) > 0.50 {\n"
     "    direction = Vector4.Normalize(handRay[1]);\n"
     "  };\n"),
])

# 12. ONE RECOIL LATCH PER HAND. The projectile path kicks once per frame (the muzzle sequence), so a shotgun's pellets
#     are one kick; patch 8 sent a left-gun shot's kick to the left hand through that same latch. With both guns firing
#     in one frame -- two automatic pistols, both triggers -- whichever projectile came first took the frame and the
#     other hand's kick was dropped. The left hand now has its own latch, as on the hitscan path (s_waRecoilSeqSeenLeft).
patch("src/Natives/OrientationProvider.cpp", [
    ("static volatile uintptr_t s_vrgLeftWeapon = 0, s_vrgRightWeapon = 0;\n",
     "static volatile uintptr_t s_vrgLeftWeapon = 0, s_vrgRightWeapon = 0;\n"
     "// The left hand's own once-per-frame recoil latch (the right hand keeps g_provRecoilSeqSeen): with both guns firing in\n"
     "// one frame, each hand kicks once.\n"
     "static volatile LONG s_vrgRecoilSeqSeenLeft = -1;\n"),
    ("                        const LONG recoilSeen = g_provRecoilSeqSeen;\n"
     "                        if (recoilSeen != recoilSeq &&\n"
     "                            InterlockedCompareExchange(&g_provRecoilSeqSeen, recoilSeq, recoilSeen) == recoilSeen) {\n",
     "                        volatile LONG* const recoilLatch = vrgLeftShot ? &s_vrgRecoilSeqSeenLeft : &g_provRecoilSeqSeen;   // [VRGestures fork]\n"
     "                        const LONG recoilSeen = *recoilLatch;\n"
     "                        if (recoilSeen != recoilSeq &&\n"
     "                            InterlockedCompareExchange(recoilLatch, recoilSeq, recoilSeen) == recoilSeen) {\n"),
])

# 13. THE LASER STARTS PAST A SILENCER. (0.2.0: dots only, so the start is kept but moves nothing; patches 15, 34 and
#     39 anchor on its script call.) The gun's muzzle slot stays at the barrel when a silencer is fitted, so the beam
#     came out of the middle of the silencer. SetVRLaserStart(metres) moves the drawn beam's start that far down the
#     barrel; VRGestures sends the silencer length while the right gun is silenced (WeaponObject.IsSilenced) and 0
#     otherwise. The beam only: the shot leaves where it always did.
patch("src/Overlay/OverlayDebugDraw.cpp", [
    ('extern "C" __declspec(dllexport) int32_t CyberpunkVR_LaserBeam = 0;   // 1 = the beam too\n',
     'extern "C" __declspec(dllexport) int32_t CyberpunkVR_LaserBeam = 0;   // 1 = the beam too\n'
     '// How far down the barrel the gun\'s beam starts (SetVRLaserStart): a silencer\'s length while one is fitted, else 0.\n'
     'extern "C" __declspec(dllexport) volatile float CyberpunkVR_LaserStartM = 0.0f;\n'),
])
patch("src/Natives/OrientationProvider.cpp", [
    ("void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n",
     "// [VRGestures fork] where the right gun's beam starts, metres down the barrel from the muzzle slot: a silencer's length\n"
     "// while one is fitted (VRGestures), 0 otherwise. Clamped to [0, 0.6].\n"
     "extern \"C\" volatile float CyberpunkVR_LaserStartM;\n"
     "void SetVRLaserStart(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t) {\n"
     "    float m = 0.0f;\n"
     "    RED4ext::GetParameter(aFrame, &m);\n"
     "    aFrame->code++;\n"
     "    CyberpunkVR_LaserStartM = (std::isfinite(m) && m > 0.0f) ? (m < 0.6f ? m : 0.6f) : 0.0f;\n"
     "}\n\n"
     "void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n"),
])
patch("include/Natives/NativeFunctions.hpp", [
    ("void VRHandAimRay(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, RED4ext::DynArray<RED4ext::Vector4>* aOut, int64_t);   // [VRGestures fork]\n",
     "void VRHandAimRay(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, RED4ext::DynArray<RED4ext::Vector4>* aOut, int64_t);   // [VRGestures fork]\n"
     "void SetVRLaserStart(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork]\n"),
])
patch("src/Natives/Registration.cpp", [
    ("    rtti->RegisterFunction(fHandAim);\n",
     "    rtti->RegisterFunction(fHandAim);\n"
     "    // [VRGestures fork] where the gun's beam starts: past a silencer\n"
     "    auto fLaserStart = RED4ext::CGlobalFunction::Create(\"SetVRLaserStart\", \"SetVRLaserStart\", &SetVRLaserStart);\n"
     "    fLaserStart->flags = flags; fLaserStart->AddParam(\"Float\", \"metres\"); rtti->RegisterFunction(fLaserStart);\n"),
])

# 14. NO BARREL RAYCAST WHILE THE LASER IS OFF. The weapon module traces the barrel line every frame (two raycasts since
#     patch 6: Static, then Dynamic) for SetVRAimHit, and the only thing that reads that hit is the laser. With the laser
#     sight off (GetVRLaserSight) both traces are skipped.
patch("mods/cet/CyberpunkVRPort_Weapon/init.lua", [
    ("            if type(SetVRAimHit) == 'function' and q then\n",
     "            -- [VRGestures fork] only the laser reads the hit: no traces while it is off\n"
     "            if type(SetVRAimHit) == 'function' and q and (type(GetVRLaserSight) ~= 'function' or GetVRLaserSight()) then\n"),
])

# 15. EXPERIMENTAL: THE LAUNCHER OUT WITH A GUN STILL IN THE RIGHT HAND. Only while VRGestures' setting is on (the
#     VRGestures.launcherWithGun flat for the scripts, SetVRLauncherWithGun for the input merge); otherwise nothing changes.
#     The game puts the right-hand gun away whenever left-hand cyberware equips (LeftHandCyberwareEquipEvents.OnEnter sets
#     forceTempUnequipWeapon; the upper body's TemporaryUnequip then sends UnequipWeapon), so that flag is cleared for the
#     launcher. With a gun in the right hand: the left trigger becomes the launcher's own button (UseCombatGadget, RB) and
#     fires it on the PRESS -- the hand-aimed laser made release-to-fire unnecessary -- the right trigger stays the gun's,
#     the launcher ignores RangedAttack and never enters its charge state, and the dual-wield trigger merge stays out of it.
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_cyberware.reds", [
    ("  (scriptInterface.executionOwner as PlayerPuppet).vrLauncherShotQueued = false;\n"
     "  (scriptInterface.executionOwner as PlayerPuppet).vrLauncherKeepOpen = LeftHandCyberwareHelper.IsProjectileLauncherEquipped(scriptInterface);\n",
     "  (scriptInterface.executionOwner as PlayerPuppet).vrLauncherShotQueued = false;\n"
     "  (scriptInterface.executionOwner as PlayerPuppet).vrLauncherKeepOpen = LeftHandCyberwareHelper.IsProjectileLauncherEquipped(scriptInterface);\n"
     "  // [VRGestures fork] launcher with a gun: the game's equip asks the upper body to put the right-hand gun away\n"
     "  // (forceTempUnequipWeapon); with VRGestures.launcherWithGun on, it stays in hand.\n"
     "  if TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false) && LeftHandCyberwareHelper.IsProjectileLauncherEquipped(scriptInterface) {\n"
     "    stateContext.RemovePermanentBoolParameter(n\"forceTempUnequipWeapon\");\n"
     "  };\n"),
    ("public class VrLauncherReadyDecisions extends LeftHandCyberwareTransition {\n",
     "// [VRGestures fork] the launcher is out next to a gun in the right hand: it fires on its own button only\n"
     "public func VrLauncherWithGun(const scriptInterface: ref<StateGameScriptInterface>) -> Bool {\n"
     "  return TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false) && DefaultTransition.HasRightWeaponEquipped(scriptInterface);\n"
     "}\n\n"
     "public class VrLauncherReadyDecisions extends LeftHandCyberwareTransition {\n"),
    ("  protected final const func ToLeftHandCyberwareCharge(const stateContext: ref<StateContext>, const scriptInterface: ref<StateGameScriptInterface>) -> Bool {\n",
     "  protected final const func ToLeftHandCyberwareCharge(const stateContext: ref<StateContext>, const scriptInterface: ref<StateGameScriptInterface>) -> Bool {\n"
     "    if VrLauncherWithGun(scriptInterface) { return false; };   // [VRGestures fork] a press is the shot, no charge\n"),
    ("  protected final const func ToLeftHandCyberwareQuickAction(const stateContext: ref<StateContext>, const scriptInterface: ref<StateGameScriptInterface>) -> Bool {\n"
     "    if !stateContext.GetBoolParameter(n\"vrLauncherInputArmed\", true) || !LeftHandCyberwareHelper.ProjectileLauncherHasCharge(scriptInterface) { return false; };\n"
     "    if (scriptInterface.executionOwner as PlayerPuppet).IsAimingAtFriendly() { return false; };\n",
     "  protected final const func ToLeftHandCyberwareQuickAction(const stateContext: ref<StateContext>, const scriptInterface: ref<StateGameScriptInterface>) -> Bool {\n"
     "    if !stateContext.GetBoolParameter(n\"vrLauncherInputArmed\", true) || !LeftHandCyberwareHelper.ProjectileLauncherHasCharge(scriptInterface) { return false; };\n"
     "    if (scriptInterface.executionOwner as PlayerPuppet).IsAimingAtFriendly() { return false; };\n"
     "    // [VRGestures fork] with a gun in the right hand RangedAttack is the gun's: the launcher fires on the press of its\n"
     "    // own button (the left trigger, mapped to UseCombatGadget by the input merge)\n"
     "    if VrLauncherWithGun(scriptInterface) { return scriptInterface.IsActionJustPressed(n\"UseCombatGadget\"); };\n"),
    ("    if scriptInterface.GetActionValue(n\"UseCombatGadget\") == 0.00 && scriptInterface.GetActionValue(n\"RangedAttack\") == 0.00 {\n",
     "    // [VRGestures fork] with a gun in the right hand a held RangedAttack is the gun firing: only the launcher's button re-arms it\n"
     "    if scriptInterface.GetActionValue(n\"UseCombatGadget\") == 0.00 && (VrLauncherWithGun(scriptInterface) || scriptInterface.GetActionValue(n\"RangedAttack\") == 0.00) {\n"),
])
patch("include/Anim/HandGestures.hpp", [
    ("void PublishEquipment(int occupiedMask);\n",
     "void PublishEquipment(int occupiedMask);\n"
     "// [VRGestures fork] the right hand holds a real weapon (not fists / arm cyberware), per the latest PublishEquipment\n"
     "bool RightHandHoldsGun();\n"),
])
patch("src/Anim/HandGestures.cpp", [
    ("void PublishEquipment(int mask) {\n    equipment.store((GetTickCount64()<<2)|uint64_t(mask&3),std::memory_order_release);\n}\n",
     "void PublishEquipment(int mask) {\n    equipment.store((GetTickCount64()<<2)|uint64_t(mask&3),std::memory_order_release);\n}\n"
     "bool RightHandHoldsGun() {   // [VRGestures fork] bit 1 = the right slot; stale after 500 ms like Apply's read\n"
     "    const auto held=equipment.load(std::memory_order_acquire);\n"
     "    const auto now=GetTickCount64();\n"
     "    return held && now>=(held>>2) && now-(held>>2)<=500 && ((held>>1)&1)!=0;\n"
     "}\n"),
])
patch("src/Hooks/XInput.cpp", [
    ("extern \"C\" __declspec(dllexport) volatile uint64_t CyberpunkVR_LeftTriggerBlockUntil = 0;\n",
     "extern \"C\" __declspec(dllexport) volatile uint64_t CyberpunkVR_LeftTriggerBlockUntil = 0;\n"
     "extern \"C\" volatile uint64_t CyberpunkVR_LauncherWithGunUntil;   // [VRGestures fork] Natives/OrientationProvider.cpp\n"),
    ("    const bool firearmTrigger=g_VRBind==4 && gameplayScreen && !uiPopupOpen && !g_isInVehicle &&\n"
     "        g_hasWeaponEquipped && CyberpunkVR_WeaponClass>=1 && CyberpunkVR_WeaponClass<=4 && cyberwareKind!=4 &&\n",
     "    // [VRGestures fork] the launcher out with a gun still in the right hand (VRGestures' experimental setting,\n"
     "    // SetVRLauncherWithGun): the right trigger stays the gun's, the left one becomes the launcher's own button.\n"
     "    const bool launcherWithGun=cyberwareKind==4 && GetTickCount64()<CyberpunkVR_LauncherWithGunUntil &&\n"
     "        cvr::gestures::RightHandHoldsGun();\n"
     "    const bool firearmTrigger=g_VRBind==4 && gameplayScreen && !uiPopupOpen && !g_isInVehicle &&\n"
     "        g_hasWeaponEquipped && CyberpunkVR_WeaponClass>=1 && CyberpunkVR_WeaponClass<=4 && (cyberwareKind!=4 || launcherWithGun) &&\n"),
    ("        pState->Gamepad.bRightTrigger=lt;   // [VRGestures fork] lt: honours the left-trigger block\n"
     "        pState->Gamepad.bLeftTrigger=0;\n",
     "        if(launcherWithGun) {\n"
     "            // [VRGestures fork] the left trigger is the launcher's own button (UseCombatGadget = RB); RT stays the gun's\n"
     "            if(lt>=90)pState->Gamepad.wButtons|=0x0200;\n"
     "        } else pState->Gamepad.bRightTrigger=lt;   // [VRGestures fork] lt: honours the left-trigger block\n"
     "        pState->Gamepad.bLeftTrigger=0;\n"),
    ("        gameplayScreen && !uiPopupOpen && !g_isInVehicle && g_hasWeaponEquipped && !menuCapture && !scannerActive;\n",
     "        gameplayScreen && !uiPopupOpen && !g_isInVehicle && g_hasWeaponEquipped && !menuCapture && !scannerActive &&\n"
     "        !launcherWithGun;   // [VRGestures fork] a launcher next to the gun is not a second gun\n"),
])
patch("src/Natives/OrientationProvider.cpp", [
    ("void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n",
     "// [VRGestures fork] the launcher may stay out next to a gun in the right hand (VRGestures' experimental setting): a\n"
     "// deadline VRGestures holds up once a second, so a mod that stops calling hands the triggers back within 2.5 s.\n"
     "extern \"C\" __declspec(dllexport) volatile uint64_t CyberpunkVR_LauncherWithGunUntil = 0;\n"
     "void SetVRLauncherWithGun(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t) {\n"
     "    int32_t on = 0;\n"
     "    RED4ext::GetParameter(aFrame, &on);\n"
     "    aFrame->code++;\n"
     "    CyberpunkVR_LauncherWithGunUntil = on ? GetTickCount64() + 2500 : 0;\n"
     "}\n\n"
     "void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n"),
])
patch("include/Natives/NativeFunctions.hpp", [
    ("void SetVRLaserStart(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork]\n",
     "void SetVRLaserStart(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork]\n"
     "void SetVRLauncherWithGun(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork]\n"),
])
patch("src/Natives/Registration.cpp", [
    ("    fLaserStart->flags = flags; fLaserStart->AddParam(\"Float\", \"metres\"); rtti->RegisterFunction(fLaserStart);\n",
     "    fLaserStart->flags = flags; fLaserStart->AddParam(\"Float\", \"metres\"); rtti->RegisterFunction(fLaserStart);\n"
     "    // [VRGestures fork] the launcher out next to a gun (experimental)\n"
     "    auto fLauncherGun = RED4ext::CGlobalFunction::Create(\"SetVRLauncherWithGun\", \"SetVRLauncherWithGun\", &SetVRLauncherWithGun);\n"
     "    fLauncherGun->flags = flags; fLauncherGun->AddParam(\"Int32\", \"on\"); rtti->RegisterFunction(fLauncherGun);\n"),
])

# 16. LAUNCHER WITH A GUN, FIXED FROM THE FIRST TEST. (a) With a pistol in the right hand the port's cyberware kind is the
#     pistol's, not the launcher's (4), so patch 15's trigger split never engaged and the left trigger stayed the pistol's
#     aim. VRGestures now says, every frame the launcher is out next to a gun, that it is (SetVRLauncherWithGun, a 0.5 s
#     deadline), and the split and the left trigger's mapping follow that alone. (b) The weapon cycle VRGestures used to
#     bring the launcher out put the pistol away for a moment (a weapon switch); in this mode it requests the launcher as
#     left-hand cyberware instead, and that request now counts as "selected" so the launcher stays out after its shots.
patch("src/Hooks/XInput.cpp", [
    ("    const bool launcherWithGun=cyberwareKind==4 && GetTickCount64()<CyberpunkVR_LauncherWithGunUntil &&\n",
     "    const bool launcherWithGun=GetTickCount64()<CyberpunkVR_LauncherWithGunUntil &&   // [VRGestures fork] 16: VRGestures' word\n"),
    ("    if(cyberwareKind==4 && gameplayScreen && !g_isInVehicle) {\n",
     "    if((cyberwareKind==4 || launcherWithGun) && gameplayScreen && !g_isInVehicle) {   // [VRGestures fork] 16\n"),
])
patch("src/Natives/OrientationProvider.cpp", [
    ("    CyberpunkVR_LauncherWithGunUntil = on ? GetTickCount64() + 2500 : 0;\n",
     "    CyberpunkVR_LauncherWithGunUntil = on ? GetTickCount64() + 500 : 0;   // 16: refreshed every frame the launcher is out\n"),
])
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_launcher_selection.reds", [
    ("      player.vrLauncherSelectedAsWeapon = NotEquals(action, EquipmentManipulationAction.RequestLeftHandCyberware);\n",
     "      // [VRGestures fork] launcher with a gun: VRGestures requests it as left-hand cyberware (a weapon-cycle pick would\n"
     "      // switch the gun away), and it is to stay out all the same\n"
     "      player.vrLauncherSelectedAsWeapon = NotEquals(action, EquipmentManipulationAction.RequestLeftHandCyberware)\n"
     "        || TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false);\n"),
])

# 17. THE LAUNCHER IS NOT IN THE WEAPON CYCLE. VRGestures brings it out as left-hand cyberware (RequestLeftHandCyberware,
#     which only VRGestures sends; the game's own gadget button sends RequestGadget), so the cycle is the game's own again
#     -- with the launcher installed the port used to take every cycle over and put one weapon alone in the right hand,
#     which also dropped a dual-wield partner. That request now always counts as "selected", so the launcher stays out
#     after its shots until VRGestures puts it away (UnequipLeftHandCyberware).
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_launcher_selection.reds", [
    ("// The launcher occupies the native fourth, cyberware slot in the weapon cycle.\n",
     "// [VRGestures fork] 17: the launcher is not a weapon-cycle slot; VRGestures brings it out as left-hand cyberware.\n"
     "public func VrgLauncherOutOfCycle() -> Bool {\n"
     "  return true;\n"
     "}\n\n"
     "// The launcher occupies the native fourth, cyberware slot in the weapon cycle.\n"),
    ("  if !ItemID.IsValid(launcher) || !(this.m_owner as PlayerPuppet).ShouldAllowCycleToFistCyberware() {\n",
     "  if !ItemID.IsValid(launcher) || !(this.m_owner as PlayerPuppet).ShouldAllowCycleToFistCyberware() || VrgLauncherOutOfCycle() {\n"),
    ("  if Equals(action, EquipmentManipulationAction.CycleWeaponWheelItem) && ItemID.IsValid(launcher) {\n",
     "  if Equals(action, EquipmentManipulationAction.CycleWeaponWheelItem) && ItemID.IsValid(launcher) && !VrgLauncherOutOfCycle() {\n"),
    ("      player.vrLauncherSelectedAsWeapon = NotEquals(action, EquipmentManipulationAction.RequestLeftHandCyberware)\n"
     "        || TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false);\n",
     "      player.vrLauncherSelectedAsWeapon = NotEquals(action, EquipmentManipulationAction.RequestLeftHandCyberware)\n"
     "        || VrgLauncherOutOfCycle();   // 17: VRGestures' request is the only one, and its launcher stays out\n"),
])
# 18. LAUNCHER WITH A GUN STAYS OUT. (a) The equip's "put the gun away" flag was removed only once the launcher counted
#     as equipped, which at that moment it may not yet: the pistol went away and came back. Now it is removed whenever the
#     mode is on. (b) A right-hand request (the pistol drawn again, a weapon switch) cleared the launcher's keep-open, so
#     its shot left along the head's aim and it closed after the shot; in this mode only left-hand and both-hand requests
#     do. (c) The weapon switch button, with a gun in the right hand, switches the gun and leaves the launcher out.
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_cyberware.reds", [
    ("  if TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false) && LeftHandCyberwareHelper.IsProjectileLauncherEquipped(scriptInterface) {\n",
     "  if TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false) {   // 18: whether or not it counts as equipped yet\n"),
    ("  if scriptInterface.IsActionJustPressed(n\"SwitchItem\") || scriptInterface.IsActionJustTapped(n\"HolsterWeapon\") || scriptInterface.IsActionJustReleased(n\"UseConsumable\") { return false; };\n",
     "  // [VRGestures fork] 18: with a gun in the right hand the switch button switches the gun\n"
     "  if scriptInterface.IsActionJustPressed(n\"SwitchItem\") && !VrLauncherWithGun(scriptInterface) { return false; };\n"
     "  if scriptInterface.IsActionJustTapped(n\"HolsterWeapon\") || scriptInterface.IsActionJustReleased(n\"UseConsumable\") { return false; };\n"),
])
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_launcher_selection.reds", [
    ("      if !this.CheckCyberwareItemForActivatedAction(item) {\n",
     "      // [VRGestures fork] 18: with the launcher next to a gun, a right-hand request is the gun's business\n"
     "      if !this.CheckCyberwareItemForActivatedAction(item) && !(TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false)\n"
     "          && Equals(this.GetRequestSlotFromEquipmentManipulationAction(action), EquipmentManipulationRequestSlot.Right)) {\n"),
])
# 19. LAUNCHER WITH A GUN, SAID DIRECTLY. Patches 15 and 18 read the VRGestures.launcherWithGun TweakDB flat, which
#     VRGestures sets at runtime and which may not reach these scripts; VRGestures now also says so on the player
#     (VrgSetLauncherWithGun). In that mode the launcher shot flies along the hand even though the port's binding is the
#     gun's (VRLauncherControllerAim is false then), from the hand when the launcher's barrel points are not published.
#     The VRGestures request no longer counts as a weapon-cycle pick (that made any lost selection an instant unequip).
#     VrgLauncherState() reports keep-open, selection, the state machines and why the launcher last closed, for the log.
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_cyberware.reds", [
    ("private let vrCyberwareHandlingRequest: Bool;\n",
     "private let vrCyberwareHandlingRequest: Bool;\n"
     "// [VRGestures fork] 19: the launcher-with-a-gun mode, said by VRGestures on the player; and the launcher's state for its log\n"
     "@addField(PlayerPuppet) public let vrforkWithGun: Bool;\n"
     "@addField(PlayerPuppet) public let vrforkWhy: String;\n"
     "@addMethod(PlayerPuppet)\n"
     "public func VrgSetLauncherWithGun(on: Bool) -> Void {\n"
     "  this.vrforkWithGun = on;\n"
     "}\n"
     "public func VrgWithGunMode(player: ref<PlayerPuppet>) -> Bool {\n"
     "  return (IsDefined(player) && player.vrforkWithGun) || TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false);\n"
     "}\n"
     "public func VrforkBit(b: Bool) -> String {\n"
     "  return b ? \"1\" : \"0\";\n"
     "}\n"
     "@addMethod(PlayerPuppet)\n"
     "public func VrgLauncherState() -> String {\n"
     "  let bb = this.GetPlayerStateMachineBlackboard();\n"
     "  let psm = GetAllBlackboardDefs().PlayerStateMachine;\n"
     "  return \"keep=\" + VrforkBit(this.vrLauncherKeepOpen) + \" sel=\" + VrforkBit(this.vrLauncherSelectedAsWeapon)\n"
     "    + \" cycle=\" + VrforkBit(this.vrLauncherFromWeaponCycle) + \" withGun=\" + VrforkBit(this.vrforkWithGun)\n"
     "    + \" flat=\" + VrforkBit(TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false))\n"
     "    + \" lhc=\" + IntToString(bb.GetInt(psm.LeftHandCyberware)) + \" upper=\" + IntToString(bb.GetInt(psm.UpperBody))\n"
     "    + \" ctrlAim=\" + VrforkBit(VRLauncherControllerAim()) + \" why=\" + this.vrforkWhy;\n"
     "}\n"),
    ("  (scriptInterface.executionOwner as PlayerPuppet).vrLauncherKeepOpen = LeftHandCyberwareHelper.IsProjectileLauncherEquipped(scriptInterface);\n"
     "  // [VRGestures fork] launcher with a gun:",
     "  (scriptInterface.executionOwner as PlayerPuppet).vrLauncherKeepOpen = LeftHandCyberwareHelper.IsProjectileLauncherEquipped(scriptInterface);\n"
     "  (scriptInterface.executionOwner as PlayerPuppet).vrforkWhy = \"\";\n"
     "  // [VRGestures fork] launcher with a gun:"),
    ("  if TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false) {   // 18: whether or not it counts as equipped yet\n",
     "  if VrgWithGunMode(scriptInterface.executionOwner as PlayerPuppet) {   // 18, 19: whether or not it counts as equipped yet\n"),
    ("  (scriptInterface.executionOwner as PlayerPuppet).vrLauncherKeepOpen = LeftHandCyberwareHelper.IsProjectileLauncherEquipped(scriptInterface);\n"
     "}\n\n@wrapMethod(LeftHandCyberwareEventsTransition)\n",
     "  (scriptInterface.executionOwner as PlayerPuppet).vrLauncherKeepOpen = LeftHandCyberwareHelper.IsProjectileLauncherEquipped(scriptInterface);\n"
     "  if !(scriptInterface.executionOwner as PlayerPuppet).vrLauncherKeepOpen { (scriptInterface.executionOwner as PlayerPuppet).vrforkWhy = \"equip exit: not equipped\"; };\n"
     "}\n\n@wrapMethod(LeftHandCyberwareEventsTransition)\n"),
    ("  (scriptInterface.executionOwner as PlayerPuppet).vrLauncherFromWeaponCycle = false;\n  wrappedMethod(stateContext, scriptInterface);\n",
     "  (scriptInterface.executionOwner as PlayerPuppet).vrLauncherFromWeaponCycle = false;\n"
     "  (scriptInterface.executionOwner as PlayerPuppet).vrforkWhy = \"closed <- \" + (scriptInterface.executionOwner as PlayerPuppet).vrforkWhy;\n"
     "  wrappedMethod(stateContext, scriptInterface);\n"),
    ("    player.vrLauncherKeepOpen = false;\n    player.vrLauncherSelectedAsWeapon = false;\n  };\n  // GetItemID/CycleWeapon",
     "    player.vrLauncherKeepOpen = false;\n    player.vrLauncherSelectedAsWeapon = false;\n    player.vrforkWhy = \"UnequipAll request\";\n  };\n  // GetItemID/CycleWeapon"),
    ("  if !player.vrLauncherKeepOpen || !IsDefined(weapon) { return false; };\n"
     "  if !WeaponObject.IsOfType(weapon.GetItemID(), gamedataItemType.Cyb_Launcher) { return false; };\n"
     "  if this.ShouldInstantlyUnequipCyberware(scriptInterface, stateContext) { return false; };\n"
     "  if stateContext.GetBoolParameter(n\"InterruptLeftHandAction\") { return false; };\n"
     "  if this.IsInVisionModeActiveState(stateContext, scriptInterface) { return false; };\n"
     "  if this.GetCancelChargeButtonInput(scriptInterface) { return false; };\n"
     "  // [VRGestures fork] 18: with a gun in the right hand the switch button switches the gun\n"
     "  if scriptInterface.IsActionJustPressed(n\"SwitchItem\") && !VrLauncherWithGun(scriptInterface) { return false; };\n"
     "  if scriptInterface.IsActionJustTapped(n\"HolsterWeapon\") || scriptInterface.IsActionJustReleased(n\"UseConsumable\") { return false; };\n"
     "  selected = EquipmentSystem.GetData(player).GetSlotActiveItem(EquipmentManipulationRequestSlot.Left);\n"
     "  if !ItemID.IsValid(selected) || selected != weapon.GetItemID() { return false; };\n",
     "  // [VRGestures fork] 19: each refusal names itself for VRGestures' log\n"
     "  if !player.vrLauncherKeepOpen { if StrLen(player.vrforkWhy) == 0 { player.vrforkWhy = \"stay: keep-open off\"; }; return false; };\n"
     "  if !IsDefined(weapon) { player.vrforkWhy = \"stay: no left weapon\"; return false; };\n"
     "  if !WeaponObject.IsOfType(weapon.GetItemID(), gamedataItemType.Cyb_Launcher) { player.vrforkWhy = \"stay: left weapon not a launcher\"; return false; };\n"
     "  if this.ShouldInstantlyUnequipCyberware(scriptInterface, stateContext) { player.vrforkWhy = \"stay: instant unequip\"; return false; };\n"
     "  if stateContext.GetBoolParameter(n\"InterruptLeftHandAction\") { player.vrforkWhy = \"stay: interrupt left hand\"; return false; };\n"
     "  if this.IsInVisionModeActiveState(stateContext, scriptInterface) { player.vrforkWhy = \"stay: vision mode\"; return false; };\n"
     "  if this.GetCancelChargeButtonInput(scriptInterface) { player.vrforkWhy = \"stay: cancel button\"; return false; };\n"
     "  // [VRGestures fork] 18: with a gun in the right hand the switch button switches the gun\n"
     "  if scriptInterface.IsActionJustPressed(n\"SwitchItem\") && !VrLauncherWithGun(scriptInterface) { player.vrforkWhy = \"stay: switch button\"; return false; };\n"
     "  if scriptInterface.IsActionJustTapped(n\"HolsterWeapon\") || scriptInterface.IsActionJustReleased(n\"UseConsumable\") { player.vrforkWhy = \"stay: holster/consumable\"; return false; };\n"
     "  selected = EquipmentSystem.GetData(player).GetSlotActiveItem(EquipmentManipulationRequestSlot.Left);\n"
     "  if !ItemID.IsValid(selected) || selected != weapon.GetItemID() { player.vrforkWhy = \"stay: left slot not the launcher\"; return false; };\n"),
    ("  return TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false) && DefaultTransition.HasRightWeaponEquipped(scriptInterface);\n",
     "  return VrgWithGunMode(scriptInterface.executionOwner as PlayerPuppet) && DefaultTransition.HasRightWeaponEquipped(scriptInterface);   // 19\n"),
])
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_launcher_selection.reds", [
    ("      if player.vrLauncherSelectedAsWeapon { player.vrLauncherFromWeaponCycle = true; };\n",
     "      // [VRGestures fork] 19: VRGestures' left-hand request is not a weapon-cycle pick\n"
     "      if player.vrLauncherSelectedAsWeapon && NotEquals(action, EquipmentManipulationAction.RequestLeftHandCyberware) { player.vrLauncherFromWeaponCycle = true; };\n"),
    ("!(TweakDBInterface.GetBool(t\"VRGestures.launcherWithGun\", false)\n",
     "!(VrgWithGunMode(player)\n"),
    ("        player.vrLauncherKeepOpen = false;\n        player.vrLauncherSelectedAsWeapon = false;\n      };\n",
     "        player.vrLauncherKeepOpen = false;\n        player.vrLauncherSelectedAsWeapon = false;\n"
     "        player.vrforkWhy = \"request \" + IntToString(EnumInt(action)) + \" cleared keep-open\";\n      };\n"),
])
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_launcher_aim.reds", [
    ("  if IsDefined(player) && player.vrLauncherKeepOpen && VRLauncherControllerAim() {\n",
     "  if IsDefined(player) && player.vrLauncherKeepOpen && (VRLauncherControllerAim() || VrgWithGunMode(player)) {   // [VRGestures fork] 19\n"),
    ("|| !VRLauncherControllerAim() {\n",
     "|| !(VRLauncherControllerAim() || VrgWithGunMode(player)) {   // [VRGestures fork] 19\n"),
    ("  end = VRCyberwarePoint(0, 1);\n",
     "  end = VRCyberwarePoint(0, 1);\n"
     "  // [VRGestures fork] 19: next to a gun the port may not publish the launcher's barrel: start just ahead of the hand\n"
     "  if (muzzle.W == 0.00 || end.W == 0.00 || Vector4.Distance(muzzle, end) < 0.01) && VrgWithGunMode(player) {\n"
     "    let gunRay = VRHandAimRay(0);\n"
     "    if ArraySize(gunRay) >= 2 && Vector4.Length(gunRay[1]) > 0.50 {\n"
     "      muzzle = gunRay[0] + Vector4.Normalize(gunRay[1]) * 0.30;\n"
     "      muzzle.W = 1.00;\n"
     "      end = muzzle + Vector4.Normalize(gunRay[1]);\n"
     "      end.W = 1.00;\n"
     "    };\n"
     "  };\n"),
])
# 20. LAUNCHER WITH A GUN, FROM THE PATCH 19 LOG. (a) Patch 19's "not a weapon-cycle pick" let the game's own quick shot
#     follow the equip at once (its EnterCondition is just "gadget button up"): the launcher fired as it came out. The
#     request counts as a cycle pick again. (b) The launcher in the left weapon slot made a pistol a dual-wield pair:
#     the upper body went to DualWield, which changed the right hand's grip and model. Next to a gun the launcher is not
#     a left weapon. (c) The trigger press also reached the weapon state's gadget button, whose RequestGadget cleared
#     keep-open and fired the game's screen-centre (head-aimed) shot, then closed the launcher. While the launcher is
#     out next to a gun that request is ignored; the launcher fires on its own button from the ready state.
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_launcher_selection.reds", [
    ("      // [VRGestures fork] 19: VRGestures' left-hand request is not a weapon-cycle pick\n"
     "      if player.vrLauncherSelectedAsWeapon && NotEquals(action, EquipmentManipulationAction.RequestLeftHandCyberware) { player.vrLauncherFromWeaponCycle = true; };\n",
     "      // [VRGestures fork] 20: counted as a cycle pick, which keeps the game's quick shot from following the equip\n"
     "      if player.vrLauncherSelectedAsWeapon { player.vrLauncherFromWeaponCycle = true; };\n"),
])
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_cyberware.reds", [
    ("    player.vrforkWhy = \"UnequipAll request\";\n  };\n",
     "    player.vrforkWhy = \"UnequipAll request\";\n  };\n"
     "  // [VRGestures fork] 20: next to a gun the launcher fires on its own button; the gadget button's request would clear\n"
     "  // keep-open and fire the game's screen-centre shot\n"
     "  if IsDefined(player) && Equals(request.requestType, EquipmentManipulationAction.RequestGadget) && VrgWithGunMode(player)\n"
     "      && player.vrLauncherKeepOpen {\n"
     "    player.vrforkWhy = \"gadget request ignored\";\n"
     "    return;\n"
     "  };\n"),
    ("public func VrforkBit(b: Bool) -> String {\n",
     "// 20: the launcher out next to a gun is not a left-hand gun -- the right hand keeps its one-gun state (DualWield changed\n"
     "// its grip and hand) and the left-gun rules leave the launcher alone\n"
     "@wrapMethod(DefaultTransition)\n"
     "public final static func HasLeftWeaponEquipped(const scriptInterface: ref<StateGameScriptInterface>, opt checkForTag: Bool) -> Bool {\n"
     "  if !wrappedMethod(scriptInterface, checkForTag) { return false; };\n"
     "  if !VrgWithGunMode(scriptInterface.executionOwner as PlayerPuppet) || !DefaultTransition.HasRightWeaponEquipped(scriptInterface) { return true; };\n"
     "  let left = scriptInterface.GetTransactionSystem().GetItemInSlot(scriptInterface.executionOwner, t\"AttachmentSlots.WeaponLeft\") as WeaponObject;\n"
     "  return !IsDefined(left) || !WeaponObject.IsOfType(left.GetItemID(), gamedataItemType.Cyb_Launcher);\n"
     "}\n"
     "public func VrforkBit(b: Bool) -> String {\n"),
])
# 21. THE GUN HAND KEEPS ITS GRIP NEXT TO THE LAUNCHER. The launcher's deploy animation covers both arms and assumes an
#     empty right hand: with a gun in it the fingers curled into a fist beside the grip. The port already learns the
#     game's own right-hand grip every frame a gun is held (VrikCarryGripPoseRight); while VRGestures says the launcher
#     is out next to a gun (CyberpunkVR_LauncherWithGunUntil) that grip is not learned but replayed onto the fingers.
#     The learner was off whenever native cyberware owns the pose pass (the launcher's rig counts), so it learns there
#     too, read-only.
patch("include/Anim/ReloadPose.hpp", [
    ("void VrikCarryGripPoseRight(uint8_t* boneBuf);\n",
     "void VrikCarryGripPoseRight(uint8_t* boneBuf);\n"
     "void VrgHoldGunGripRight(uint8_t* boneBuf, bool nativeCyberware);   // [VRGestures fork] 21\n"),
])
patch("src/Anim/ReloadPose.cpp", [
    ("namespace {\nfloat g_gripRotR[32][4] = {};\n",
     "extern \"C\" volatile uint64_t CyberpunkVR_LauncherWithGunUntil;   // [VRGestures fork] 21: Natives/OrientationProvider.cpp\n"
     "namespace {\nfloat g_gripRotR[32][4] = {};\n"),
    # 0.2.0: upstream's learner also skips a weapon in the left hand (the left-handed mode)
    ("    if (g_hasWeaponEquipped && CyberpunkVR_CarryLeft == 0 && !cvr::anim::WeaponInLeftHand()\n        && !g_VRSmokeFingerActive && !g_VRReloadFingerActive[1]) {\n",
     "    if (g_hasWeaponEquipped && CyberpunkVR_CarryLeft == 0 && !cvr::anim::WeaponInLeftHand()\n        && !g_VRSmokeFingerActive && !g_VRReloadFingerActive[1]\n"
     "        && GetTickCount64() >= CyberpunkVR_LauncherWithGunUntil) {   // [VRGestures fork] 21: not the launcher's fist\n"),
    ("    CyberpunkVR_DebugCarryGripBones = wrote;\n}\n",
     "    CyberpunkVR_DebugCarryGripBones = wrote;\n}\n\n"
     "// [VRGestures fork] 21: the launcher out next to a gun -- the right hand wears its own learned grip, not the launcher\n"
     "// animation's empty fist. With native cyberware owning the pass VrikCarryGripPoseRight does not run, so this learns.\n"
     "void VrgHoldGunGripRight(uint8_t* boneBuf, bool nativeCyberware) {\n"
     "    const int  cnt = g_VRSmokeFingerCount;\n"
     "    const int* idx = g_VRSmokeFingerIdx;\n"
     "    if (cnt <= 0 || !idx) return;\n"
     "    const bool withGun = GetTickCount64() < CyberpunkVR_LauncherWithGunUntil;\n"
     "    if (!withGun) {\n"
     "        if (nativeCyberware && g_hasWeaponEquipped && CyberpunkVR_CarryLeft == 0\n"
     "            && !g_VRSmokeFingerActive && !g_VRReloadFingerActive[1]) {\n"
     "            for (int k = 0; k < cnt && k < 32; ++k) {\n"
     "                const int bi = idx[k];\n"
     "                if (bi < 0 || bi >= VRIK_MAX_BONES) continue;\n"
     "                const float* q = reinterpret_cast<const float*>(boneBuf + bi * 48 + VRIK_ROT_OFF);\n"
     "                g_gripRotR[k][0] = q[0]; g_gripRotR[k][1] = q[1]; g_gripRotR[k][2] = q[2]; g_gripRotR[k][3] = q[3];\n"
     "            }\n"
     "            g_gripCountR = cnt;\n"
     "            g_gripHaveR = 1;\n"
     "        }\n"
     "        return;\n"
     "    }\n"
     "    if (!g_gripHaveR || !g_hasWeaponEquipped || g_VRReloadFingerActive[1] || g_VRSmokeFingerActive) return;\n"
     "    const int n = (g_gripCountR > 0 && g_gripCountR < cnt) ? g_gripCountR : cnt;\n"
     "    for (int k = 0; k < n && k < 32; ++k) {\n"
     "        const int bi = idx[k];\n"
     "        if (bi < 0 || bi >= VRIK_MAX_BONES) continue;\n"
     "        const float* tq = g_gripRotR[k];\n"
     "        if (tq[0] == 0.0f && tq[1] == 0.0f && tq[2] == 0.0f && tq[3] == 0.0f) continue;\n"
     "        float* q = reinterpret_cast<float*>(boneBuf + bi * 48 + VRIK_ROT_OFF);\n"
     "        q[0] = tq[0]; q[1] = tq[1]; q[2] = tq[2]; q[3] = tq[3];\n"
     "    }\n"
     "}\n"),
])
patch("src/Hooks/AnimPose.cpp", [
    ("                if(!VRIK_UsesNativeCyberware())cvr::anim::VrikCarryGripPoseRight(boneBuf);\n",
     "                if(!VRIK_UsesNativeCyberware())cvr::anim::VrikCarryGripPoseRight(boneBuf);\n"
     "                cvr::anim::VrgHoldGunGripRight(boneBuf,VRIK_UsesNativeCyberware());   // [VRGestures fork] 21\n"),
])
# 22. THE GRIP IS LEARNED ONLY FROM A RIGHT HAND HOLDING ALONE. Patch 21's learner also ran in the moment between the
#     launcher attaching and VRGestures first saying it is out, and learned the launcher animation's fist -- which it
#     then replayed. A grip is now learned only while the right hand holds a weapon and the left holds nothing. And the
#     launcher's own graph drives the passes once it is ready, which return before the finger layers: held there too.
patch("include/Anim/HandGestures.hpp", [
    ("bool RightHandHoldsGun();\n",
     "bool RightHandHoldsGun();\n"
     "// [VRGestures fork] 22: the right hand holds a real weapon and the left hand nothing\n"
     "bool OnlyRightHandHolds();\n"),
])
patch("src/Anim/HandGestures.cpp", [
    ("void Apply(uint8_t* buffer) {\n",
     "bool OnlyRightHandHolds() {   // [VRGestures fork] 22\n"
     "    const auto held=equipment.load(std::memory_order_acquire);\n"
     "    const auto now=GetTickCount64();\n"
     "    return held && now>=(held>>2) && now-(held>>2)<=500 && (held&3)==2;\n"
     "}\n"
     "void Apply(uint8_t* buffer) {\n"),
])
patch("src/Anim/ReloadPose.cpp", [
    ("#include \"Anim/ReloadPose.hpp\"\n",
     "#include \"Anim/ReloadPose.hpp\"\n"
     "#include \"Anim/HandGestures.hpp\"   // [VRGestures fork] 22: OnlyRightHandHolds\n"),
    ("        && GetTickCount64() >= CyberpunkVR_LauncherWithGunUntil) {   // [VRGestures fork] 21: not the launcher's fist\n",
     "        && GetTickCount64() >= CyberpunkVR_LauncherWithGunUntil   // [VRGestures fork] 21: not the launcher's fist\n"
     "        && cvr::gestures::OnlyRightHandHolds()) {                  // 22: nor its fist before VRGestures says so\n"),
    ("        if (nativeCyberware && g_hasWeaponEquipped && CyberpunkVR_CarryLeft == 0\n"
     "            && !g_VRSmokeFingerActive && !g_VRReloadFingerActive[1]) {\n",
     "        if (nativeCyberware && g_hasWeaponEquipped && CyberpunkVR_CarryLeft == 0\n"
     "            && !g_VRSmokeFingerActive && !g_VRReloadFingerActive[1] && cvr::gestures::OnlyRightHandHolds()) {   // 22\n"),
])
patch("src/Hooks/AnimPose.cpp", [
    ("                        if(g_solveCacheModel && g_solveCacheN>0 && !headAimWork && !suspended && !DeviceCamActive() && !cvr::ladder::Active())\n"
     "                            VRIK_ApplyCyberwarePose(boneBuf,reinterpret_cast<float*>(trackBuf),\n",
     "                        // [VRGestures fork] 22: the launcher's own graph drives these passes once it is ready, and they\n"
     "                        // return before the finger layers -- the gun hand's grip is held here too\n"
     "                        cvr::anim::VrgHoldGunGripRight(boneBuf,true);\n"
     "                        if(g_solveCacheModel && g_solveCacheN>0 && !headAimWork && !suspended && !DeviceCamActive() && !cvr::ladder::Active())\n"
     "                            VRIK_ApplyCyberwarePose(boneBuf,reinterpret_cast<float*>(trackBuf),\n"),
])
# 23. THE GUN STAYS IN THE GRIP NEXT TO THE LAUNCHER. The launcher's animation, made for an empty right hand, also moves
#     WeaponRight -- the bone the gun hangs from -- so with the fingers held (21, 22) the gun sat forward of them. Its
#     full local transform (scale too: an animation hides a held prop with it) is learned with the finger grip and put
#     back with it.
patch("src/Anim/ReloadPose.cpp", [
    ("int   g_gripHaveR  = 0;\n",
     "int   g_gripHaveR  = 0;\n"
     "float g_gripWeaponPos[3] = {}, g_gripWeaponRot[4] = {};   // [VRGestures fork] 23: WeaponRight, the gun's bone\n"
     "int   g_gripWeaponHave = 0;\n"
     "void VrgLearnGripWeapon(const uint8_t* boneBuf) {\n"
     "    const int wi = g_VRSmokeCigIdx;\n"
     "    if (wi < 0 || wi >= VRIK_MAX_BONES) return;\n"
     "    const float* t = reinterpret_cast<const float*>(boneBuf + wi * 48 + VRIK_TRANS_OFF);\n"
     "    const float* q = reinterpret_cast<const float*>(boneBuf + wi * 48 + VRIK_ROT_OFF);\n"
     "    for (int k = 0; k < 3; ++k) g_gripWeaponPos[k] = t[k];\n"
     "    for (int k = 0; k < 4; ++k) g_gripWeaponRot[k] = q[k];\n"
     "    g_gripWeaponHave = 1;\n"
     "}\n"),
    ("        g_gripCountR = cnt;\n        g_gripHaveR = 1;\n        CyberpunkVR_DebugCarryGripHave = 1;\n",
     "        g_gripCountR = cnt;\n        g_gripHaveR = 1;\n        VrgLearnGripWeapon(boneBuf);   // [VRGestures fork] 23\n"
     "        CyberpunkVR_DebugCarryGripHave = 1;\n"),
    ("            g_gripCountR = cnt;\n            g_gripHaveR = 1;\n        }\n        return;\n",
     "            g_gripCountR = cnt;\n            g_gripHaveR = 1;\n            VrgLearnGripWeapon(boneBuf);   // 23\n        }\n        return;\n"),
    ("        q[0] = tq[0]; q[1] = tq[1]; q[2] = tq[2]; q[3] = tq[3];\n    }\n}\n",
     "        q[0] = tq[0]; q[1] = tq[1]; q[2] = tq[2]; q[3] = tq[3];\n    }\n"
     "    // 23: and the gun's bone back in the grip\n"
     "    const int wi = g_VRSmokeCigIdx;\n"
     "    if (g_gripWeaponHave && wi >= 0 && wi < VRIK_MAX_BONES) {\n"
     "        float* t = reinterpret_cast<float*>(boneBuf + wi * 48 + VRIK_TRANS_OFF);\n"
     "        float* q = reinterpret_cast<float*>(boneBuf + wi * 48 + VRIK_ROT_OFF);\n"
     "        for (int k = 0; k < 3; ++k) t[k] = g_gripWeaponPos[k];\n"
     "        for (int k = 0; k < 4; ++k) q[k] = g_gripWeaponRot[k];\n"
     "    }\n"
     "}\n"),
])
patch("src/Anim/ReloadPose.cpp", [
    ("float g_gripWeaponPos[3] = {}, g_gripWeaponRot[4] = {};   // [VRGestures fork] 23: WeaponRight, the gun's bone\n",
     "float g_gripWeaponPos[3] = {}, g_gripWeaponRot[4] = {}, g_gripWeaponScale[3] = {};   // [VRGestures fork] 23: WeaponRight, the gun's bone\n"),
    ("    for (int k = 0; k < 4; ++k) g_gripWeaponRot[k] = q[k];\n    g_gripWeaponHave = 1;\n",
     "    const float* s = reinterpret_cast<const float*>(boneBuf + wi * 48) + 8;   // scale: an animation hides a prop with it\n"
     "    for (int k = 0; k < 4; ++k) g_gripWeaponRot[k] = q[k];\n"
     "    for (int k = 0; k < 3; ++k) g_gripWeaponScale[k] = s[k];\n"
     "    g_gripWeaponHave = 1;\n"),
    ("        for (int k = 0; k < 4; ++k) q[k] = g_gripWeaponRot[k];\n    }\n}\n",
     "        float* s = reinterpret_cast<float*>(boneBuf + wi * 48) + 8;\n"
     "        for (int k = 0; k < 4; ++k) q[k] = g_gripWeaponRot[k];\n"
     "        for (int k = 0; k < 3; ++k) s[k] = g_gripWeaponScale[k];\n"
     "    }\n}\n"),
])
# 24. TEMPORARY: WHY THE GUN HAND'S GRIP SLIPPED. Next to the launcher the right hand still flickered now and then, and
#     once lost the gun for seconds, with nothing in the script log. The pose passes set bits for each reason the grip
#     was not held (VRGestures' word lapsed, no grip learned, no gun seen, a reload or cigarette owns the fingers) and
#     for each reason the launcher graph's arm replay was skipped; the worker thread writes them, at most five lines a
#     second, to VRGestures_grip_diag.log beside the port's other diagnostics. Read-only: nothing it does moves a bone.
patch("include/Anim/ReloadPose.hpp", [
    ("void VrgHoldGunGripRight(uint8_t* boneBuf, bool nativeCyberware);   // [VRGestures fork] 21\n",
     "void VrgHoldGunGripRight(uint8_t* boneBuf, bool nativeCyberware);   // [VRGestures fork] 21\n"
     "// [VRGestures fork] 24 TEMPORARY: the grip's misses, written by the worker thread\n"
     "bool VrgLauncherWithGunNow();\n"
     "void VrgNoteArmSkip(uint32_t why);\n"
     "void VrgGripDiagTick();\n"),
])
patch("src/Anim/ReloadPose.cpp", [
    ("int   g_gripWeaponHave = 0;\n",
     "int   g_gripWeaponHave = 0;\n"
     "// 24 TEMPORARY: bits since the worker last wrote, and how many passes held the grip\n"
     "std::atomic<uint32_t> g_vrgGripMiss{0}, g_vrgArmSkip{0}, g_vrgGripHeld{0};\n"
     "uint64_t g_vrgWithGunSeen = 0;\n"),
    ("    const bool withGun = GetTickCount64() < CyberpunkVR_LauncherWithGunUntil;\n"
     "    if (!withGun) {\n",
     "    const uint64_t now = GetTickCount64();\n"
     "    const bool withGun = now < CyberpunkVR_LauncherWithGunUntil;\n"
     "    if (withGun) g_vrgWithGunSeen = now;\n"
     "    // 24: the word lapsed while a gun and something in the left hand are still there\n"
     "    else if (g_vrgWithGunSeen && now - g_vrgWithGunSeen < 3000 && cvr::gestures::RightHandHoldsGun()\n"
     "             && !cvr::gestures::OnlyRightHandHolds()) g_vrgGripMiss.fetch_or(1);\n"
     "    if (!withGun) {\n"),
    ("    if (!g_gripHaveR || !g_hasWeaponEquipped || g_VRReloadFingerActive[1] || g_VRSmokeFingerActive) return;\n",
     "    const uint32_t miss = (g_gripHaveR ? 0u : 2u) | (g_hasWeaponEquipped ? 0u : 4u)\n"
     "        | (g_VRReloadFingerActive[1] ? 8u : 0u) | (g_VRSmokeFingerActive ? 16u : 0u) | (g_gripWeaponHave ? 0u : 32u);\n"
     "    if (miss) g_vrgGripMiss.fetch_or(miss); else g_vrgGripHeld.fetch_add(1);\n"
     "    if (!g_gripHaveR || !g_hasWeaponEquipped || g_VRReloadFingerActive[1] || g_VRSmokeFingerActive) return;\n"),
])
patch("src/Anim/ReloadPose.cpp", [
    ("// [VRGestures fork] 21: the launcher out next to a gun -- the right hand wears its own learned grip, not the launcher\n",
     "// [VRGestures fork] 24 TEMPORARY\n"
     "bool VrgLauncherWithGunNow() { return GetTickCount64() < CyberpunkVR_LauncherWithGunUntil; }\n"
     "void VrgNoteArmSkip(uint32_t why) { g_vrgArmSkip.fetch_or(why); }\n"
     "void VrgGripDiagTick() {\n"
     "    static int lines = 0;\n"
     "    const uint32_t miss = g_vrgGripMiss.exchange(0), skip = g_vrgArmSkip.exchange(0), held = g_vrgGripHeld.exchange(0);\n"
     "    if ((!miss && !skip) || lines >= 3000) return;\n"
     "    FILE* f = nullptr;\n"
     "    if (fopen_s(&f, VRDiagPath(\"VRGestures_grip_diag.log\").c_str(), lines ? \"a\" : \"w\") != 0 || !f) return;\n"
     "    SYSTEMTIME st; GetLocalTime(&st);\n"
     "    std::fprintf(f, \"%02d:%02d:%02d.%03d held=%u grip:%s%s%s%s%s%s arm-replay-skipped:%s%s%s%s%s%s\\n\",\n"
     "        st.wHour, st.wMinute, st.wSecond, st.wMilliseconds, held,\n"
     "        (miss & 1) ? \" word-lapsed\" : \"\", (miss & 2) ? \" no-grip-learned\" : \"\", (miss & 4) ? \" no-gun-seen\" : \"\",\n"
     "        (miss & 8) ? \" reload\" : \"\", (miss & 16) ? \" cigarette\" : \"\", (miss & 32) ? \" no-gun-bone-learned\" : \"\",\n"
     "        (skip & 1) ? \" no-solve-model\" : \"\", (skip & 2) ? \" no-solve\" : \"\", (skip & 4) ? \" head-aim\" : \"\",\n"
     "        (skip & 8) ? \" suspended\" : \"\", (skip & 16) ? \" device-camera\" : \"\", (skip & 32) ? \" ladder\" : \"\");\n"
     "    std::fclose(f);\n"
     "    ++lines;\n"
     "}\n\n"
     "// [VRGestures fork] 21: the launcher out next to a gun -- the right hand wears its own learned grip, not the launcher\n"),
])
patch("src/Hooks/AnimPose.cpp", [
    ("                        cvr::anim::VrgHoldGunGripRight(boneBuf,true);\n",
     "                        cvr::anim::VrgHoldGunGripRight(boneBuf,true);\n"
     "                        if(cvr::anim::VrgLauncherWithGunNow())   // [VRGestures fork] 24 TEMPORARY: why the arm replay is skipped\n"
     "                            cvr::anim::VrgNoteArmSkip((g_solveCacheModel?0u:1u)|(g_solveCacheN>0?0u:2u)|(headAimWork?4u:0u)|\n"
     "                                (suspended?8u:0u)|(DeviceCamActive()?16u:0u)|(cvr::ladder::Active()?32u:0u));\n"),
])
patch("src/Core/WorkerThread.cpp", [
    ("        cvr::anim::RestFingerRightTick();\n",
     "        cvr::anim::RestFingerRightTick();\n"
     "        cvr::anim::VrgGripDiagTick();   // [VRGestures fork] 24 TEMPORARY\n"),
])
# 25. LAUNCHER WITH A GUN THROUGH WEAPON CHANGES. (a) Drawing a right-hand weapon rebuilt the left hand from that
#     weapon's dual-wield partner (TryGetSecondaryItemID), which dropped the launcher; a one-handed weapon now keeps it
#     there (a two-handed one still takes it away, as VRGestures will not bring it out beside one). (b) The cancel input
#     also closed it during a weapon switch; with a gun in hand it no longer does. (c) A launcher held in its equip
#     state that can no longer stay (it was asked for as Gorilla Arms arrived) hung there for good, out of reach of every
#     request; 1.5 s past its draw it now backs out.
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_launcher_selection.reds", [
    ("// [VRGestures fork] 17: the launcher is not a weapon-cycle slot; VRGestures brings it out as left-hand cyberware.\n",
     "// [VRGestures fork] 25: a right-hand weapon the launcher may stay beside -- the game's one-handed guns and the one-handed\n"
     "// melee types (VRGestures asks the same before bringing it out)\n"
     "public func VrgOneHandedItem(item: ItemID) -> Bool {\n"
     "  if WeaponObject.IsOneHandedRanged(item) { return true; };\n"
     "  let rec = TweakDBInterface.GetWeaponItemRecord(ItemID.GetTDBID(item));\n"
     "  if !IsDefined(rec) { return false; };\n"
     "  let type = rec.ItemType().Type();\n"
     "  return Equals(type, gamedataItemType.Wea_Knife) || Equals(type, gamedataItemType.Wea_ShortBlade)\n"
     "    || Equals(type, gamedataItemType.Wea_Machete) || Equals(type, gamedataItemType.Wea_OneHandedClub);\n"
     "}\n\n"
     "// [VRGestures fork] 17: the launcher is not a weapon-cycle slot; VRGestures brings it out as left-hand cyberware.\n"),
    ("    state = wrappedMethod(action, currentState);\n"
     "    item = Equals(action, EquipmentManipulationAction.RequestLeftHandCyberware) || !ItemID.IsValid(state.rightHandItem)\n",
     "    state = wrappedMethod(action, currentState);\n"
     "    // [VRGestures fork] 25: launcher with a gun -- a one-handed weapon drawn into the right hand keeps the launcher\n"
     "    if IsDefined(player) && VrgWithGunMode(player) && !this.IsEquipmentManipulationAnUnequipRequest(action)\n"
     "        && !ItemID.IsValid(state.leftHandItem) && ItemID.IsValid(currentState.leftHandItem)\n"
     "        && WeaponObject.IsOfType(currentState.leftHandItem, gamedataItemType.Cyb_Launcher)\n"
     "        && ItemID.IsValid(state.rightHandItem) && VrgOneHandedItem(state.rightHandItem) {\n"
     "      state.leftHandItem = currentState.leftHandItem;\n"
     "    };\n"
     "    item = Equals(action, EquipmentManipulationAction.RequestLeftHandCyberware) || !ItemID.IsValid(state.rightHandItem)\n"),
    ("  if player.vrLauncherFromWeaponCycle && !player.vrLauncherSelectedAsWeapon { return true; };\n"
     "  return wrappedMethod(stateContext, scriptInterface);\n",
     "  if player.vrLauncherFromWeaponCycle && !player.vrLauncherSelectedAsWeapon { return true; };\n"
     "  // [VRGestures fork] 25: never held in the equip state by a launcher that can no longer stay\n"
     "  if player.vrLauncherSelectedAsWeapon && this.GetInStateTime() >= this.GetEquipDuration(scriptInterface) + 1.50\n"
     "      && !this.VrLauncherCanStay(stateContext, scriptInterface) {\n"
     "    player.vrforkWhy = \"stuck in equip <- \" + player.vrforkWhy;\n"
     "    return true;\n"
     "  };\n"
     "  return wrappedMethod(stateContext, scriptInterface);\n"),
])
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_cyberware.reds", [
    ("  if this.GetCancelChargeButtonInput(scriptInterface) { player.vrforkWhy = \"stay: cancel button\"; return false; };\n",
     "  // [VRGestures fork] 25: with a gun in the right hand the cancel input is the weapon switch's, not the launcher's\n"
     "  if this.GetCancelChargeButtonInput(scriptInterface) && !VrLauncherWithGun(scriptInterface) { player.vrforkWhy = \"stay: cancel button\"; return false; };\n"),
])
# 26. THE GRIP'S GUN, SEEN FROM THE HAND SLOTS. Patch 24's log: with the launcher out beside a pistol the port's
#     g_hasWeaponEquipped (the player's equipped-weapon property) read empty for tens of seconds at a time, and the grip
#     was not held then -- the flicker. The replay now asks the hand slots (RightHandHoldsGun, the equipment mask the
#     port's weapon script publishes every frame), which saw the pistol throughout.
patch("src/Anim/ReloadPose.cpp", [
    ("    const uint32_t miss = (g_gripHaveR ? 0u : 2u) | (g_hasWeaponEquipped ? 0u : 4u)\n",
     "    const bool gunInHand = cvr::gestures::RightHandHoldsGun();   // 26: not g_hasWeaponEquipped, which drops out here\n"
     "    const uint32_t miss = (g_gripHaveR ? 0u : 2u) | (gunInHand ? 0u : 4u)\n"),
    ("    if (miss) g_vrgGripMiss.fetch_or(miss); else g_vrgGripHeld.fetch_add(1);\n"
     "    if (!g_gripHaveR || !g_hasWeaponEquipped || g_VRReloadFingerActive[1] || g_VRSmokeFingerActive) return;\n",
     "    if (miss) g_vrgGripMiss.fetch_or(miss); else g_vrgGripHeld.fetch_add(1);\n"
     "    if (!g_gripHaveR || !gunInHand || g_VRReloadFingerActive[1] || g_VRSmokeFingerActive) return;\n"),
])
# 27. THE GUN BESIDE THE LAUNCHER, IN VRGESTURES' OWN WORD. The patch 24/26 log: with the launcher out beside a pistol the
#     port's hand-slot mask (RightHandHoldsGun) read "no gun" for many seconds at a time, like g_hasWeaponEquipped before
#     it. The trigger merge (16) and the grip replay (21-23) both waited on it: the left trigger reached the launcher only
#     once it came back (the delayed shot), and the grip let go meanwhile (the flicker). VRGestures, which reads the right
#     weapon slot itself, now says so: SetVRLauncherWithGun(2) = out with a gun in the right hand; the mask stays a
#     fallback.
patch("src/Natives/OrientationProvider.cpp", [
    ("extern \"C\" __declspec(dllexport) volatile uint64_t CyberpunkVR_LauncherWithGunUntil = 0;\n",
     "extern \"C\" __declspec(dllexport) volatile uint64_t CyberpunkVR_LauncherWithGunUntil = 0;\n"
     "extern \"C\" __declspec(dllexport) volatile uint64_t CyberpunkVR_LauncherGunInHandUntil = 0;   // 27: and a gun beside it\n"),
    ("    CyberpunkVR_LauncherWithGunUntil = on ? GetTickCount64() + 500 : 0;   // 16: refreshed every frame the launcher is out\n",
     "    CyberpunkVR_LauncherWithGunUntil = on ? GetTickCount64() + 500 : 0;   // 16: refreshed every frame the launcher is out\n"
     "    CyberpunkVR_LauncherGunInHandUntil = on == 2 ? GetTickCount64() + 500 : 0;   // 27: 2 = with a gun in the right hand\n"),
])
patch("src/Hooks/XInput.cpp", [
    ("extern \"C\" volatile uint64_t CyberpunkVR_LauncherWithGunUntil;   // [VRGestures fork] Natives/OrientationProvider.cpp\n",
     "extern \"C\" volatile uint64_t CyberpunkVR_LauncherWithGunUntil;   // [VRGestures fork] Natives/OrientationProvider.cpp\n"
     "extern \"C\" volatile uint64_t CyberpunkVR_LauncherGunInHandUntil;   // [VRGestures fork] 27\n"),
    ("    const bool launcherWithGun=GetTickCount64()<CyberpunkVR_LauncherWithGunUntil &&   // [VRGestures fork] 16: VRGestures' word\n"
     "        cvr::gestures::RightHandHoldsGun();\n",
     "    const bool launcherWithGun=GetTickCount64()<CyberpunkVR_LauncherGunInHandUntil ||   // [VRGestures fork] 27: its word, gun included\n"
     "        (GetTickCount64()<CyberpunkVR_LauncherWithGunUntil && cvr::gestures::RightHandHoldsGun());   // 16\n"),
])
patch("src/Anim/ReloadPose.cpp", [
    ("extern \"C\" volatile uint64_t CyberpunkVR_LauncherWithGunUntil;   // [VRGestures fork] 21: Natives/OrientationProvider.cpp\n",
     "extern \"C\" volatile uint64_t CyberpunkVR_LauncherWithGunUntil;   // [VRGestures fork] 21: Natives/OrientationProvider.cpp\n"
     "extern \"C\" volatile uint64_t CyberpunkVR_LauncherGunInHandUntil;   // [VRGestures fork] 27\n"),
    ("    const bool gunInHand = cvr::gestures::RightHandHoldsGun();   // 26: not g_hasWeaponEquipped, which drops out here\n",
     "    const bool gunInHand = now < CyberpunkVR_LauncherGunInHandUntil   // 27: VRGestures' word\n"
     "        || cvr::gestures::RightHandHoldsGun();                      // 26: not g_hasWeaponEquipped, which drops out here\n"),
])
# 28. TEMPORARY: THE LAST EQUIP REQUEST, FOR VRGESTURES' LOG. With the launcher out a holster draw (RequestWeaponSlot1)
#     equipped nothing while the weapon cycle did; every request the equipment system handles is recorded with the hand
#     items before and after it, and VrgLauncherState() reports the last one.
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_cyberware.reds", [
    ("@addField(PlayerPuppet) public let vrforkWhy: String;\n",
     "@addField(PlayerPuppet) public let vrforkWhy: String;\n"
     "@addField(PlayerPuppet) public let vrforkLastReq: String;   // 28 TEMPORARY\n"
     "public func VrforkItem(item: ItemID) -> String {\n"
     "  return ItemID.IsValid(item) ? TDBID.ToStringDEBUG(ItemID.GetTDBID(item)) : \"none\";\n"
     "}\n"),
    ("    + \" ctrlAim=\" + VrforkBit(VRLauncherControllerAim()) + \" why=\" + this.vrforkWhy;\n",
     "    + \" ctrlAim=\" + VrforkBit(VRLauncherControllerAim()) + \" why=\" + this.vrforkWhy + \" req=\" + this.vrforkLastReq;\n"),
    ("  wrappedMethod(request);\n",
     "  let beforeR = this.GetSlotActiveItem(EquipmentManipulationRequestSlot.Right);   // 28 TEMPORARY\n"
     "  let beforeL = this.GetSlotActiveItem(EquipmentManipulationRequestSlot.Left);\n"
     "  wrappedMethod(request);\n"
     "  if IsDefined(player) {\n"
     "    player.vrforkLastReq = IntToString(EnumInt(request.requestType)) + \" [\" + VrforkItem(beforeR) + \" | \" + VrforkItem(beforeL)\n"
     "      + \"] -> [\" + VrforkItem(this.GetSlotActiveItem(EquipmentManipulationRequestSlot.Right)) + \" | \"\n"
     "      + VrforkItem(this.GetSlotActiveItem(EquipmentManipulationRequestSlot.Left)) + \"]\";\n"
     "  };\n"),
])
# 29. A HOLSTER DRAW BESIDE THE LAUNCHER. The patch 28 log: with the launcher out a holster draw (RequestWeaponSlot1) was
#     accepted by the equipment system (right hand -> the pistol) and never reached the hand. The right hand's equipment
#     state machine will not equip while the other hand's weapon is arm cyberware (CanEquipRequestedWeapon: ArmsCW), so
#     it waited for good; the weapon cycle got through only because its switch puts the hand away first. With the
#     launcher-with-a-gun mode on, a one-handed weapon may come into the right hand beside the launcher.
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_launcher_selection.reds", [
    ("// [VRGestures fork] 17: the launcher is not a weapon-cycle slot; VRGestures brings it out as left-hand cyberware.\n",
     "// [VRGestures fork] 29: the right hand may equip a one-handed weapon beside the launcher (the launcher is arm cyberware,\n"
     "// which otherwise holds a right-hand equip back until it is gone)\n"
     "@wrapMethod(EquipmentBaseTransition)\n"
     "protected final const func CanEquipRequestedWeapon(const scriptInterface: ref<StateGameScriptInterface>, stateContext: ref<StateContext>, stateMachineInstanceData: StateMachineInstanceData) -> Bool {\n"
     "  if wrappedMethod(scriptInterface, stateContext, stateMachineInstanceData) { return true; };\n"
     "  if !VrgWithGunMode(scriptInterface.executionOwner as PlayerPuppet) || !this.IsRightHandLogic(stateMachineInstanceData) { return false; };\n"
     "  let left = ScriptedPuppet.GetLeftActiveWeapon(scriptInterface.executionOwner);\n"
     "  if !IsDefined(left) || !WeaponObject.IsOfType(left.GetItemID(), gamedataItemType.Cyb_Launcher) { return false; };\n"
     "  let item = this.GetSlotActiveItem(scriptInterface, stateMachineInstanceData);\n"
     "  return ItemID.IsValid(item) && VrgOneHandedItem(item) && this.CanProcessEquip(stateContext, scriptInterface);\n"
     "}\n\n"
     "// [VRGestures fork] 17: the launcher is not a weapon-cycle slot; VRGestures brings it out as left-hand cyberware.\n"),
])
# 30. THE TEMPORARY DIAGNOSTICS COME OUT. Patch 24's grip log (VRGestures_grip_diag.log, its bits in the pose passes and
#     the worker's writer) and patch 28's equip-request record did their job: 26, 27 and 29 came out of them. Patch 19's
#     VrgLauncherState() stays, for a look from the CET console; it costs nothing unless it is called.
patch("include/Anim/ReloadPose.hpp", [
    ("// [VRGestures fork] 24 TEMPORARY: the grip's misses, written by the worker thread\n"
     "bool VrgLauncherWithGunNow();\n"
     "void VrgNoteArmSkip(uint32_t why);\n"
     "void VrgGripDiagTick();\n", ""),
])
patch("src/Anim/ReloadPose.cpp", [
    ("// 24 TEMPORARY: bits since the worker last wrote, and how many passes held the grip\n"
     "std::atomic<uint32_t> g_vrgGripMiss{0}, g_vrgArmSkip{0}, g_vrgGripHeld{0};\n"
     "uint64_t g_vrgWithGunSeen = 0;\n", ""),
    ("// [VRGestures fork] 24 TEMPORARY\n"
     "bool VrgLauncherWithGunNow() { return GetTickCount64() < CyberpunkVR_LauncherWithGunUntil; }\n"
     "void VrgNoteArmSkip(uint32_t why) { g_vrgArmSkip.fetch_or(why); }\n"
     "void VrgGripDiagTick() {\n"
     "    static int lines = 0;\n"
     "    const uint32_t miss = g_vrgGripMiss.exchange(0), skip = g_vrgArmSkip.exchange(0), held = g_vrgGripHeld.exchange(0);\n"
     "    if ((!miss && !skip) || lines >= 3000) return;\n"
     "    FILE* f = nullptr;\n"
     "    if (fopen_s(&f, VRDiagPath(\"VRGestures_grip_diag.log\").c_str(), lines ? \"a\" : \"w\") != 0 || !f) return;\n"
     "    SYSTEMTIME st; GetLocalTime(&st);\n"
     "    std::fprintf(f, \"%02d:%02d:%02d.%03d held=%u grip:%s%s%s%s%s%s arm-replay-skipped:%s%s%s%s%s%s\\n\",\n"
     "        st.wHour, st.wMinute, st.wSecond, st.wMilliseconds, held,\n"
     "        (miss & 1) ? \" word-lapsed\" : \"\", (miss & 2) ? \" no-grip-learned\" : \"\", (miss & 4) ? \" no-gun-seen\" : \"\",\n"
     "        (miss & 8) ? \" reload\" : \"\", (miss & 16) ? \" cigarette\" : \"\", (miss & 32) ? \" no-gun-bone-learned\" : \"\",\n"
     "        (skip & 1) ? \" no-solve-model\" : \"\", (skip & 2) ? \" no-solve\" : \"\", (skip & 4) ? \" head-aim\" : \"\",\n"
     "        (skip & 8) ? \" suspended\" : \"\", (skip & 16) ? \" device-camera\" : \"\", (skip & 32) ? \" ladder\" : \"\");\n"
     "    std::fclose(f);\n"
     "    ++lines;\n"
     "}\n\n", ""),
    ("    if (withGun) g_vrgWithGunSeen = now;\n"
     "    // 24: the word lapsed while a gun and something in the left hand are still there\n"
     "    else if (g_vrgWithGunSeen && now - g_vrgWithGunSeen < 3000 && cvr::gestures::RightHandHoldsGun()\n"
     "             && !cvr::gestures::OnlyRightHandHolds()) g_vrgGripMiss.fetch_or(1);\n", ""),
    ("    const uint32_t miss = (g_gripHaveR ? 0u : 2u) | (gunInHand ? 0u : 4u)\n"
     "        | (g_VRReloadFingerActive[1] ? 8u : 0u) | (g_VRSmokeFingerActive ? 16u : 0u) | (g_gripWeaponHave ? 0u : 32u);\n"
     "    if (miss) g_vrgGripMiss.fetch_or(miss); else g_vrgGripHeld.fetch_add(1);\n", ""),
])
patch("src/Hooks/AnimPose.cpp", [
    ("                        if(cvr::anim::VrgLauncherWithGunNow())   // [VRGestures fork] 24 TEMPORARY: why the arm replay is skipped\n"
     "                            cvr::anim::VrgNoteArmSkip((g_solveCacheModel?0u:1u)|(g_solveCacheN>0?0u:2u)|(headAimWork?4u:0u)|\n"
     "                                (suspended?8u:0u)|(DeviceCamActive()?16u:0u)|(cvr::ladder::Active()?32u:0u));\n", ""),
])
patch("src/Core/WorkerThread.cpp", [
    ("        cvr::anim::VrgGripDiagTick();   // [VRGestures fork] 24 TEMPORARY\n", ""),
])
patch("mods/redscript/CyberpunkVRPort_Cyberware/vrport_cyberware.reds", [
    ("@addField(PlayerPuppet) public let vrforkLastReq: String;   // 28 TEMPORARY\n"
     "public func VrforkItem(item: ItemID) -> String {\n"
     "  return ItemID.IsValid(item) ? TDBID.ToStringDEBUG(ItemID.GetTDBID(item)) : \"none\";\n"
     "}\n", ""),
    (" + \" why=\" + this.vrforkWhy + \" req=\" + this.vrforkLastReq;\n", " + \" why=\" + this.vrforkWhy;\n"),
    ("  let beforeR = this.GetSlotActiveItem(EquipmentManipulationRequestSlot.Right);   // 28 TEMPORARY\n"
     "  let beforeL = this.GetSlotActiveItem(EquipmentManipulationRequestSlot.Left);\n"
     "  wrappedMethod(request);\n"
     "  if IsDefined(player) {\n"
     "    player.vrforkLastReq = IntToString(EnumInt(request.requestType)) + \" [\" + VrforkItem(beforeR) + \" | \" + VrforkItem(beforeL)\n"
     "      + \"] -> [\" + VrforkItem(this.GetSlotActiveItem(EquipmentManipulationRequestSlot.Right)) + \" | \"\n"
     "      + VrforkItem(this.GetSlotActiveItem(EquipmentManipulationRequestSlot.Left)) + \"]\";\n"
     "  };\n",
     "  wrappedMethod(request);\n"),
])
# 31. (0.2.0: dropped -- upstream took the per-eye world-marker log line out itself.)

# 32. TWO QUICK TAPS OF X ARE THE QUICK EXIT. Leaving a car was a 400 ms hold of X only (the port's guard against an
#     ejection on a brushed button), so the game's quick exit -- QuickExit, a fresh press of ExitVehicle_Button that
#     throws the player out of a moving car (VehicleEventsTransition.HandleExitRequest) -- could not be reached quickly.
#     Two taps of X inside 350 ms now hold B for 350 ms: a moving car takes the press as QuickExit, a stopped one the
#     held 0.3 s as the ordinary exit. One stray tap still does nothing.
patch("src/Hooks/XInput.cpp", [
    ("        if(exitHold.Update(vehicleButtons.exitOnX && gameplayScreen,(vr.buttons&0x4000)!=0,GetTickCount64(),need))\n"
     "            synthButtons |= 0x2000;   // XINPUT_GAMEPAD_B = ExitVehicle_Button\n"
     "    }\n",
     "        if(exitHold.Update(vehicleButtons.exitOnX && gameplayScreen,(vr.buttons&0x4000)!=0,GetTickCount64(),need))\n"
     "            synthButtons |= 0x2000;   // XINPUT_GAMEPAD_B = ExitVehicle_Button\n"
     "    }\n"
     "    // [VRGestures fork] 32: two quick taps of X = the quick exit (a 350 ms B press)\n"
     "    {\n"
     "        static uint64_t s_downAt = 0, s_tapUpAt = 0, s_pulseUntil = 0;\n"
     "        static bool s_down = false;\n"
     "        const uint64_t now = GetTickCount64();\n"
     "        const bool allowed = vehicleButtons.exitOnX && gameplayScreen;\n"
     "        const bool x = allowed && (vr.buttons & 0x4000) != 0;\n"
     "        if (x && !s_down) {\n"
     "            s_downAt = now;\n"
     "            if (s_tapUpAt != 0 && now - s_tapUpAt <= 350) { s_pulseUntil = now + 350; s_tapUpAt = 0; }\n"
     "        } else if (!x && s_down) {\n"
     "            s_tapUpAt = (now - s_downAt <= 250) ? now : 0;   // a tap, not the end of a hold\n"
     "        }\n"
     "        s_down = x;\n"
     "        if (!allowed) { s_tapUpAt = 0; s_pulseUntil = 0; }\n"
     "        if (now < s_pulseUntil) synthButtons |= 0x2000;\n"
     "    }\n"),
])
# 33. THE LEFT STICK CLICK SPRINTS AGAIN. The port sprinted only on a full-forward push held 200 ms, and the click itself
#     reached the game as a one-frame L3 on release (it doubles as the D-pad chord), which the game's sprint ignores.
#     A press of the left stick now starts a sprint at once: the port holds L3 through its own sprint machinery while
#     the stick is moving, until the stick comes back to centre (or nothing moves within 1.5 s of the click). A click that
#     becomes a D-pad, cyberware or menu chord is not a sprint. The full-forward gesture is off while this is on
#     (CyberpunkVR_SprintOnStickClick = 0 puts it back). Shared slot 240 is up while the port holds L3 for this, so
#     VRGestures does not count those presses as clicks (its L3 double-click is the launcher).
patch("src/Hooks/XInput.cpp", [
    ("extern \"C\" __declspec(dllexport) int32_t CyberpunkVR_VehicleExitHoldMs = 400;\n",
     "extern \"C\" __declspec(dllexport) int32_t CyberpunkVR_VehicleExitHoldMs = 400;\n"
     "// [VRGestures fork] 33: 1 = a left stick click starts the sprint (the full-forward gesture is off); 0 = the old gesture\n"
     "extern \"C\" __declspec(dllexport) int32_t CyberpunkVR_SprintOnStickClick = 1;\n"
     "std::atomic<int> g_vrgSprintClick{0};   // set by the XR frame loop on a stick click that is not a chord\n"),
    ("        const bool detent = fullForward && !g_isInVehicle && !crouchBlocks;\n"
     "        if (detent) s_detentMs += dtMs; else s_detentMs = 0.0;\n"
     "        const double holdMs = (CyberpunkVR_SprintHoldMs >= 0) ? CyberpunkVR_SprintHoldMs : 200;\n"
     "        const bool want = detent && (s_detentMs >= holdMs);\n",
     "        bool detent = fullForward && !g_isInVehicle && !crouchBlocks;\n"
     "        // [VRGestures fork] 33: the click is the sprint; it lasts while the stick moves\n"
     "        bool clickSprint = false;\n"
     "        if (CyberpunkVR_SprintOnStickClick != 0) {\n"
     "            static bool s_clickMoved = false;\n"
     "            static double s_clickIdleMs = 0.0;\n"
     "            const float mag = std::sqrt(vr.leftThumbX * vr.leftThumbX + vr.leftThumbY * vr.leftThumbY);\n"
     "            if (g_vrgSprintClick.load(std::memory_order_relaxed) != 0) {\n"
     "                if (mag > 0.30f) { s_clickMoved = true; s_clickIdleMs = 0.0; } else { s_clickIdleMs += dtMs; }\n"
     "                const bool stopped = s_clickMoved ? (mag < 0.20f) : (s_clickIdleMs > 1500.0);\n"
     "                if (g_isInVehicle || stopped) {\n"
     "                    g_vrgSprintClick.store(0, std::memory_order_relaxed);\n"
     "                    s_clickMoved = false; s_clickIdleMs = 0.0;\n"
     "                } else {\n"
     "                    clickSprint = mag > 0.30f && !crouchBlocks;\n"
     "                }\n"
     "            } else {\n"
     "                s_clickMoved = false; s_clickIdleMs = 0.0;\n"
     "            }\n"
     "            detent = false;\n"
     "        }\n"
     "        OpenXRManager::Get().SetSharedSlot(240, clickSprint ? 1.0f : 0.0f);\n"
     "        if (detent) s_detentMs += dtMs; else s_detentMs = 0.0;\n"
     "        const double holdMs = (CyberpunkVR_SprintHoldMs >= 0) ? CyberpunkVR_SprintHoldMs : 200;\n"
     "        const bool want = clickSprint || (detent && (s_detentMs >= holdMs));\n"),
])
patch("src/Runtimes/OpenXRFrameLoop.cpp", [
    ("extern float BodyYawFollowOffset();\n",
     "extern float BodyYawFollowOffset();\n"
     "extern std::atomic<int> g_vrgSprintClick;   // [VRGestures fork] 33: Hooks/XInput.cpp\n"),
    ("                    if (leftStickClicked) {\n"
     "                        if (dpadUsedThisFrame) s_l3UsedForDpad = true;\n"
     "                        s_l3Held = true;\n",
     "                    if (leftStickClicked) {\n"
     "                        if (dpadUsedThisFrame) s_l3UsedForDpad = true;\n"
     "                        // [VRGestures fork] 33: the press is a sprint, unless the hold turns into a chord\n"
     "                        if (!s_l3Held) g_vrgSprintClick.store(1, std::memory_order_relaxed);\n"
     "                        if (s_l3UsedForDpad) g_vrgSprintClick.store(0, std::memory_order_relaxed);\n"
     "                        s_l3Held = true;\n"),
])
# 34. A SCRIPTED D-PAD PRESS. VRGPadPress(buttons, ms) holds D-pad bits (0x000F: up, down, left, right) down for ms
#     milliseconds, merged like the controllers' own buttons. VRGestures' hand-to-mouth heal presses D-pad up, which
#     is the game's UseConsumable_Button -- the same press the D-pad chord gives, without the chord.
patch("src/Natives/OrientationProvider.cpp", [
    ("void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n",
     "// [VRGestures fork] 34: a D-pad press from script (bits 0x000F only), held until the deadline\n"
     "extern \"C\" __declspec(dllexport) volatile uint64_t CyberpunkVR_PadPressUntil = 0;\n"
     "extern \"C\" __declspec(dllexport) volatile int32_t CyberpunkVR_PadPressButtons = 0;\n"
     "void VRGPadPress(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t) {\n"
     "    int32_t buttons = 0, ms = 0;\n"
     "    RED4ext::GetParameter(aFrame, &buttons);\n"
     "    RED4ext::GetParameter(aFrame, &ms);\n"
     "    aFrame->code++;\n"
     "    CyberpunkVR_PadPressButtons = buttons & 0x000F;\n"
     "    CyberpunkVR_PadPressUntil = GetTickCount64() + static_cast<uint64_t>(ms > 0 ? (ms < 1000 ? ms : 1000) : 0);\n"
     "}\n\n"
     "void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n"),
])
patch("include/Natives/NativeFunctions.hpp", [
    ("void SetVRLauncherWithGun(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork]\n",
     "void SetVRLauncherWithGun(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork]\n"
     "void VRGPadPress(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork] 34\n"),
])
patch("src/Natives/Registration.cpp", [
    ("    fLauncherGun->flags = flags; fLauncherGun->AddParam(\"Int32\", \"on\"); rtti->RegisterFunction(fLauncherGun);\n",
     "    fLauncherGun->flags = flags; fLauncherGun->AddParam(\"Int32\", \"on\"); rtti->RegisterFunction(fLauncherGun);\n"
     "    // [VRGestures fork] 34: a D-pad press from script\n"
     "    auto fPadPress = RED4ext::CGlobalFunction::Create(\"VRGPadPress\", \"VRGPadPress\", &VRGPadPress);\n"
     "    fPadPress->flags = flags; fPadPress->AddParam(\"Int32\", \"buttons\"); fPadPress->AddParam(\"Int32\", \"ms\");\n"
     "    rtti->RegisterFunction(fPadPress);\n"),
])
patch("src/Hooks/XInput.cpp", [
    ("extern \"C\" __declspec(dllexport) volatile int32_t CyberpunkVR_TestPadButtons = 0;\n",
     "extern \"C\" __declspec(dllexport) volatile int32_t CyberpunkVR_TestPadButtons = 0;\n"
     "extern \"C\" volatile uint64_t CyberpunkVR_PadPressUntil;    // [VRGestures fork] 34: Natives/OrientationProvider.cpp\n"
     "extern \"C\" volatile int32_t CyberpunkVR_PadPressButtons;\n"),
    ("    if (CyberpunkVR_TestPadButtons & 0x20000) vr.rightGrip = 1.f;\n",
     "    if (CyberpunkVR_TestPadButtons & 0x20000) vr.rightGrip = 1.f;\n"
     "    if (GetTickCount64() < CyberpunkVR_PadPressUntil)   // [VRGestures fork] 34: a scripted D-pad press\n"
     "        vr.buttons |= static_cast<uint16_t>(CyberpunkVR_PadPressButtons & 0x000F);\n"),
])
# 35. A SMALLER SCANNER ZONE. The left-ear zone that opens the scanner on a left-grip squeeze was 22 cm around a point
#     below and outside the ear (26 cm once armed), which reached the brow and the mouth: squeezes meant for other
#     gestures there opened the scanner. 15 cm keeps the hand-over-the-ear squeeze and leaves the face to VRGestures.
patch("src/Hooks/XInput.cpp", [
    ("extern \"C\" __declspec(dllexport) float CyberpunkVR_ScannerEarRadius = 0.22f;\n",
     "extern \"C\" __declspec(dllexport) float CyberpunkVR_ScannerEarRadius = 0.15f;   // [VRGestures fork] 35: was 0.22\n"),
])
# 36. THE MENU SWIPE, FOR THE LEFT HAND. VRGLeftSwipe() is VRMenuGesture's swipe read on the left hand -- the same
#     tracking-space history, drop (20 cm), window (0.4 s), speed (0.75 m/s), slant and cooldown -- for VRGestures'
#     quickslot wheel, which felt wrong with its own head-relative test. One addition: the right hand must not have
#     dropped 10 cm with it, since a two-handed gun lowered by both hands (the left one gripping) is not a swipe.
#     Returns (1, 0, 0, 0) once per swipe, empty otherwise.
patch("src/Natives/VrMenu.cpp", [
    ("// VRMenuPointer(center, right, up, size) -> array<Vector4>, the menu plane given in the world (unit\n",
     "// [VRGestures fork] 36: VRGLeftSwipe() -> array<Vector4>: (1, 0, 0, 0) once per left-hand swipe, else empty\n"
     "namespace {\n"
     "// 0.2.0 took out the menu swipe these came from: its 0.1.9 values\n"
     "constexpr float kDrop = 0.20f;\n"
     "constexpr double kWindow = 0.40;\n"
     "constexpr float kSpeed = 0.75f;\n"
     "constexpr float kSlant = 0.65f;\n"
     "constexpr double kCooldown = 0.9;\n"
     "struct LeftSample { double t; float p[3]; float rightY; bool held; };\n"
     "std::deque<LeftSample> g_leftHistory;\n"
     "uint64_t g_leftSequence = 0;\n"
     "double g_leftFire = -10.0;\n"
     "}\n"
     "void VRGLeftSwipe(RED4ext::IScriptable*, RED4ext::CStackFrame* stack, RED4ext::DynArray<RED4ext::Vector4>* out, int64_t) {\n"
     "    stack->code++;\n"
     "    if (!out) return;\n"
     "    out->Clear();\n"
     "    OpenXRHeadPose head{}, hands[2]{};\n"
     "    uint64_t sequence{}, stamp{};\n"
     "    VRControllerState input{};\n"
     "    auto& xr = OpenXRManager::Get();\n"
     "    if (!xr.GetGestureHandFrame(&head, hands, &sequence, &stamp, false) || !hands[0].valid ||\n"
     "        !xr.GetControllerState(&input) || !input.leftHandValid) {\n"
     "        g_leftHistory.clear();\n"
     "        return;\n"
     "    }\n"
     "    if (sequence == g_leftSequence) return;\n"
     "    g_leftSequence = sequence;\n"
     "    const float headQ[4] = {head.oriX, head.oriY, head.oriZ, head.oriW};\n"
     "    const float local[3] = {hands[0].posX, hands[0].posY, hands[0].posZ};\n"
     "    float p[3];\n"
     "    VRIK_QuatRotateVec(headQ, local, p);\n"
     "    float rightY = 0.0f;\n"
     "    if (hands[1].valid) {\n"
     "        const float rl[3] = {hands[1].posX, hands[1].posY, hands[1].posZ};\n"
     "        float rp[3];\n"
     "        VRIK_QuatRotateVec(headQ, rl, rp);\n"
     "        rightY = rp[1] + head.posY;\n"
     "    }\n"
     "    const double t = double(stamp) * 1e-6;\n"
     "    g_leftHistory.push_back({t, {p[0] + head.posX, p[1] + head.posY, p[2] + head.posZ}, rightY,\n"
     "                             input.leftGrip > 0.70f});\n"
     "    while (!g_leftHistory.empty() && t - g_leftHistory.front().t > 0.6) g_leftHistory.pop_front();\n"
     "    if (t - g_leftFire < kCooldown || g_leftHistory.size() < 3 || !g_leftHistory.back().held) return;\n"
     "    const LeftSample& end = g_leftHistory.back();\n"
     "    bool found = false;\n"
     "    for (auto it = g_leftHistory.rbegin(); it != g_leftHistory.rend(); ++it) {\n"
     "        if (end.t - it->t > kWindow || !it->held) break;\n"
     "        const float drop = it->p[1] - end.p[1];\n"
     "        const float dx = it->p[0] - end.p[0], dz = it->p[2] - end.p[2];\n"
     "        if (drop >= kDrop && std::sqrt(dx * dx + dz * dz) <= kSlant * drop && drop / float(end.t - it->t) >= kSpeed\n"
     "            && it->rightY - end.rightY < 0.10f)\n"
     "            found = true;\n"
     "    }\n"
     "    if (!found) return;\n"
     "    g_leftFire = t;\n"
     "    out->PushBack({1.0f, 0.0f, 0.0f, 0.0f});\n"
     "    g_leftHistory.clear();\n"
     "}\n\n"
     "// VRMenuPointer(center, right, up, size) -> array<Vector4>, the menu plane given in the world (unit\n"),
])
patch("include/Natives/NativeFunctions.hpp", [
    ("void VRMenuGesture(RED4ext::IScriptable*,RED4ext::CStackFrame*,RED4ext::DynArray<RED4ext::Vector4>*,int64_t);\n",
     "void VRMenuGesture(RED4ext::IScriptable*,RED4ext::CStackFrame*,RED4ext::DynArray<RED4ext::Vector4>*,int64_t);\n"
     "void VRGLeftSwipe(RED4ext::IScriptable*,RED4ext::CStackFrame*,RED4ext::DynArray<RED4ext::Vector4>*,int64_t);   // [VRGestures fork] 36\n"),
])
patch("src/Natives/Registration.cpp", [
    ("    menuGesture->flags=flags;menuGesture->SetReturnType(\"array:Vector4\");rtti->RegisterFunction(menuGesture);\n",
     "    menuGesture->flags=flags;menuGesture->SetReturnType(\"array:Vector4\");rtti->RegisterFunction(menuGesture);\n"
     "    auto leftSwipe=RED4ext::CGlobalFunction::Create(\"VRGLeftSwipe\",\"VRGLeftSwipe\",&VRGLeftSwipe);   // [VRGestures fork] 36\n"
     "    leftSwipe->flags=flags;leftSwipe->SetReturnType(\"array:Vector4\");rtti->RegisterFunction(leftSwipe);\n"),
])
# 37. THE QUICKSLOT WHEEL ON THE MENU'S SCREEN. A new module (modules/quickwheel.lua, kept whole in
#     vrgestures/files/ and copied in) draws Custom Quickslots' slots on a ring at the left hand, on a second instance of
#     the VR menu's screen, and reports which slot the hand is over; VRGestures opens it on the left-hand swipe (36) and
#     uses the slot the grip is let go over. The menu runs it every frame and closes it whenever the menu itself opens.
#     GetMod("CyberpunkVRPort_Menu") passes these through: openQuickWheel(slots), closeQuickWheel(), quickWheelHover().
def copy_in(rel):
    src = ROOT / "vrgestures" / "files" / rel
    dst = ROOT / rel
    dst.write_bytes(src.read_bytes())
    print(f"copied {rel}")

copy_in("mods/cet/CyberpunkVRPort_Menu/modules/quickwheel.lua")
patch("mods/cet/CyberpunkVRPort_Menu/modules/menu.lua", [
    ("local L = require(\"modules/locale\")\n",
     "local L = require(\"modules/locale\")\n"
     "local QW = require(\"modules/quickwheel\")   -- [VRGestures fork] 37\n"),
    ("function M.open(cam,initialSection)\n",
     "function M.open(cam,initialSection)\n"
     "  QW.close()   -- [VRGestures fork] 37: the menu takes over from the quickslot wheel\n"),
    ("  local ok, err = pcall(tick, dt or 0)\n",
     "  pcall(QW.update, dt or 0)   -- [VRGestures fork] 37\n"
     "  local ok, err = pcall(tick, dt or 0)\n"),
    ("function M.openCentred(initialSection) return M.open(camera(),initialSection) end\n",
     "function M.openCentred(initialSection) return M.open(camera(),initialSection) end\n"
     "-- [VRGestures fork] 37: the quickslot wheel, for VRGestures (not while the menu is open)\n"
     "function M.openQuickWheel(slots) if S.open then return false end return QW.open(slots) end\n"
     "function M.closeQuickWheel() QW.close() end\n"
     "function M.quickWheelHover() return QW.hover() end\n"),
    ("  pcall(M.close)\n"
     "  Gameplay.cancelTransition(kit)\n"
     "  capture(false)\n"
     "end\n",
     "  pcall(M.close)\n"
     "  pcall(QW.close)   -- [VRGestures fork] 37\n"
     "  Gameplay.cancelTransition(kit)\n"
     "  capture(false)\n"
     "end\n"),
])
# 38. A CROUCH ENDS THE CLICK SPRINT. With patch 33 a stick click holds the sprint for as long as the player moves, and
#     the game takes a crouch during a sprint as a slide -- which VRGestures keeps for the right grip -- so the right
#     stick pushed down did nothing on the move. The push now ends the click sprint, and its crouch press (R3, the
#     Alternative scheme's ToggleCrouch) waits until the game has left the sprint, 250 ms at most, so it lands as a
#     crouch. The stick's half of the axis is consumed from the first frame, as before.
patch("src/Hooks/XInput.cpp", [
    ("            if (g_vrgSprintClick.load(std::memory_order_relaxed) != 0) {\n",
     "            // [VRGestures fork] 38: the right stick pushed down to crouch ends the click sprint\n"
     "            if (vr.rightThumbY <= -0.85f) g_vrgSprintClick.store(0, std::memory_order_relaxed);\n"
     "            if (g_vrgSprintClick.load(std::memory_order_relaxed) != 0) {\n"),
    ("    if (wantCrouch) ry = 0.0f;\n",
     "    if (wantCrouch) ry = 0.0f;\n"
     "    // [VRGestures fork] 38: the crouch press waits for the sprint to end (a crouch in a sprint is a slide)\n"
     "    bool crouchPress = wantCrouch;\n"
     "    {\n"
     "        static uint64_t s_crouchDownAt = 0;\n"
     "        const uint64_t nowC = GetTickCount64();\n"
     "        if (wantCrouch) { if (s_crouchDownAt == 0) s_crouchDownAt = nowC; } else s_crouchDownAt = 0;\n"
     "        if (wantCrouch && g_VRSprintActive == 1 && nowC - s_crouchDownAt < 250) crouchPress = false;\n"
     "    }\n"),
    ("    if (wantCrouch) synthButtons |= XINPUT_GAMEPAD_RIGHT_THUMB;\n",
     "    if (crouchPress) synthButtons |= XINPUT_GAMEPAD_RIGHT_THUMB;   // [VRGestures fork] 38: was wantCrouch\n"),
])
# 39. THE DODGE BUTTON IS VRGESTURES' GRIP. The right stick pushed up no longer dodges (CyberpunkVR_DashStickUp 0), and
#     VRGPressDodge(ms) holds the game's Dodge_Button (pad B) down for ms milliseconds, merged where the stick-up dash
#     was -- after the physical B, which stays the port's magazine drop -- in gameplay only (not in a car, in water, on a
#     device screen, in the scanner or a menu). VRGestures' right-grip tap is that press, so the game itself decides the
#     dodge, the dash and the Air Dash with its own rules; VRGestures stops reaching into the dodge state.
patch("src/Hooks/XInput.cpp", [
    ("extern \"C\" __declspec(dllexport) int32_t CyberpunkVR_DashStickUp = 1;\n",
     "extern \"C\" __declspec(dllexport) int32_t CyberpunkVR_DashStickUp = 0;   // [VRGestures fork] 39: was 1; the grip is the dodge\n"),
    ("extern \"C\" volatile int32_t CyberpunkVR_PadPressButtons;\n",
     "extern \"C\" volatile int32_t CyberpunkVR_PadPressButtons;\n"
     "extern \"C\" volatile uint64_t CyberpunkVR_DodgePressUntil;   // [VRGestures fork] 39: Natives/OrientationProvider.cpp\n"),
    ("    if (dashPulse) synthButtons |= 0x2000;   // XINPUT_GAMEPAD_B\n",
     "    if (dashPulse) synthButtons |= 0x2000;   // XINPUT_GAMEPAD_B\n"
     "    // [VRGestures fork] 39: VRGestures' grip tap, as the same B (gameplay only)\n"
     "    if (GetTickCount64() < CyberpunkVR_DodgePressUntil && !inWater && !g_isInVehicle && !deviceScreen && !scannerActive\n"
     "        && g_menuModeValue == 0)\n"
     "        synthButtons |= 0x2000;\n"),
])
patch("src/Natives/OrientationProvider.cpp", [
    ("void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n",
     "// [VRGestures fork] 39: the game's Dodge button (pad B) from script, held until the deadline\n"
     "extern \"C\" __declspec(dllexport) volatile uint64_t CyberpunkVR_DodgePressUntil = 0;\n"
     "void VRGPressDodge(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t) {\n"
     "    int32_t ms = 0;\n"
     "    RED4ext::GetParameter(aFrame, &ms);\n"
     "    aFrame->code++;\n"
     "    CyberpunkVR_DodgePressUntil = GetTickCount64() + static_cast<uint64_t>(ms > 0 ? (ms < 500 ? ms : 500) : 0);\n"
     "}\n\n"
     "void GetVRLaserSight(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, bool* aOut, int64_t) {\n"),
])
patch("include/Natives/NativeFunctions.hpp", [
    ("void VRGPadPress(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork] 34\n",
     "void VRGPadPress(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork] 34\n"
     "void VRGPressDodge(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t);   // [VRGestures fork] 39\n"),
])
patch("src/Natives/Registration.cpp", [
    ("    rtti->RegisterFunction(fPadPress);\n",
     "    rtti->RegisterFunction(fPadPress);\n"
     "    // [VRGestures fork] 39: the Dodge button from script\n"
     "    auto fPressDodge = RED4ext::CGlobalFunction::Create(\"VRGPressDodge\", \"VRGPressDodge\", &VRGPressDodge);\n"
     "    fPressDodge->flags = flags; fPressDodge->AddParam(\"Int32\", \"ms\"); rtti->RegisterFunction(fPressDodge);\n"),
])
# 41. THE RIGHT STICK PUSHED UP SPRINTS. With the stick-up dodge gone (39) the top of the right stick was free; a push
#     there now starts the same sprint the left stick click does (33): held through the port's sprint machinery while
#     the player moves, ended by the movement stick coming back to centre or by the right stick pushed down (38).
#     Plus, TEMPORARY: one line in cyberpunkvrport.log each time the stick-down crouch sends its R3, to find out why
#     the crouch is not happening.
patch("src/Hooks/XInput.cpp", [
    ("            if (vr.rightThumbY <= -0.85f) g_vrgSprintClick.store(0, std::memory_order_relaxed);\n",
     "            if (vr.rightThumbY <= -0.85f) g_vrgSprintClick.store(0, std::memory_order_relaxed);\n"
     "            // [VRGestures fork] 41: the right stick pushed up starts it, as the left stick click does\n"
     "            else if (vr.rightThumbY >= 0.85f && !g_isInVehicle && g_menuModeValue == 0)\n"
     "                g_vrgSprintClick.store(1, std::memory_order_relaxed);\n"),
    ("        if (wantCrouch && g_VRSprintActive == 1 && nowC - s_crouchDownAt < 250) crouchPress = false;\n"
     "    }\n",
     "        if (wantCrouch && g_VRSprintActive == 1 && nowC - s_crouchDownAt < 250) crouchPress = false;\n"
     "        static bool s_crouchLogged = false;   // [VRGestures fork] 41 TEMPORARY: each crouch the stick sends\n"
     "        if (crouchPress && !s_crouchLogged)\n"
     "            Log(\"[vrg-crouch] stick down: R3 sent (sprint=%d loco=%d)\\n\", int(g_VRSprintActive), int(g_VRLocomotionState));\n"
     "        s_crouchLogged = crouchPress;\n"
     "    }\n"),
])
# 42. TEMPORARY: WHY THE STICK-DOWN CROUCH DOES NOT FIRE. Patch 41's log showed no crouch sent at all, so each hard push
#     down (raw Y at -0.85 or past) now logs, once per push, the values and every gate the crouch test reads.
patch("src/Hooks/XInput.cpp", [
    ("    if (wantCrouch) ry = 0.0f;\n",
     "    if (wantCrouch) ry = 0.0f;\n"
     "    {   // [VRGestures fork] 42 TEMPORARY: a hard push down, and every gate of the crouch\n"
     "        static bool s_pushLogged = false;\n"
     "        const bool push = vr.rightThumbY <= -0.85f;\n"
     "        if (push && !s_pushLogged)\n"
     "            Log(\"[vrg-crouch] push: rawY=%.2f legacyRy=%.2f analog=%d fullDown=%d water=%d vehicle=%d device=%d \"\n"
     "                \"scanner=%d deviceCam=%d menu=%d -> crouch=%d\\n\", vr.rightThumbY, legacyRy, int(analogMovement),\n"
     "                int(fullDown), int(inWater), int(g_isInVehicle), int(deviceScreen), int(scannerActive),\n"
     "                int(DeviceCamActive()), int(g_menuModeValue), int(wantCrouch));\n"
     "        s_pushLogged = push;\n"
     "    }\n"),
])
# 43. A HELD LEFT STICK CLICK. The click was only ever sent as a one-frame L3 on its release (it is also the D-pad
#     chord's modifier), so the game could never see L3 held. Held a full second with no chord (no right-stick D-pad,
#     no cyberware or menu chord), the click now passes through as a held L3 until it is let go -- and is not also a
#     sprint (the click sprint of 33 is ended), nor a release press on top.
patch("src/Runtimes/OpenXRFrameLoop.cpp", [
    ("                    static bool s_l3Held = false;\n"
     "                    static bool s_l3UsedForDpad = false;\n",
     "                    static bool s_l3Held = false;\n"
     "                    static bool s_l3UsedForDpad = false;\n"
     "                    static uint64_t s_l3DownAt = 0;   // [VRGestures fork] 43\n"
     "                    static bool s_l3Long = false;\n"),
    ("                        if (s_l3UsedForDpad) g_vrgSprintClick.store(0, std::memory_order_relaxed);\n"
     "                        s_l3Held = true;\n"
     "                    } else {\n"
     "                        if (s_l3Held && !s_l3UsedForDpad)\n"
     "                            ctrl.buttons |= 0x0040;   // XINPUT_GAMEPAD_LEFT_THUMB\n"
     "                        s_l3Held = false;\n"
     "                        s_l3UsedForDpad = false;\n"
     "                    }\n",
     "                        if (s_l3UsedForDpad) g_vrgSprintClick.store(0, std::memory_order_relaxed);\n"
     "                        // [VRGestures fork] 43: held a full second with no chord, the click is passed through, held\n"
     "                        const uint64_t nowL3 = GetTickCount64();\n"
     "                        if (!s_l3Held) { s_l3DownAt = nowL3; s_l3Long = false; }\n"
     "                        if (!s_l3UsedForDpad && !s_l3Long && nowL3 - s_l3DownAt >= 1000) {\n"
     "                            s_l3Long = true;\n"
     "                            g_vrgSprintClick.store(0, std::memory_order_relaxed);   // a hold, not a sprint\n"
     "                        }\n"
     "                        if (s_l3Long && !s_l3UsedForDpad) ctrl.buttons |= 0x0040;   // XINPUT_GAMEPAD_LEFT_THUMB\n"
     "                        s_l3Held = true;\n"
     "                    } else {\n"
     "                        if (s_l3Held && !s_l3UsedForDpad && !s_l3Long)   // 43: a long hold has had its press\n"
     "                            ctrl.buttons |= 0x0040;   // XINPUT_GAMEPAD_LEFT_THUMB\n"
     "                        s_l3Held = false;\n"
     "                        s_l3UsedForDpad = false;\n"
     "                        s_l3Long = false;\n"
     "                    }\n"),
])
# 44. THE STICK-DOWN CROUCH IS NOT HELD BACK A FLAT QUARTER SECOND IN A SPRINT. Patch 38 made the crouch wait 250 ms
#     whenever the sprint flag was up (a crouch in a sprint is a slide), so a third of the crouches came late and a
#     quick flick let go inside the wait was lost. Now it goes the moment the game says the sprint has ended, still
#     never later than 250 ms after the push, and a push let go before its press is kept and sent then. Plus the
#     temporary crouch logging of 41 and 42 comes out.
patch("src/Hooks/XInput.cpp", [
    ("    if (wantCrouch) ry = 0.0f;\n"
     "    {   // [VRGestures fork] 42 TEMPORARY: a hard push down, and every gate of the crouch\n"
     "        static bool s_pushLogged = false;\n"
     "        const bool push = vr.rightThumbY <= -0.85f;\n"
     "        if (push && !s_pushLogged)\n"
     "            Log(\"[vrg-crouch] push: rawY=%.2f legacyRy=%.2f analog=%d fullDown=%d water=%d vehicle=%d device=%d \"\n"
     "                \"scanner=%d deviceCam=%d menu=%d -> crouch=%d\\n\", vr.rightThumbY, legacyRy, int(analogMovement),\n"
     "                int(fullDown), int(inWater), int(g_isInVehicle), int(deviceScreen), int(scannerActive),\n"
     "                int(DeviceCamActive()), int(g_menuModeValue), int(wantCrouch));\n"
     "        s_pushLogged = push;\n"
     "    }\n"
     "    // [VRGestures fork] 38: the crouch press waits for the sprint to end (a crouch in a sprint is a slide)\n"
     "    bool crouchPress = wantCrouch;\n"
     "    {\n"
     "        static uint64_t s_crouchDownAt = 0;\n"
     "        const uint64_t nowC = GetTickCount64();\n"
     "        if (wantCrouch) { if (s_crouchDownAt == 0) s_crouchDownAt = nowC; } else s_crouchDownAt = 0;\n"
     "        if (wantCrouch && g_VRSprintActive == 1 && nowC - s_crouchDownAt < 250) crouchPress = false;\n"
     "        static bool s_crouchLogged = false;   // [VRGestures fork] 41 TEMPORARY: each crouch the stick sends\n"
     "        if (crouchPress && !s_crouchLogged)\n"
     "            Log(\"[vrg-crouch] stick down: R3 sent (sprint=%d loco=%d)\\n\", int(g_VRSprintActive), int(g_VRLocomotionState));\n"
     "        s_crouchLogged = crouchPress;\n"
     "    }\n",
     "    if (wantCrouch) ry = 0.0f;\n"
     "    // [VRGestures fork] 38/44: the crouch press waits for the sprint to end (a crouch in a sprint is a slide) --\n"
     "    // until the game says it has, never longer than 250 ms -- and a push let go before its press is kept and\n"
     "    // sent then, as a short press, instead of being lost\n"
     "    bool crouchPress = false;\n"
     "    {\n"
     "        static uint64_t s_crouchDownAt = 0;\n"
     "        static bool s_crouchSent = false;\n"
     "        static uint64_t s_crouchOwedBy = 0;   // a push let go in the wait: sent when the sprint ends, by this time\n"
     "        static uint64_t s_crouchPulseTo = 0;  // that press, held until this time\n"
     "        const uint64_t nowC = GetTickCount64();\n"
     "        const bool sprintWait = g_VRSprintActive == 1;\n"
     "        if (wantCrouch) {\n"
     "            if (s_crouchDownAt == 0) { s_crouchDownAt = nowC; s_crouchSent = false; s_crouchOwedBy = 0; }\n"
     "            crouchPress = s_crouchSent || !sprintWait || nowC - s_crouchDownAt >= 250;\n"
     "            s_crouchSent = crouchPress;\n"
     "        } else {\n"
     "            if (s_crouchDownAt != 0 && !s_crouchSent) s_crouchOwedBy = s_crouchDownAt + 250;\n"
     "            s_crouchDownAt = 0;\n"
     "            const bool crouchGates = !inWater && !g_isInVehicle && !deviceScreen && !scannerActive && !DeviceCamActive();\n"
     "            if (s_crouchOwedBy != 0 && !crouchGates) s_crouchOwedBy = 0;\n"
     "            if (s_crouchOwedBy != 0 && (!sprintWait || nowC >= s_crouchOwedBy)) { s_crouchOwedBy = 0; s_crouchPulseTo = nowC + 60; }\n"
     "            crouchPress = nowC < s_crouchPulseTo;\n"
     "        }\n"
     "    }\n"),
])
# 45. LEFT GRIP + LEFT STICK = THE D-PAD. A left grip squeezed with the left stick at rest arms the chord for that
#     squeeze: the stick then picks a D-pad direction (pushed past the same 0.90 as the right-stick chord) and does
#     not walk. A squeeze that closes while walking stays walking. It stands aside while the left hand is on a gun
#     (two-handed) or carrying one, on a ladder, while the monowire owns the grip, in a car (the grip takes the
#     wheel), in menus, a braindance, a keypad or a device camera, and a stick click during the squeeze ends it
#     (grip + double click is VRGestures' launcher toggle). The left-click + right-stick chord stays as it was.
# 46. NO LEFT GRIP + LEFT STICK CLICK CYBERWARE. VRGestures' gestures use the cyberware; the chord is gone, which
#     also leaves the grip and the click to the launcher toggle and to 45.
patch("src/Runtimes/OpenXRFrameLoop.cpp", [
    ("#include \"Hooks/CyberwareChord.hpp\"\n",
     "#include \"Hooks/CyberwareChord.hpp\"\n"
     "#include \"Hooks/LadderInput.hpp\"       // [VRGestures fork] 45: what the left grip may be busy with\n"
     "#include \"Hooks/KeypadInput.hpp\"\n"
     "#include \"Anim/Cyberware.hpp\"\n"
     "#include \"Anim/HeadAimWeapon.hpp\"\n"
     "bool DeviceCamActive();                      // Camera/CameraState.hpp (its eye flag clashes with this file's)\n"
     "extern std::atomic<int> g_bdActive;\n"
     "#include \"Core/VrCoreShared.hpp\"\n"
     "extern \"C\" int CyberpunkVR_TwoHandActive;   // Anim/TwoHandGrip.cpp\n"
     "extern \"C\" int CyberpunkVR_CarryLeft;\n"),
    # 0.2.0: the PSVR2 triangle shift follows the click now, so the chord goes straight after it
    ("                        leftStickClicked = sclick;\n",
     "                        leftStickClicked = sclick;\n"
     "\n"
     "                        // [VRGestures fork] 45: LEFT GRIP + LEFT STICK = the D-pad, armed by a squeeze that closes\n"
     "                        // with the stick at rest; while armed the stick picks a direction and does not walk\n"
     "                        {\n"
     "                            static bool s_gripDown = false;\n"
     "                            static bool s_gripDpad = false;\n"
     "                            const bool gripNow = grip >= (s_gripDown ? 0.5f : 0.7f);\n"
     "                            const int cwKind = cvr::cyberware::SelectedKind();\n"
     "                            const bool wireGrip = cwKind == 3 && g_menuModeValue == 0 && !cvr::anim::IsHeadAimWeaponActive();\n"
     "                            const bool busy = !gameplayInputActive || g_menuModeValue != 0 || g_isInVehicle\n"
     "                                || CyberpunkVR_TwoHandActive != 0 || CyberpunkVR_CarryLeft != 0 || cvr::ladder::Active()\n"
     "                                || wireGrip || DeviceCamActive() || g_bdActive.load(std::memory_order_relaxed) != 0\n"
     "                                || cvr::input::KeypadInputActive();\n"
     "                            if (gripNow && !s_gripDown) s_gripDpad = std::fabs(sx) < 0.3f && std::fabs(sy) < 0.3f;\n"
     "                            if (!gripNow || busy || sclick) s_gripDpad = false;\n"
     "                            s_gripDown = gripNow;\n"
     "                            if (s_gripDpad) {\n"
     "                                float threshold = CyberpunkVR_DpadChordStick;\n"
     "                                if (!(threshold > 0.05f) || threshold > 1.0f) threshold = 0.90f;\n"
     "                                if (sy > threshold)  { ctrl.buttons |= XB_DPAD_UP;    dpadUsedThisFrame = true; }\n"
     "                                if (sy < -threshold) { ctrl.buttons |= XB_DPAD_DOWN;  dpadUsedThisFrame = true; }\n"
     "                                if (sx < -threshold) { ctrl.buttons |= XB_DPAD_LEFT;  dpadUsedThisFrame = true; }\n"
     "                                if (sx > threshold)  { ctrl.buttons |= XB_DPAD_RIGHT; dpadUsedThisFrame = true; }\n"
     "                                ctrl.leftThumbX = 0.0f;\n"
     "                                ctrl.leftThumbY = 0.0f;\n"
     "                            }\n"
     "                        }\n"),
    ("                const bool cyberwareClaim=cvr::input::UpdateCyberwareChord(leftStickClicked,ctrl.leftGrip,\n"
     "                    uiTracking.hands[1].stickClick,gameplayInputActive);\n",
     "                // [VRGestures fork] 46: no left grip + left stick click cyberware (VRGestures' gestures use it)\n"
     "                const bool cyberwareClaim=false;\n"),
])
# 47. THE LEFT-GRIP D-PAD IN CARS, OFF THE WHEEL. 45 stood aside for the whole of a car because the left grip also
#     takes the steering wheel. It now stands aside only while the wheel grab has the left hand -- near the wheel
#     or holding it (the same flag that keeps the grip from being a gameplay button there) -- so a squeeze anywhere
#     else in the cabin, or as a passenger, is the D-pad.
patch("src/Runtimes/OpenXRFrameLoop.cpp", [
    ("                            const bool busy = !gameplayInputActive || g_menuModeValue != 0 || g_isInVehicle\n",
     "                            // 47: in a car only while the wheel grab has this hand (near the wheel, or holding it)\n"
     "                            const bool leftOnWheel = (static_cast<int>(OpenXRManager::Get().GetSharedSlot(vrshared::kWheelArmedMask))\n"
     "                                                      & vrshared::kWheelArmedLeftBit) != 0;\n"
     "                            const bool busy = !gameplayInputActive || g_menuModeValue != 0 || (g_isInVehicle && leftOnWheel)\n"),
])
# 48. THE WRIST DISPLAY. Scripts post small gauges -- a title, a state word, up to three bars -- through
#     VRWristGauge(slot, spec) and the port draws them as their own OpenXR quad in the LEFT controller's aim space,
#     so the display stays on the wrist with no lag behind the hand (Runtimes/WristHud.cpp, kept whole in
#     vrgestures/files/ and copied in; built on Framegen/StatsOverlay's bitmap pattern). VRWristHudPlace(x, y, z, tilt,
#     width) moves it. Nothing is submitted while no gauge is live; a gauge not refreshed for 1.5 s goes away.
def copy_new(rel):
    src = ROOT / "vrgestures" / "files" / rel
    dst = ROOT / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    print(f"copied {rel}")

copy_new("include/Runtimes/WristHud.hpp")
copy_new("src/Runtimes/WristHud.cpp")
patch("include/Runtimes/OpenXRManager.hpp", [
    ("#include \"Framegen/StatsOverlay.hpp\"\n",
     "#include \"Framegen/StatsOverlay.hpp\"\n"
     "#include \"Runtimes/WristHud.hpp\"   // [VRGestures fork] 48\n"),
    ("    cvr::framegen::StatsOverlay m_framegenOverlay;\n",
     "    cvr::framegen::StatsOverlay m_framegenOverlay;\n"
     "    cvr::wristhud::Quad m_wristHud;   // [VRGestures fork] 48: the wrist display\n"),
])
patch("src/Runtimes/OpenXRManager.cpp", [
    ("    m_framegenOverlay.Shutdown(true);\n",
     "    m_framegenOverlay.Shutdown(true);\n"
     "    m_wristHud.Shutdown(true);   // [VRGestures fork] 48\n"),
])
patch("src/Runtimes/OpenXRFrameLoop.cpp", [
    ("                            const XrCompositionLayerBaseHeader* layers[1+2*cvr::hud::ChannelCount+3] = {};\n",
     "                            const XrCompositionLayerBaseHeader* layers[1+2*cvr::hud::ChannelCount+4] = {};   // [VRGestures fork] 48: +1, the wrist\n"),
    ("                                if(!cvr::vrui::Visible())layers[endInfo.layerCount++]=metrics;\n",
     "                                if(!cvr::vrui::Visible())layers[endInfo.layerCount++]=metrics;\n"
     "                            // [VRGestures fork] 48: the wrist display, in the left hand's aim space\n"
     "                            if(const auto* wrist=m_wristHud.Prepare(m_session,m_handAimSpaces[0],m_d3dDevice,m_d3dQueue))\n"
     "                                if(!cvr::vrui::Visible())layers[endInfo.layerCount++]=wrist;\n"),
])
patch("src/Natives/Registration.cpp", [
    ("#include \"Natives/NativeFunctions.hpp\"\n",
     "#include \"Natives/NativeFunctions.hpp\"\n"
     "#include \"Runtimes/WristHud.hpp\"   // [VRGestures fork] 48\n"),
    ("    fHandAim->flags = flags; fHandAim->AddParam(\"Int32\", \"side\"); fHandAim->SetReturnType(\"array:Vector4\");\n"
     "    rtti->RegisterFunction(fHandAim);\n",
     "    fHandAim->flags = flags; fHandAim->AddParam(\"Int32\", \"side\"); fHandAim->SetReturnType(\"array:Vector4\");\n"
     "    rtti->RegisterFunction(fHandAim);\n"
     "    // [VRGestures fork] 48: the wrist display\n"
     "    auto fWristGauge = RED4ext::CGlobalFunction::Create(\"VRWristGauge\", \"VRWristGauge\", &cvr::wristhud::VRWristGauge);\n"
     "    fWristGauge->flags = flags; fWristGauge->AddParam(\"Int32\", \"slot\"); fWristGauge->AddParam(\"String\", \"spec\");\n"
     "    rtti->RegisterFunction(fWristGauge);\n"
     "    auto fWristPlace = RED4ext::CGlobalFunction::Create(\"VRWristHudPlace\", \"VRWristHudPlace\", &cvr::wristhud::VRWristHudPlace);\n"
     "    fWristPlace->flags = flags;\n"
     "    fWristPlace->AddParam(\"Float\", \"x\"); fWristPlace->AddParam(\"Float\", \"y\"); fWristPlace->AddParam(\"Float\", \"z\");\n"
     "    fWristPlace->AddParam(\"Float\", \"tilt\"); fWristPlace->AddParam(\"Float\", \"width\");\n"
     "    rtti->RegisterFunction(fWristPlace);\n"),
])
# 49. THE RAW RIGHT STICK Y FOR SCRIPTS. Shared slot 241 carries the right stick's Y every poll, before anything here
#     consumes it, so a script can read a HELD push: CyberWings boosts while the stick is held up. (Slot 240, the
#     click-sprint latch, stays on after the push and could not say "held".)
patch("src/Hooks/XInput.cpp", [
    ("        OpenXRManager::Get().SetSharedSlot(240, clickSprint ? 1.0f : 0.0f);\n",
     "        OpenXRManager::Get().SetSharedSlot(240, clickSprint ? 1.0f : 0.0f);\n"
     "        OpenXRManager::Get().SetSharedSlot(241, vr.rightThumbY);   // [VRGestures fork] 49: the raw right stick Y\n"),
])
# 50. OTHER MODS' ROWS ON THE WRIST READOUT. The readout gains a few rows of its own kind -- a label, a thin bar like
#     the health bar, a value -- that other scripts fill through GetMod("CyberpunkVRPort_WristHud").row(id, label,
#     value, text, r, g, b) (VRGestures passes CyberWings' charge and heat). They are built and laid out with
#     everything else, so they survive the widget swaps the readout already rebuilds after; a row not refreshed for
#     1.5 s goes away by itself, and nothing shows while there are none. Placed with the "OTHER MODS' ROWS" sliders.
patch("mods/cet/CyberpunkVRPort_WristHud/init.lua", [
    ("  { g = \"COLOUR  (above 1.0 is emissive -- this is an HDR tint)\" },\n",
     "  { g = \"OTHER MODS' ROWS  (label, bar, value: CyberWings' charge and heat, through row())\" },\n"
     "  { k = \"ex_x\",    l = \"left edge\",         d = 0.0, lo = -400.0, hi = 400.0 },\n"
     "  { k = \"ex_y\",    l = \"up / down\",         d = 215.0, lo = -300.0, hi = 400.0 },\n"
     "  { k = \"ex_step\", l = \"row step\",          d = 30.0, lo = 10.0, hi = 90.0 },\n"
     "  { k = \"ex_font\", l = \"type size\",         d = 18.0, lo = 6.0, hi = 60.0, int = true },\n"
     "  { k = \"ex_lw\",   l = \"label width\",       d = 70.0, lo = 0.0, hi = 300.0 },\n"
     "  { k = \"ex_w\",    l = \"bar length\",        d = 150.0, lo = 20.0, hi = 500.0 },\n"
     "  { k = \"ex_h\",    l = \"bar thickness\",     d = 6.0, lo = 1.0, hi = 40.0 },\n"
     "  { k = \"ex_alpha\", l = \"opacity\",          d = 0.85, lo = 0.0, hi = 1.0 },\n"
     "\n"
     "  { g = \"COLOUR  (above 1.0 is emissive -- this is an HDR tint)\" },\n"),
    ("    S.stars[i] = q\n  end\n",
     "    S.stars[i] = q\n  end\n"
     "  -- [VRGestures fork] 50: the other mods' rows\n"
     "  S.extra = {}\n"
     "  for i = 1, MAX_EXTRA do\n"
     "    S.extra[i] = { lbl = mkText(root, textHorizontalAlignment.Left), track = mkRect(root), fill = mkRect(root),\n"
     "                   val = mkText(root, textHorizontalAlignment.Right) }\n"
     "  end\n"),
    ("local MAX_STARS = 5                  -- what the wanted bar itself shows: five star widgets\n",
     "local MAX_STARS = 5                  -- what the wanted bar itself shows: five star widgets\n"
     "-- [VRGestures fork] 50: rows other mods post through row(); id -> { label, value, text, r, g, b, at }, in arrival order\n"
     "local MAX_EXTRA = 4\n"
     "local EXTRA, EXTRA_ORDER, EXTRA_T = {}, {}, 0.0\n"),
    ("  S.dirty = false\n",
     "  -- [VRGestures fork] 50: the other mods' rows, one under another\n"
     "  for i = 1, MAX_EXTRA do\n"
     "    local e = S.extra and S.extra[i]\n"
     "    if e then\n"
     "      local y = oy + cfg.ex_y + (i - 1) * cfg.ex_step\n"
     "      local x = ox + cfg.ex_x\n"
     "      place(e.lbl, cfg.ex_lw + cfg.ex_font * 2.0, cfg.ex_font * 1.8, x, y, 0.0, 0.5)\n"
     "      place(e.track, cfg.ex_w, cfg.ex_h, x + cfg.ex_lw, y, 0.0, 0.5)\n"
     "      place(e.fill, cfg.ex_w, cfg.ex_h, x + cfg.ex_lw, y, 0.0, 0.5)\n"
     "      place(e.val, cfg.ex_font * 4.0, cfg.ex_font * 1.8, x + cfg.ex_lw + cfg.ex_w + cfg.ex_font * 4.2, y, 1.0, 0.5)\n"
     "      for _, t in ipairs({ e.lbl, e.val }) do\n"
     "        pcall(function() t:SetFontFamily(fam[1], fam[2]) end)\n"
     "        pcall(function() t:SetFontSize(math.floor(cfg.ex_font + 0.5)) end)\n"
     "        pcall(function() t:SetTintColor(tint()) end)\n"
     "        t:SetOpacity(cfg.ex_alpha)\n"
     "      end\n"
     "      pcall(function() e.track:SetTintColor(tint()) end)\n"
     "      e.track:SetOpacity(cfg.ex_alpha * 0.18)\n"
     "    end\n"
     "  end\n"
     "  S.dirty = false\n"),
    ("registerForEvent(\"onUpdate\", function(dt)\n",
     "-- [VRGestures fork] 50: the other mods' rows, refreshed with the values; a row not posted for 1.5 s goes\n"
     "local function extras()\n"
     "  if not S.built or not S.extra then return end\n"
     "  for i = #EXTRA_ORDER, 1, -1 do\n"
     "    local id = EXTRA_ORDER[i]\n"
     "    if EXTRA_T - EXTRA[id].at > 1.5 then EXTRA[id] = nil; table.remove(EXTRA_ORDER, i) end\n"
     "  end\n"
     "  for i = 1, MAX_EXTRA do\n"
     "    local e, r = S.extra[i], EXTRA[EXTRA_ORDER[i] or \"\"]\n"
     "    if r then\n"
     "      local v = math.max(0.0, math.min(1.0, r.value))\n"
     "      pcall(function() e.lbl:SetText(r.label) end)\n"
     "      pcall(function() e.val:SetText(r.text) end)\n"
     "      e.fill:SetSize(Vector2.new({ X = math.max(cfg.ex_w * v, 0.0), Y = cfg.ex_h }))\n"
     "      if r.r then\n"
     "        pcall(function() e.fill:SetTintColor(HDRColor.new({ Red = r.r, Green = r.g, Blue = r.b, Alpha = 1.0 })) end)\n"
     "      else\n"
     "        pcall(function() e.fill:SetTintColor(tint()) end)\n"
     "      end\n"
     "      e.fill:SetOpacity(cfg.ex_alpha)\n"
     "      e.fill:SetVisible(v > 0.001)\n"
     "      e.lbl:SetVisible(true); e.val:SetVisible(true); e.track:SetVisible(true)\n"
     "    else\n"
     "      e.lbl:SetVisible(false); e.val:SetVisible(false); e.track:SetVisible(false); e.fill:SetVisible(false)\n"
     "    end\n"
     "  end\n"
     "end\n"
     "\n"
     "registerForEvent(\"onUpdate\", function(dt)\n"
     "  EXTRA_T = EXTRA_T + (dt or 0.016)   -- [VRGestures fork] 50\n"),
    ("  if S.accFast >= 0.12 then\n    S.accFast = 0.0\n    values()\n  end\n",
     "  if S.accFast >= 0.12 then\n    S.accFast = 0.0\n    values()\n    pcall(extras)   -- [VRGestures fork] 50\n  end\n"),
    ("    ImGui.End()\n  end)\nend)\n",
     "    ImGui.End()\n  end)\nend)\n"
     "\n"
     "-- [VRGestures fork] 50: for other mods. row(id, label, value 0..1, text, r, g, b): a row on the wrist (colour optional,\n"
     "-- HDR -- above 1 glows); post it every frame or so, it goes 1.5 s after the last. clear(id) takes it off at once.\n"
     "return {\n"
     "  row = function(id, label, value, text, r, g, b)\n"
     "    if type(id) ~= \"string\" then return false end\n"
     "    if not EXTRA[id] then EXTRA_ORDER[#EXTRA_ORDER + 1] = id end\n"
     "    EXTRA[id] = { label = tostring(label or \"\"), value = tonumber(value) or 0.0, text = tostring(text or \"\"),\n"
     "                  r = tonumber(r), g = tonumber(g), b = tonumber(b), at = EXTRA_T }\n"
     "    return S.built == true\n"
     "  end,\n"
     "  -- a readout setting by its wrist.cfg name: read it, or set and save it (VRGestures' game-menu sliders)\n"
     "  setting = function(k, v)\n"
     "    if cfg[k] == nil then return nil end\n"
     "    if v ~= nil then cfg[k] = tonumber(v) or cfg[k]; S.dirty = true; pcall(saveCfg) end\n"
     "    return cfg[k]\n"
     "  end,\n"
     "  clear = function(id)\n"
     "    if not EXTRA[id] then return end\n"
     "    EXTRA[id] = nil\n"
     "    for i, k in ipairs(EXTRA_ORDER) do if k == id then table.remove(EXTRA_ORDER, i) break end end\n"
     "  end,\n"
     "}\n"),
])
# 51. THE OTHER MODS' ROWS TAKE THE BUFF ICONS' PLACE. Below the icons (50's default) was off the patch, so the rows
#     never showed. They now sit on the icon rows themselves, and while any row is posted the buff icons step aside;
#     the icons come back the moment the last row goes.
patch("mods/cet/CyberpunkVRPort_WristHud/init.lua", [
    ("  { k = \"ex_y\",    l = \"up / down\",         d = 215.0, lo = -300.0, hi = 400.0 },\n",
     "  { k = \"ex_y\",    l = \"up / down\",         d = 164.0, lo = -300.0, hi = 400.0 },   -- [VRGestures fork] 51: the icon rows\n"),
    ("  { k = \"ex_step\", l = \"row step\",          d = 30.0, lo = 10.0, hi = 90.0 },\n",
     "  { k = \"ex_step\", l = \"row step\",          d = 32.0, lo = 10.0, hi = 90.0 },\n"),
    ("local function icons()\n"
     "  local p = Game.GetPlayer()\n"
     "  if p == nil or not S.built then return end\n",
     "local function icons()\n"
     "  local p = Game.GetPlayer()\n"
     "  if p == nil or not S.built then return end\n"
     "  -- [VRGestures fork] 51: other mods' rows are on the icon rows; the icons step aside while there are any\n"
     "  if #EXTRA_ORDER > 0 then\n"
     "    for i = 1, MAX_ICONS do if S.icons[i] then S.icons[i]:SetVisible(false) end end\n"
     "    return\n"
     "  end\n"),
    ("  for i = 1, MAX_EXTRA do\n"
     "    local e, r = S.extra[i], EXTRA[EXTRA_ORDER[i] or \"\"]\n",
     "  -- [VRGestures fork] 51: the first row in or the last row out redraws the icons at once\n"
     "  if (#EXTRA_ORDER > 0) ~= (S.extraShown == true) then S.extraShown = #EXTRA_ORDER > 0; pcall(icons) end\n"
     "  for i = 1, MAX_EXTRA do\n"
     "    local e, r = S.extra[i], EXTRA[EXTRA_ORDER[i] or \"\"]\n"),
])
# 52. THE WRIST READOUT'S ROWS AND SETTINGS FOR CET MODS, THROUGH MAILBOXES. 0.2.0 runs the port's Lua mods in the
#     plugin's own host, so VRGestures (in CET) can no longer GetMod the readout for 50's row() and setting(). Both hosts
#     still call the game's global functions, so the plugin keeps a few named texts (VRGMailPut / Add / Get / Take,
#     Runtimes/WristHud.cpp): VRGestures posts its rows to "vrg.wrist.rows" and its slider changes to "vrg.wrist.set";
#     the readout reads them ten times a second and publishes its own numbers to "vrg.wrist.cfg" once a second.
patch("src/Natives/Registration.cpp", [
    ("    rtti->RegisterFunction(fWristPlace);\n",
     "    rtti->RegisterFunction(fWristPlace);\n"
     "    // [VRGestures fork] 52: mailboxes between CET and the plugin's Lua host\n"
     "    auto fMailPut = RED4ext::CGlobalFunction::Create(\"VRGMailPut\", \"VRGMailPut\", &cvr::wristhud::VRGMailPut);\n"
     "    fMailPut->flags = flags; fMailPut->AddParam(\"String\", \"box\"); fMailPut->AddParam(\"String\", \"text\");\n"
     "    rtti->RegisterFunction(fMailPut);\n"
     "    auto fMailAdd = RED4ext::CGlobalFunction::Create(\"VRGMailAdd\", \"VRGMailAdd\", &cvr::wristhud::VRGMailAdd);\n"
     "    fMailAdd->flags = flags; fMailAdd->AddParam(\"String\", \"box\"); fMailAdd->AddParam(\"String\", \"line\");\n"
     "    rtti->RegisterFunction(fMailAdd);\n"
     "    auto fMailGet = RED4ext::CGlobalFunction::Create(\"VRGMailGet\", \"VRGMailGet\", &cvr::wristhud::VRGMailGet);\n"
     "    fMailGet->flags = flags; fMailGet->AddParam(\"String\", \"box\"); fMailGet->AddParam(\"Int32\", \"maxAgeMs\");\n"
     "    fMailGet->SetReturnType(\"String\"); rtti->RegisterFunction(fMailGet);\n"
     "    auto fMailTake = RED4ext::CGlobalFunction::Create(\"VRGMailTake\", \"VRGMailTake\", &cvr::wristhud::VRGMailTake);\n"
     "    fMailTake->flags = flags; fMailTake->AddParam(\"String\", \"box\");\n"
     "    fMailTake->SetReturnType(\"String\"); rtti->RegisterFunction(fMailTake);\n"),
])
patch("mods/cet/CyberpunkVRPort_WristHud/init.lua", [
    ("-- [VRGestures fork] 50: the other mods' rows, refreshed with the values; a row not posted for 1.5 s goes\n",
     "-- [VRGestures fork] 52: the same rows and settings for mods in CET, which GetMod no longer reaches from here, through\n"
     "-- the plugin's mailboxes. Rows: box \"vrg.wrist.rows\", one a line -- id, label, value, text, r, g, b, tab-separated --\n"
     "-- the whole set at every post (a set not posted for 1.5 s reads empty). Settings: this readout's numbers go out on\n"
     "-- \"vrg.wrist.cfg\" (k=v lines, once a second); changes come in on \"vrg.wrist.set\" and are saved like the overlay's.\n"
     "local MAIL_IDS, MAIL_T, MAIL_CFG_T = {}, 0.0, 1.0\n"
     "local function bridge(dt)\n"
     "  if type(VRGMailGet) ~= \"function\" then return end\n"
     "  MAIL_T = MAIL_T + (dt or 0.016)\n"
     "  MAIL_CFG_T = MAIL_CFG_T + (dt or 0.016)\n"
     "  if MAIL_T < 0.1 then return end\n"
     "  MAIL_T = 0.0\n"
     "  local now = {}\n"
     "  local rows = VRGMailGet(\"vrg.wrist.rows\", 1500) or \"\"\n"
     "  for line in rows:gmatch(\"[^\\n]+\") do\n"
     "    local f = {}\n"
     "    for x in (line .. \"\\t\"):gmatch(\"([^\\t]*)\\t\") do f[#f + 1] = x end\n"
     "    if f[1] and f[1] ~= \"\" then\n"
     "      local id = \"mail:\" .. f[1]\n"
     "      now[id] = true\n"
     "      if not EXTRA[id] then EXTRA_ORDER[#EXTRA_ORDER + 1] = id end\n"
     "      EXTRA[id] = { label = f[2] or \"\", value = tonumber(f[3]) or 0.0, text = f[4] or \"\",\n"
     "                    r = tonumber(f[5]), g = tonumber(f[6]), b = tonumber(f[7]), at = EXTRA_T }\n"
     "    end\n"
     "  end\n"
     "  for id in pairs(MAIL_IDS) do\n"
     "    if not now[id] and EXTRA[id] then\n"
     "      EXTRA[id] = nil\n"
     "      for i, k in ipairs(EXTRA_ORDER) do if k == id then table.remove(EXTRA_ORDER, i) break end end\n"
     "    end\n"
     "  end\n"
     "  MAIL_IDS = now\n"
     "  local set = type(VRGMailTake) == \"function\" and VRGMailTake(\"vrg.wrist.set\") or \"\"\n"
     "  local changed = false\n"
     "  for k, v in set:gmatch(\"([%w_]+)=(-?[%d%.]+)\") do\n"
     "    if cfg[k] ~= nil and tonumber(v) then cfg[k] = tonumber(v); changed = true end\n"
     "  end\n"
     "  if changed then S.dirty = true; pcall(saveCfg); MAIL_CFG_T = 1.0 end\n"
     "  if MAIL_CFG_T >= 1.0 and type(VRGMailPut) == \"function\" then\n"
     "    MAIL_CFG_T = 0.0\n"
     "    local out = {}\n"
     "    for _, e in ipairs(SPEC) do\n"
     "      if e.k and cfg[e.k] ~= nil then out[#out + 1] = string.format(\"%s=%.4f\", e.k, cfg[e.k]) end\n"
     "    end\n"
     "    VRGMailPut(\"vrg.wrist.cfg\", table.concat(out, \"\\n\"))\n"
     "  end\n"
     "end\n"
     "\n"
     "-- [VRGestures fork] 50: the other mods' rows, refreshed with the values; a row not posted for 1.5 s goes\n"),
    ("  EXTRA_T = EXTRA_T + (dt or 0.016)   -- [VRGestures fork] 50\n",
     "  EXTRA_T = EXTRA_T + (dt or 0.016)   -- [VRGestures fork] 50\n"
     "  pcall(bridge, dt)                   -- [VRGestures fork] 52: rows and settings from CET\n"),
])

print("all VRGestures fork patches applied")
