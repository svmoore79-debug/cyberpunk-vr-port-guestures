-- [VRGestures fork] 37: THE QUICKSLOT WHEEL. A ring of the player's Custom Quickslots slots, opened by VRGestures when
-- the LEFT hand swipes down with its grip held (the port's own menu swipe, read on the left hand: VRGLeftSwipe). It
-- stands where the hand stopped, square to the eyes. The hand reaches into a slot -- it lights and ticks -- and letting
-- go of the grip there uses it; the empty centre is "cancel". VRGestures owns the slots and the use; this draws the
-- ring and says which slot the hand is over.
--
-- The screen is the menu's own plane entity (vr_menu.ent, 1.00 x 0.50 m), a second instance of it, with a matte round
-- backplate (vr_menu_icon.ent) behind each slot so the additive light reads over a bright street. The hand is the left
-- index knuckle as the VR menu's pointer native reports it, projected onto the plane.

local K = require("modules/ink")
local Images = require("modules/gameplay_data")

local Q = {}

local ENT = "vrport\\ui\\vr_menu.ent"
local PLATE_ENT = "vrport\\ui\\vr_menu_icon.ent"
local UI = "vrp_menu_ui"
local CW, CH, PX = 3200, 1600, 3200        -- canvas pixels, pixels per metre
local W, H = CW / PX, CH / PX

-- metres from the centre to a slot's centre, and a slot's diameter: for up to 12 slots; more widen the ring (to what
-- the screen holds) and then shrink the slots so they never overlap (S.ring, S.slot, set on open)
local RING, RING_MAX = 0.17, 0.20
local SLOT = 0.085
local HUB = 0.065       -- the centre's radius: cancel
local REACH = 0.20      -- how far in front of or behind the plane the hand still counts
local PLATE_BACK = 0.0006

local S = { open = false }

local function add(a, b) return { a[1] + b[1], a[2] + b[2], a[3] + b[3] } end
local function sub(a, b) return { a[1] - b[1], a[2] - b[2], a[3] - b[3] } end
local function mul(a, s) return { a[1] * s, a[2] * s, a[3] * s } end
local function dot(a, b) return a[1] * b[1] + a[2] * b[2] + a[3] * b[3] end
local function cross(a, b)
  return { a[2] * b[3] - a[3] * b[2], a[3] * b[1] - a[1] * b[3], a[1] * b[2] - a[2] * b[1] }
end
local function norm(a)
  local n = math.sqrt(dot(a, a))
  if n < 1e-6 then return { 0, 0, 0 }, 0 end
  return mul(a, 1 / n), n
end

-- The rotation whose columns are the world images of the local X, Y and Z axes (menu.lua's).
local function quatFromBasis(X, Y, Z)
  local m00, m01, m02 = X[1], Y[1], Z[1]
  local m10, m11, m12 = X[2], Y[2], Z[2]
  local m20, m21, m22 = X[3], Y[3], Z[3]
  local tr = m00 + m11 + m22
  local qx, qy, qz, qw
  if tr > 0 then
    local s = math.sqrt(tr + 1.0) * 2
    qw, qx, qy, qz = 0.25 * s, (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s
  elseif m00 > m11 and m00 > m22 then
    local s = math.sqrt(1.0 + m00 - m11 - m22) * 2
    qw, qx, qy, qz = (m21 - m12) / s, 0.25 * s, (m01 + m10) / s, (m02 + m20) / s
  elseif m11 > m22 then
    local s = math.sqrt(1.0 + m11 - m00 - m22) * 2
    qw, qx, qy, qz = (m02 - m20) / s, (m01 + m10) / s, 0.25 * s, (m12 + m21) / s
  else
    local s = math.sqrt(1.0 + m22 - m00 - m11) * 2
    qw, qx, qy, qz = (m10 - m01) / s, (m02 + m20) / s, (m12 + m21) / s, 0.25 * s
  end
  return Quaternion.new(qx, qy, qz, qw)
end

-- A plane entity with its canvas right along R and canvas up along U, centred on C (menu.lua's transformFor).
local function transformFor(C, R, U)
  local tr = WorldTransform.new()
  tr:SetPosition(Vector4.new(C[1], C[2], C[3], 1.0))
  tr:SetOrientation(quatFromBasis(mul(R, -1), mul(U, -1), cross(R, U)))
  return tr
end

local function headPos()
  local p = nil
  pcall(function()
    local wp = VRViewWorldPos()
    if wp ~= nil and wp.w ~= nil and wp.w > 0.5 then p = { wp.x, wp.y, wp.z } end
  end)
  return p
end

-- The left index knuckle in the world, from the menu pointer native (any plane will do for its origin).
local function leftHand()
  if type(VRMenuPointer) ~= "function" then return nil end
  local out = nil
  pcall(function()
    out = VRMenuPointer(Vector4.new(0, 0, 0, 1), Vector4.new(1, 0, 0, 0), Vector4.new(0, 0, 1, 0), Vector4.new(W, H, 0, 0))
  end)
  if out == nil or #out < 8 then return nil end
  local o = out[3]
  if o == nil or (o.x == 0 and o.y == 0 and o.z == 0) then return nil end
  return { o.x, o.y, o.z }
end

local function spawn(path, tr)
  local id = nil
  pcall(function() id = exEntitySpawner.Spawn(path, tr, "") end)
  return { id = id }
end

local function despawn(h)
  if h == nil or h.id == nil then return end
  pcall(function()
    local e = Game.FindEntityByID(h.id)
    if e ~= nil then exEntitySpawner.Despawn(e) end
  end)
  h.id = nil
end

local function resolve(h)
  if h.root ~= nil then return true end
  pcall(function()
    h.entity = Game.FindEntityByID(h.id)
    if h.entity ~= nil then h.comp = h.entity:FindComponentByName(CName.new(UI)) end
    if h.comp ~= nil then h.root = h.comp:GetWidget() end
  end)
  return h.root ~= nil
end

local function ready(h)
  if h.ready then return true end
  if h.comp == nil or h.root == nil or type(VRMenuSurfaceReady) ~= "function" then return false end
  local ok, done = pcall(VRMenuSurfaceReady, h.comp, h.root)
  if not ok or not done then return false end
  local display = h.entity:FindComponentByName(CName.new("display"))
  if display == nil then return false end
  h.ready = pcall(function() display:Toggle(true) end)
  return h.ready
end

local function slotXY(i, n)
  local a = math.pi / 2 - (i - 1) * 2 * math.pi / n     -- the first at the top, clockwise
  return S.ring * math.cos(a), S.ring * math.sin(a)
end

local function canvasXY(x, y) return CW / 2 + x * PX, CH / 2 - y * PX end

local function iconFor(tdbid)
  if tdbid == nil then return nil end
  local icon = nil
  pcall(function()
    local name = NameToString(IconsNameResolver.GetIconsNameResolver():TranslateItemToIconName(tdbid, true))
    if name ~= "" and name ~= "None" then icon = Images.image(TweakDBID.new("UIIcon." .. name)) end
  end)
  return icon
end

local function build()
  local root = S.screen.root
  root:RemoveAllChildren()
  local n = #S.slots
  local d = S.slot * PX
  S.rings = {}
  -- the hub: cancel, and the name of what the hand is over
  local hx, hy = canvasXY(0, 0)
  K.ring(root, hx, hy, HUB * PX, 3, K.CYAN, 0.55, 40)
  S.hubText = K.text(root, hx - 300, hy - 60, 600, 120, "CANCEL", 44, K.TEXT, "center")
  for i, s in ipairs(S.slots) do
    local x, y = slotXY(i, n)
    local cx, cy = canvasXY(x, y)
    S.rings[i] = K.ring(root, cx, cy, d / 2, 4, s.empty and K.GREY or K.CYAN, s.empty and 0.5 or 0.9, 40)
    local icon = iconFor(s.item)
    if icon ~= nil then
      K.image(root, cx - d * 0.30, cy - d * 0.36, d * 0.60, d * 0.50, icon.atlas, icon.part, K.WHITE, s.empty and 0.35 or 1.0)
    end
    K.text(root, cx - d / 2, cy + d * 0.14, d, d * 0.22, K.clip(s.short or s.label, 13), 26, s.empty and K.GREY or K.TEXT, "center")
    if s.count and s.count > 1 then
      K.text(root, cx + d * 0.10, cy - d * 0.48, d * 0.40, d * 0.20, "x" .. tostring(s.count), 28, K.YELLOW, "center")
    end
  end
  S.screen.built = true
end

local function plates()
  local N = cross(S.R, S.U)
  for i = 1, #S.slots do
    local x, y = slotXY(i, #S.slots)
    local C = add(add(add(S.C, mul(S.R, x)), mul(S.U, y)), mul(N, -PLATE_BACK))
    local h = spawn(PLATE_ENT, transformFor(C, S.R, S.U))
    h.scale = S.slot * 0.98
    S.plates[i] = h
  end
end

local function showPlates()
  for _, h in ipairs(S.plates) do
    if not h.shown and h.id ~= nil then
      pcall(function()
        h.entity = h.entity or Game.FindEntityByID(h.id)
        local c = h.entity and h.entity:FindComponentByName(CName.new("display"))
        if c ~= nil then
          c.visualScale = Vector3.new(h.scale, h.scale, 1.0)
          c:Toggle(true)
          h.shown = true
        end
      end)
    end
  end
end

-- slots: { { index, label, short, item (TweakDBID or nil), count, empty }, ... } in wheel order.
function Q.open(slots)
  if S.open then Q.close() end
  if slots == nil or #slots == 0 or type(VRMenuSurfaceReady) ~= "function" then return false end
  local head, hand = headPos(), leftHand()
  if head == nil or hand == nil then return false end
  local N = norm(sub(head, hand))
  local up = { 0, 0, 1 }
  local U = norm(sub(up, mul(N, dot(up, N))))
  local R = cross(U, N)
  S.C, S.R, S.U = hand, R, U
  S.slots, S.hover, S.plates = slots, -1, {}
  local n = #slots
  S.ring = math.min(RING_MAX, math.max(RING, n * SLOT * 1.1 / (2 * math.pi)))
  S.slot = math.min(SLOT, 2 * math.pi * S.ring / n * 0.9)
  S.screen = spawn(ENT, transformFor(S.C, S.R, S.U))
  S.open, S.placed = true, false
  plates()
  return true
end

function Q.close()
  if not S.open then return end
  S.open = false
  despawn(S.screen)
  S.screen = nil
  for _, h in ipairs(S.plates or {}) do despawn(h) end
  S.plates = {}
  S.hover = -1
end

function Q.isOpen() return S.open end

-- -1 = nowhere on the wheel, 0 = the centre (cancel), i = the i-th slot as given to open
function Q.hover() return S.open and S.hover or -1 end

local function setHover(k)
  if k == S.hover then return end
  if S.hover > 0 and S.rings[S.hover] then
    local s = S.slots[S.hover]
    K.tint(S.rings[S.hover], s.empty and K.GREY or K.CYAN, s.empty and 0.5 or 0.9)
  end
  S.hover = k
  if k > 0 and S.rings[k] then
    K.tint(S.rings[k], K.YELLOW, 1.0)
    S.hubText:SetText(S.slots[k].label)
    S.hubText:SetTintColor(K.color(K.YELLOW))
  else
    S.hubText:SetText("CANCEL")
    S.hubText:SetTintColor(K.color(k == 0 and K.YELLOW or K.TEXT))
  end
  if k >= 0 and type(VRHapticEvent) == "function" then pcall(VRHapticEvent, 21, 1) end
end

function Q.update(dt)
  if not S.open or S.screen == nil or S.screen.id == nil then return end
  if not resolve(S.screen) then return end
  pcall(function() if S.screen.comp.glitchValue ~= 0 then S.screen.comp.glitchValue = 0.0 end end)
  if not S.screen.built then build() end
  if not S.placed and ready(S.screen) then
    pcall(function() S.screen.entity:SetWorldTransform(transformFor(S.C, S.R, S.U)) end)
    S.placed = true
  end
  if not S.placed then return end
  showPlates()
  local hand = leftHand()
  if hand == nil then setHover(-1) return end
  local l = sub(hand, S.C)
  local x, y, d = dot(l, S.R), dot(l, S.U), dot(l, cross(S.R, S.U))
  if math.abs(d) > REACH then setHover(-1) return end
  local r = math.sqrt(x * x + y * y)
  if r < HUB then setHover(0) return end
  local n = #S.slots
  local best, bestD = -1, S.slot * 0.75
  for i = 1, n do
    local sx, sy = slotXY(i, n)
    local dd = math.sqrt((x - sx) ^ 2 + (y - sy) ^ 2)
    if dd < bestD then best, bestD = i, dd end
  end
  setHover(best)
end

return Q
