// [VRGestures fork] 48: the wrist display -- see Runtimes/WristHud.hpp.
#include "Runtimes/WristHud.hpp"
#include <RED4ext/RED4ext.hpp>
#include <RED4ext/Scripting/Functions.hpp>
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <map>
#include <mutex>
#include <string>

namespace cvr::wristhud {
namespace {
constexpr uint32_t W=384,H=448;     // the bitmap: room for four one-bar gauges or two three-bar ones
constexpr int MaxSlots=4,MaxBars=3;
constexpr uint64_t TtlMs=1500;

struct Gauge { std::string title,state;uint32_t accent=0xFFFFDC6Eu;int bars=0;float v[MaxBars]{};std::string t[MaxBars];uint32_t c[MaxBars]{};uint64_t at=0; };
struct Place { float x=0.0f,y=0.035f,z=0.16f,tilt=40.0f,width=0.10f; };
std::mutex mtx;
Gauge gauges[MaxSlots];
Place place;
uint64_t serial=0;

// RRGGBB -> the bitmap's byte order (R in the low byte), opaque
uint32_t Colour(const std::string& hex,uint32_t fallback) {
    if(hex.size()!=6)return fallback;
    char* end{};const unsigned long v=std::strtoul(hex.c_str(),&end,16);
    if(!end || *end)return fallback;
    return 0xFF000000u|((v&0xFF)<<16)|(v&0xFF00)|((v>>16)&0xFF);
}

// Five columns, seven rows (Framegen/StatsOverlay's alphabet).
const uint8_t* Glyph(char c) {
    static constexpr uint8_t digits[][5]={{62,81,73,69,62},{0,66,127,64,0},{66,97,81,73,70},{33,65,69,75,49},{24,20,18,127,16},
        {39,69,69,69,57},{60,74,73,73,48},{1,113,9,5,3},{54,73,73,73,54},{6,73,73,41,30}};
    static constexpr uint8_t letters[][5]={{126,17,17,17,126},{127,73,73,73,54},{62,65,65,65,34},{127,65,65,34,28},
        {127,73,73,73,65},{127,9,9,9,1},{62,65,73,73,122},{127,8,8,8,127},{0,65,127,65,0},{32,64,65,63,1},
        {127,8,20,34,65},{127,64,64,64,64},{127,2,12,2,127},{127,4,8,16,127},{62,65,65,65,62},{127,9,9,9,6},
        {62,65,81,33,94},{127,9,25,41,70},{70,73,73,73,49},{1,1,127,1,1},{63,64,64,64,63},{31,32,64,32,31},
        {63,64,56,64,63},{99,20,8,20,99},{7,8,112,8,7},{97,81,73,69,67}};
    static constexpr uint8_t blank[]={0,0,0,0,0},dot[]={0,96,96,0,0},dash[]={8,8,8,8,8};
    static constexpr uint8_t percent[]={99,19,8,100,99},colon[]={0,54,54,0,0},slash[]={32,16,8,4,2};
    if(c>='a' && c<='z')c=static_cast<char>(c-'a'+'A');
    if(c>='0' && c<='9')return digits[c-'0'];if(c>='A' && c<='Z')return letters[c-'A'];
    if(c=='%')return percent;if(c==':')return colon;if(c=='/')return slash;
    return c=='.' ? dot : (c=='-' ? dash : blank);
}
struct Canvas {
    uint32_t* pixels;int width,height;
    void Rect(int x,int y,int w,int h,uint32_t color) {
        for(int row=std::max(0,y);row<std::min(height,y+h);++row)
            if(x<width && x+w>0)std::fill(pixels+row*width+std::max(0,x),pixels+row*width+std::min(width,x+w),color);
    }
    void Text(int x,int y,const std::string& text,uint32_t color,int scale) {
        for(const char* p=text.c_str();*p && x+5*scale<=width;++p,x+=6*scale) {
            const auto* glyph=Glyph(*p);
            for(int col=0;col<5;++col)for(int row=0;row<7;++row)if(glyph[col]&(1u<<row))
                Rect(x+col*scale,y+row*scale,scale,scale,color);
        }
    }
    int Width(const std::string& text,int scale) const { return int(text.size())*6*scale; }
};
int GaugeHeight(const Gauge& g) { return 44+g.bars*30+10; }
void Draw(Canvas c,const Gauge* live[],int count) {
    std::fill(c.pixels,c.pixels+c.width*c.height,0u);
    int y=0;
    for(int i=0;i<count;++i) {
        const Gauge& g=*live[i];const int h=GaugeHeight(g);
        c.Rect(0,y,c.width,h,0xE0120D0Au);                 // the plate
        c.Rect(0,y,5,h,g.accent);                          // its edge
        c.Text(16,y+12,g.title,g.accent,3);
        c.Text(c.width-14-c.Width(g.state,2),y+16,g.state,0xFFF0E6D4u,2);
        for(int b=0;b<g.bars;++b) {
            const int by=y+44+b*30,trackW=c.width-16-118;
            c.Rect(16,by+8,trackW,12,0xFF261C16u);
            const int fill=int(std::clamp(g.v[b],0.0f,1.0f)*trackW);
            if(fill>0)c.Rect(16,by+8,fill,12,g.c[b]);
            c.Text(c.width-14-c.Width(g.t[b],3),by+3,g.t[b],0xFFF2F2F2u,3);
        }
        y+=h+8;
    }
}
std::vector<std::string> Split(const std::string& s) {
    std::vector<std::string> out;size_t start=0;
    for(;;){const size_t tab=s.find('\t',start);out.push_back(s.substr(start,tab==std::string::npos?std::string::npos:tab-start));
        if(tab==std::string::npos)break;start=tab+1;}
    return out;
}
}

void VRWristGauge(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t) {
    int32_t slot=0;RED4ext::CString spec;
    RED4ext::GetParameter(aFrame,&slot);
    RED4ext::GetParameter(aFrame,&spec);
    aFrame->code++;
    if(slot<0 || slot>=MaxSlots)return;
    const std::string text=spec.c_str();
    std::lock_guard lock(mtx);
    Gauge& g=gauges[slot];
    if(text.empty()){g=Gauge{};++serial;return;}
    const auto f=Split(text);
    Gauge n;n.title=f.size()>0?f[0]:"";n.state=f.size()>1?f[1]:"";n.accent=Colour(f.size()>2?f[2]:"",0xFFFFDC6Eu);
    for(size_t i=3;i+2<f.size()+0 && n.bars<MaxBars;i+=3) {
        n.v[n.bars]=static_cast<float>(std::atof(f[i].c_str()));n.t[n.bars]=f[i+1];n.c[n.bars]=Colour(f[i+2],0xFFFFDC6Eu);++n.bars;
    }
    n.at=GetTickCount64();
    const bool same=g.at && g.title==n.title && g.state==n.state && g.accent==n.accent && g.bars==n.bars &&
        std::equal(g.t,g.t+MaxBars,n.t) && std::equal(g.c,g.c+MaxBars,n.c) &&
        [&]{for(int b=0;b<n.bars;++b)if(std::fabs(g.v[b]-n.v[b])>0.002f)return false;return true;}();
    g=n;
    if(!same)++serial;
}

void VRWristHudPlace(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t) {
    float x=0,y=0,z=0,tilt=0,width=0;
    RED4ext::GetParameter(aFrame,&x);RED4ext::GetParameter(aFrame,&y);RED4ext::GetParameter(aFrame,&z);
    RED4ext::GetParameter(aFrame,&tilt);RED4ext::GetParameter(aFrame,&width);
    aFrame->code++;
    std::lock_guard lock(mtx);
    place.x=std::clamp(x,-0.3f,0.3f);place.y=std::clamp(y,-0.3f,0.3f);place.z=std::clamp(z,-0.3f,0.5f);
    place.tilt=std::clamp(tilt,-90.0f,180.0f);place.width=std::clamp(width,0.04f,0.4f);
}

// [VRGestures fork] 52: the mailboxes (see the header). A handful of short texts, so one lock and a map.
namespace {
struct Box { std::string text;uint64_t at=0; };
std::mutex mailMtx;
std::map<std::string,Box> mail;
constexpr size_t MaxBoxText=16384;
}

void VRGMailPut(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t) {
    RED4ext::CString box,text;
    RED4ext::GetParameter(aFrame,&box);RED4ext::GetParameter(aFrame,&text);
    aFrame->code++;
    std::lock_guard lock(mailMtx);
    Box& b=mail[box.c_str()];
    b.text.assign(text.c_str());if(b.text.size()>MaxBoxText)b.text.resize(MaxBoxText);
    b.at=GetTickCount64();
}

void VRGMailAdd(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, void*, int64_t) {
    RED4ext::CString box,line;
    RED4ext::GetParameter(aFrame,&box);RED4ext::GetParameter(aFrame,&line);
    aFrame->code++;
    std::lock_guard lock(mailMtx);
    Box& b=mail[box.c_str()];
    if(b.text.size()+std::strlen(line.c_str())+1>MaxBoxText)return;
    b.text.append(line.c_str());b.text.push_back('\n');
    b.at=GetTickCount64();
}

void VRGMailGet(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, RED4ext::CString* aOut, int64_t) {
    RED4ext::CString box;int32_t maxAgeMs=0;
    RED4ext::GetParameter(aFrame,&box);RED4ext::GetParameter(aFrame,&maxAgeMs);
    aFrame->code++;
    if(!aOut)return;
    std::string text;
    {
        std::lock_guard lock(mailMtx);
        const auto it=mail.find(box.c_str());
        if(it!=mail.end() && (maxAgeMs<=0 || GetTickCount64()-it->second.at<=static_cast<uint64_t>(maxAgeMs)))text=it->second.text;
    }
    *aOut=RED4ext::CString(text.c_str());
}

void VRGMailTake(RED4ext::IScriptable*, RED4ext::CStackFrame* aFrame, RED4ext::CString* aOut, int64_t) {
    RED4ext::CString box;
    RED4ext::GetParameter(aFrame,&box);
    aFrame->code++;
    std::string text;
    {
        std::lock_guard lock(mailMtx);
        const auto it=mail.find(box.c_str());
        if(it!=mail.end()){text.swap(it->second.text);it->second.at=GetTickCount64();}
    }
    if(aOut)*aOut=RED4ext::CString(text.c_str());
}

const XrCompositionLayerBaseHeader* Quad::Prepare(XrSession session,XrSpace hand,ID3D12Device* device,ID3D12CommandQueue* queue) {
    if(!device || !queue || !session || !hand)return nullptr;
    // the live gauges, in slot order
    Gauge copy[MaxSlots];const Gauge* live[MaxSlots]{};int count=0;uint64_t key;Place where;
    {
        std::lock_guard lock(mtx);
        const uint64_t now=GetTickCount64();
        for(int i=0;i<MaxSlots;++i)if(gauges[i].at && now-gauges[i].at<TtlMs){copy[count]=gauges[i];live[count]=&copy[count];++count;}
        key=serial*8+count;where=place;
    }
    if(!count) {published=false;drawnSerial=~0ull;return nullptr;}   // redrawn whenever a gauge comes back
    if(!swapchain) {
        rowPitch=(W*4+255)&~255u;pixels.resize(size_t(W)*H);
        uint32_t n{};if(XR_FAILED(xrEnumerateSwapchainFormats(session,0,&n,nullptr)))return nullptr;
        std::vector<int64_t> formats(n);if(XR_FAILED(xrEnumerateSwapchainFormats(session,n,&n,formats.data())))return nullptr;
        if(std::find(formats.begin(),formats.end(),DXGI_FORMAT_R8G8B8A8_UNORM_SRGB)==formats.end())return nullptr;
        XrSwapchainCreateInfo info{XR_TYPE_SWAPCHAIN_CREATE_INFO};info.usageFlags=XR_SWAPCHAIN_USAGE_TRANSFER_DST_BIT|XR_SWAPCHAIN_USAGE_SAMPLED_BIT|XR_SWAPCHAIN_USAGE_COLOR_ATTACHMENT_BIT;
        info.format=DXGI_FORMAT_R8G8B8A8_UNORM_SRGB;info.sampleCount=1;info.width=W;info.height=H;info.faceCount=1;info.arraySize=1;info.mipCount=1;
        if(XR_FAILED(xrCreateSwapchain(session,&info,&swapchain)))return nullptr;
        if(XR_FAILED(xrEnumerateSwapchainImages(swapchain,0,&n,nullptr))) {Shutdown();return nullptr;}
        images.assign(n,{XR_TYPE_SWAPCHAIN_IMAGE_D3D12_KHR});
        if(XR_FAILED(xrEnumerateSwapchainImages(swapchain,n,&n,reinterpret_cast<XrSwapchainImageBaseHeader*>(images.data()))) ||
           FAILED(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator))) ||
           FAILED(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),nullptr,IID_PPV_ARGS(&list))) ||
           FAILED(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence)))) {Shutdown();return nullptr;}
        list->Close();D3D12_RESOURCE_DESC desc{};desc.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;desc.Width=rowPitch*H;
        desc.Height=1;desc.DepthOrArraySize=1;desc.MipLevels=1;desc.SampleDesc.Count=1;desc.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
        D3D12_HEAP_PROPERTIES heap{};heap.Type=D3D12_HEAP_TYPE_UPLOAD;
        if(FAILED(device->CreateCommittedResource(&heap,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,IID_PPV_ARGS(&upload)))) {Shutdown();return nullptr;}
        drawnSerial=~0ull;
    }
    const double now=double(GetTickCount64());
    if((key!=drawnSerial || acquired) && now>=nextUpdate && fence->GetCompletedValue()>=fenceValue) {
        if(!acquired) {XrSwapchainImageAcquireInfo info{XR_TYPE_SWAPCHAIN_IMAGE_ACQUIRE_INFO};if(XR_SUCCEEDED(xrAcquireSwapchainImage(swapchain,&info,&acquiredIndex)))acquired=true;}
        if(acquired) {
            XrSwapchainImageWaitInfo wait{XR_TYPE_SWAPCHAIN_IMAGE_WAIT_INFO};wait.timeout=0;
            if(xrWaitSwapchainImage(swapchain,&wait)==XR_SUCCESS) {
                void* data{};D3D12_RANGE none{};
                if(SUCCEEDED(upload->Map(0,&none,&data))) {
                    Draw({pixels.data(),int(W),int(H)},live,count);
                    int used=0;for(int i=0;i<count;++i)used+=GaugeHeight(*live[i])+(i?8:0);
                    for(uint32_t row=0;row<H;++row)std::memcpy(static_cast<uint8_t*>(data)+size_t(row)*rowPitch,pixels.data()+size_t(row)*W,size_t(W)*4);
                    upload->Unmap(0,nullptr);
                    if(SUCCEEDED(allocator->Reset()) && SUCCEEDED(list->Reset(allocator.Get(),nullptr))) {
                        auto* target=images[acquiredIndex].texture;
                        D3D12_RESOURCE_BARRIER b{};b.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
                        b.Transition={target,D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES,D3D12_RESOURCE_STATE_RENDER_TARGET,D3D12_RESOURCE_STATE_COPY_DEST};list->ResourceBarrier(1,&b);
                        D3D12_TEXTURE_COPY_LOCATION src{},dst{};src.pResource=upload.Get();src.Type=D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
                        src.PlacedFootprint.Footprint={target->GetDesc().Format,W,H,1,rowPitch};dst.pResource=target;dst.Type=D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
                        list->CopyTextureRegion(&dst,0,0,0,&src,nullptr);std::swap(b.Transition.StateBefore,b.Transition.StateAfter);list->ResourceBarrier(1,&b);
                        if(SUCCEEDED(list->Close())) {ID3D12CommandList* lists[]={list.Get()};queue->ExecuteCommandLists(1,lists);queue->Signal(fence.Get(),++fenceValue);
                            published=true;drawnSerial=key;usedHeight=uint32_t(std::clamp(used,1,int(H)));nextUpdate=now+100;}
                    }
                }
                XrSwapchainImageReleaseInfo release{XR_TYPE_SWAPCHAIN_IMAGE_RELEASE_INFO};
                if(XR_FAILED(xrReleaseSwapchainImage(swapchain,&release)))published=false;
                acquired=false;
            }
        }
    }
    if(!published || !usedHeight)return nullptr;
    // in the left aim space: +y up off the controller, +z back toward the elbow. Tilt 0 = lying flat facing up,
    // 90 = standing up facing back along the arm (toward the face when the wrist is raised to look at it)
    constexpr float radians=.01745329252f;
    const float a=-(90.0f-where.tilt)*radians;
    layer.space=hand;layer.eyeVisibility=XR_EYE_VISIBILITY_BOTH;layer.layerFlags=XR_COMPOSITION_LAYER_BLEND_TEXTURE_SOURCE_ALPHA_BIT;
    layer.subImage={swapchain,{{0,0},{int32_t(W),int32_t(usedHeight)}},0};
    layer.pose={{std::sin(a*.5f),0,0,std::cos(a*.5f)},{where.x,where.y,where.z}};
    layer.size={where.width,where.width*float(usedHeight)/float(W)};
    return reinterpret_cast<const XrCompositionLayerBaseHeader*>(&layer);
}

void Quad::Shutdown(bool wait) {
    if(!swapchain && !fence && pixels.empty())return;
    if(wait && fence && fence->GetCompletedValue()<fenceValue) {
        const auto event=CreateEventW(nullptr,FALSE,FALSE,nullptr);
        if(event) {if(SUCCEEDED(fence->SetEventOnCompletion(fenceValue,event)))WaitForSingleObject(event,1000);CloseHandle(event);}
    }
    if(fence && fence->GetCompletedValue()<fenceValue)return;
    if(acquired && swapchain) {
        XrSwapchainImageWaitInfo ready{XR_TYPE_SWAPCHAIN_IMAGE_WAIT_INFO};ready.timeout=0;
        if(xrWaitSwapchainImage(swapchain,&ready)!=XR_SUCCESS)return;
        XrSwapchainImageReleaseInfo release{XR_TYPE_SWAPCHAIN_IMAGE_RELEASE_INFO};
        if(XR_FAILED(xrReleaseSwapchainImage(swapchain,&release)))return;
        acquired=false;
    }
    if(swapchain) {xrDestroySwapchain(swapchain);swapchain=XR_NULL_HANDLE;}
    std::vector<XrSwapchainImageD3D12KHR>().swap(images);upload.Reset();allocator.Reset();list.Reset();fence.Reset();
    fenceValue=0;nextUpdate=0;acquired=published=false;usedHeight=0;drawnSerial=0;
    std::vector<uint32_t>().swap(pixels);rowPitch=0;
}
}
