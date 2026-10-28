local values, watchers, jobs = {}, {}, {}
local settings = {api_address="127.0.0.1:9095",api_key_file="/example/api-key",thronectl_path="thronectl",poll_seconds=3}
local lastInterval = 0
local visible = false
local panelEntry
local tree, icon, tint, tooltip
local function copy(x)
    if type(x) ~= "table" then return x end
    local y = {}
    for k,v in pairs(x) do y[k] = copy(v) end
    return y
end
local profiles = {
    { id=101, name="Same", type="xrayvless", country="—", latency_ms=33,
      download_bps=100000000,upload_bps=40000000,ping="12 ms",download="100.00 Mbps",upload="40.00 Mbps",traffic_up_text="1.0 MiB",traffic_down_text="5.0 MiB" },
    { id=102, name="Same", type="vless", country="—", latency_ms=46,
      download_bps=80000000,upload_bps=20000000,ping="24 ms",download="80.00 Mbps",upload="20.00 Mbps",traffic_up_text="0 B",traffic_down_text="0 B" },
}
local idle = { ok=true, profiles=profiles, status={state="idle",tun=false,last_profile_id=102,route={id=2,name="Default"}} }
local running = { ok=true, profiles=profiles, status={state="running",tun=true,last_profile_id=102,profile={id=102,name="Same"},route={id=2,name="Default"}} }
local fixtures = {
    idle=idle, running=running,
    denied={ok=false,error="TUN privileges missing."},
    offline={ok=false,error="Throne unavailable."},
}
local translations = {
 ["settings.api_address.label"]="Throne API address",
 ["settings.api_address.description"]="Local API endpoint. Keep Throne on loopback unless you deliberately configure a secure remote connection.",
 ["settings.api_key_file.label"]="API key file",
 ["settings.api_key_file.description"]="Path to the existing key file configured in Throne. Do not paste the key value.",
 ["settings.thronectl_path.label"]="thronectl executable",
 ["settings.thronectl_path.description"]="Executable on PATH, or a full path. A leading ~ is expanded by the helper.",
 ["settings.poll_seconds.label"]="Refresh interval (seconds)",
 ["settings.poll_seconds.description"]="Read status and stored test results every 2–60 seconds. No new speed tests are started.",
 ["errors.timeout"]="Throne timed out or returned an incomplete response.",
 ["errors.command"]="Throne did not complete the action.",
 ["errors.response"]="Could not read Throne. Check python3, thronectl and plugin settings.",
 ["errors.launch"]="Could not launch the bundled Python helper.",
 ["panel.subtitle"]="VPN profiles",
 ["panel.refresh"]="Refresh saved results",
 ["panel.close"]="Close",
 ["panel.choose"]="Select a server below",
 ["panel.current_route"]="Current Throne setting",
 ["panel.disconnect"]="Disconnect",
 ["panel.last"]="Last profile",
 ["panel.search"]="Find a profile…",
 ["panel.server"]="Server · download order",
 ["panel.empty"]="No matching profiles",
 ["panel.waiting"]="Waiting for Throne…",
 ["panel.footer"]="Saved Throne tests · download descending · Σ = accumulated traffic",
 ["panel.route_prefix"]="Route: ",
 ["panel.degraded_prefix"]="Throne reports a problem: ",
 ["panel.permissions"]="ThroneCore needs TUN privileges. Grant them in Throne; see the permissions guide.",
 ["status.off"]="VPN disconnected",
 ["status.unavailable"]="Throne unavailable",
 ["status.busy"]="Applying action…",
 ["status.connecting"]="Connecting…",
 ["status.stopping"]="Disconnecting…",
 ["status.tun"]="VPN connected · TUN",
 ["status.proxy"]="Proxy running · TUN disabled",
 ["status.loading"]="Connecting to the Throne API…",
 ["widget.off"]="Throne · VPN disconnected",
 ["widget.loading"]="Throne · loading…",
 ["widget.busy"]="Throne · action in progress…",
 ["widget.degraded"]="Throne · degraded connection",
 ["widget.unavailable"]="unavailable",
 ["widget.proxy_prefix"]="Proxy · ",
 ["widget.controls"]="Left click: open/close · Right click: close",
}
noctalia = {
    pluginDir = function() return "/example/plugin" end,
    getConfig = function(key) assert(settings[key] ~= nil); return settings[key] end,
    tr = function(key) assert(translations[key],key); return translations[key] end,
    state = {
        get = function(key) return copy(values[key]) end,
        set = function(key, value)
            values[key] = copy(value)
            for _, fn in ipairs(watchers[key] or {}) do fn(copy(value)) end
        end,
        watch = function(key, fn)
            watchers[key] = watchers[key] or {}
            table.insert(watchers[key], fn)
        end,
    },
    json = { decode = function(s) return copy(fixtures[s]) end },
    runAsync = function(argv, callback)
        assert(type(argv)=="table", "Shell command used instead of argv")
        assert(argv[1]=="python3" and argv[2]=="/example/plugin/backend.py")
        table.insert(jobs,{argv=argv,cb=callback})
        return true
    end,
    setUpdateInterval = function(ms) assert(ms>=2000 and ms<=60000); lastInterval=ms end,
    fuzzyScore = function(query, name) return name:find(query,1,true) end,
    togglePanel = function(id)
        assert(id=="__PLUGIN_ID__:panel")
        visible = not visible
        if visible then panelEntry.onOpen() else panelEntry.onClose() end
    end,
}
barWidget = {
    setGlyph=function(x) icon=x end,
    setGlyphColor=function(x) tint=x end,
    setText=function(x) assert(x=="") end,
    setTooltip=function(x) tooltip=x end,
}
panel = {
    render=function(x) tree=x end,
    close=function()
        if visible then visible=false; panelEntry.onClose() end
    end,
}
local common = {key=true,width=true,height=true,flexGrow=true,opacity=true,visible=true}
local schemas = {
    row="gap padding paddingH paddingV align justify fill radius border borderWidth minWidth minHeight onClick onHover",
    column="gap padding paddingH paddingV align justify fill radius border borderWidth minWidth minHeight onClick onHover",
    scroll="gap padding paddingH paddingV align justify fill radius border borderWidth minWidth minHeight",
    label="text fontSize color fontWeight fontFamily maxWidth maxLines textAlign",
    glyph="name size color",
    button="text glyph fontSize glyphSize variant contentAlign controlSize tooltip enabled selected onClick onRightClick onHover",
    input="value placeholder fontSize controlSize password multiline submitOnEnter frameVisible focus enabled onChange onSubmit",
}
ui = {}
for kind, fields in pairs(schemas) do
    local name = kind
    local allowed=copy(common)
    for key in fields:gmatch("%S+") do allowed[key]=true end
    ui[name]=function(props,children)
        for key in pairs(props) do assert(allowed[key], name .. ": undocumented prop " .. key) end
        return {kind=name,props=props,children=children or {}}
    end
end
local function loadEntry(file)
    local env=setmetatable({}, {__index=_G})
    local chunk, err=loadfile("__PLUGIN_ROOT__/" .. file,"t",env)
    assert(chunk,err)
    chunk()
    return env
end
local function done(job,token,exitCode)
    assert(job and job.cb, "missing async job")
    local fn=job.cb
    job.cb=nil
    fn({stdout=token,stderr="",exitCode=exitCode or 0,timedOut=false})
end
local function find(node, predicate)
    if predicate(node) then return node end
    for _,child in ipairs(node.children or {}) do
        local result=find(child,predicate)
        if result then return result end
    end
end
local function key(k) return find(tree,function(n) return n.props.key==k end) end
local function textContains(s)
    return find(tree,function(n) return type(n.props.text)=="string" and n.props.text:find(s,1,true) end)
end

local widget=loadEntry("widget.luau")
panelEntry=loadEntry("panel.luau")
assert(icon=="loader")
local service=loadEntry("service.luau")
assert(#jobs==1 and jobs[1].argv[#jobs[1].argv]=="--snapshot")
done(jobs[1],"idle")
assert(icon=="shield-off")
widget.onClick()
assert(visible and tree)
local scroll=key("profiles-flex")
assert(#scroll.children==2 and scroll.children[1].props.key=="profile-101")
assert(textContains("100.00 Mbps") and textContains("12 ms") and textContains("5.0 MiB"))
assert(#jobs==2, "opening should refresh")
key("profile-102").props.onClick()
assert(values.busy==true and #jobs==3)
assert(jobs[3].argv[6]=="--connect" and jobs[3].argv[7]=="102")
-- Action is immediate, and an older poll is not allowed to overwrite its status.
done(jobs[3],"running")
assert(icon=="shield-check" and tint=="primary")
assert(tooltip:find("80.00 Mbps",1,true))
done(jobs[2],"idle")
assert(icon=="shield-check" and #jobs==4)
done(jobs[4],"running")
assert(icon=="shield-check")
key("profile-102").props.onClick()
assert(#jobs==4, "active profile click should not reconnect")
key("profile-101").props.onClick()
assert(#jobs==5 and jobs[5].argv[7]=="101")
done(jobs[5],"denied",1)
assert(values.busy==false and textContains("TUN privileges missing"))
assert(#jobs==6)
done(jobs[6],"offline",1)
assert(icon=="alert-circle" and textContains("Throne unavailable"))
-- Both pointer actions close; right click while closed cannot reopen or toggle VPN.
widget.onClick()
assert(not visible)
widget.onRightClick()
assert(not visible and #jobs==6)
widget.onClick()
assert(visible)
local requestsBefore=#jobs
widget.onRightClick()
assert(not visible and #jobs==requestsBefore)
widget.onClick()
assert(visible)
local search=key("search")
search.props.onChange("NO MATCH")
assert(textContains("No matching profiles") or textContains("Waiting for Throne"))
panel.close()
assert(not visible)

-- Verify the render hands the viewport's height to the host through every
-- parent. This mock does not calculate layout or deliver real pointer events.
-- A separate headless investigation exercised the v5.3.0 C++ implementation.
local function checkViewportContract()
    assert(tree.props.flexGrow == 1 and tree.props.height == nil, "root must receive the host height")
    local viewport = key("profiles-flex")
    assert(viewport.kind == "scroll" and viewport.props.flexGrow == 1)
    assert(viewport.props.height == nil, "scroll height min/max are ignored by Noctalia 5.3")
    assert(tree.children[#tree.children].props.key == "footer", "footer must stay outside the scroll view")
    assert(textContains("VPN profiles"), "panel heading must be visible")
    local reserved = 2 * (tree.props.padding or 0) + (#tree.children - 1) * (tree.props.gap or 0)
    for _, child in ipairs(tree.children) do
        if child ~= viewport then reserved = reserved + child.props.height end
    end
    return reserved
end
local longList = copy(running)
longList.profiles = {}
for i=1,80 do
    local row = copy(profiles[1])
    row.id = 99+i
    row.name = "Server " .. tostring(i)
    table.insert(longList.profiles,row)
end
noctalia.state.set("action_error", "")
noctalia.state.set("snapshot",longList)
widget.onClick()
assert(visible)
assert(#key("profiles-flex").children == 80, "long list was truncated instead of being scrollable")
local reservedHeight = checkViewportContract()
noctalia.state.set("snapshot",running)
assert(checkViewportContract() == reservedHeight, "reserved height must not depend on profile count")
noctalia.state.set("snapshot",longList)
noctalia.state.set("action_error", string.rep("DNS error ",20))
assert(checkViewportContract() > reservedHeight, "error card must reserve space before the host allocates the viewport")
noctalia.state.set("action_error", "")
assert(checkViewportContract() == reservedHeight)
key("profile-179").props.onClick()
assert(jobs[#jobs].argv[7] == "179", "last profile must retain its action")
panel.close()

-- A settings change must invalidate an in-flight action/poll from the old API.
local oldAction = jobs[#jobs]
settings.api_address = "127.0.0.1:19095"
settings.poll_seconds = 0
service.onConfigChanged()
assert(lastInterval == 2000)
done(oldAction,"running")
assert(values.snapshot.ok == false, "old action must not overwrite the new endpoint state")
local pending = {}
for _, job in ipairs(jobs) do if job.cb then table.insert(pending,job) end end
for _, job in ipairs(pending) do done(job,"idle") end
assert(jobs[#jobs].argv[3] == "--addr=127.0.0.1:19095", "refresh must use updated settings")
