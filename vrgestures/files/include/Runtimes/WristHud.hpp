#pragma once
// [VRGestures fork] 48: THE WRIST DISPLAY. Small gauges (a title, a state word and up to three bars) fed by scripts
// through VRWristGauge and drawn as their own OpenXR quad in the LEFT controller's aim space, so the compositor keeps
// it on the wrist with no lag behind the hand. Built on Framegen/StatsOverlay's pattern: a CPU bitmap with a 5x7
// font, uploaded only when something changed (at most ten times a second). Nothing is submitted while no gauge is live.
#include <windows.h>
#include <d3d12.h>
#include <openxr/openxr.h>
#include <openxr/openxr_platform.h>
#include <wrl/client.h>
#include <vector>

namespace RED4ext { struct IScriptable; struct CStackFrame; struct CString; }

namespace cvr::wristhud {
// VRWristGauge(slot: Int32, spec: String): spec is tab-separated -- title, state, then per bar: value 0..1, text,
// colour RRGGBB. An empty spec clears the slot; a slot not refreshed for 1.5 s goes away by itself.
void VRWristGauge(RED4ext::IScriptable*, RED4ext::CStackFrame*, void*, int64_t);
// VRWristHudPlace(x, y, z: Float, tilt: Float, width: Float): where the display sits in the left aim space (metres;
// +z is back toward the elbow, +y up), its tilt toward the face (degrees) and its width (metres).
void VRWristHudPlace(RED4ext::IScriptable*, RED4ext::CStackFrame*, void*, int64_t);

// [VRGestures fork] 52: MAILBOXES between the two Lua hosts. Since 0.2.0 the port's Lua mods run in the plugin's own
// host and CET's GetMod no longer reaches them, but both hosts call the game's global functions. A box holds one text:
//   VRGMailPut(box: String, text: String)               replace it (and stamp it)
//   VRGMailAdd(box: String, line: String)               append one line to it
//   VRGMailGet(box: String, maxAgeMs: Int32) -> String  read it ("" when older than maxAgeMs; 0 = any age)
//   VRGMailTake(box: String) -> String                  read it and empty it
void VRGMailPut(RED4ext::IScriptable*, RED4ext::CStackFrame*, void*, int64_t);
void VRGMailAdd(RED4ext::IScriptable*, RED4ext::CStackFrame*, void*, int64_t);
void VRGMailGet(RED4ext::IScriptable*, RED4ext::CStackFrame*, RED4ext::CString*, int64_t);
void VRGMailTake(RED4ext::IScriptable*, RED4ext::CStackFrame*, RED4ext::CString*, int64_t);

class Quad {
public:
    const XrCompositionLayerBaseHeader* Prepare(XrSession,XrSpace hand,ID3D12Device*,ID3D12CommandQueue*);
    void Shutdown(bool wait=false);
private:
    XrSwapchain swapchain{};
    std::vector<XrSwapchainImageD3D12KHR> images;
    Microsoft::WRL::ComPtr<ID3D12CommandAllocator> allocator;
    Microsoft::WRL::ComPtr<ID3D12GraphicsCommandList> list;
    Microsoft::WRL::ComPtr<ID3D12Resource> upload;
    Microsoft::WRL::ComPtr<ID3D12Fence> fence;
    XrCompositionLayerQuad layer{XR_TYPE_COMPOSITION_LAYER_QUAD};
    uint64_t fenceValue{},drawnSerial{};double nextUpdate{};
    uint32_t acquiredIndex{},usedHeight{};bool acquired{},published{};
    uint32_t rowPitch{};
    std::vector<uint32_t> pixels;
};
}
