#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CloudLab/Emulab JSON-based Profile (Phase-1)
...
"""

import sys, json
import geni.portal as portal
import geni.rspec.pg as pg
import geni.rspec.igext as IG
import geni.rspec.emulab as EM

# Exit codes
EXIT_OK = 0
EXIT_PORTAL = 10
EXIT_JSON = 11
EXIT_SCHEMA = 12
EXIT_SEMANTIC = 13

def die(code, msg):
    sys.stderr.write(msg + "\n")
    sys.exit(code)

def get(d, key, default=None):
    return d[key] if isinstance(d, dict) and key in d else default

def booly(val, default=False):
    return default if val is None else bool(val)

# Portal setup
pc = portal.Context()
ParamType = getattr(portal, "ParameterType", None)
if not ParamType or not hasattr(ParamType, "STRING"):
    die(EXIT_PORTAL, "Portal ParameterType.STRING missing.")

pc.defineParameter("spec_json", "Experiment Specification (JSON)",
                   ParamType.STRING, "",
                   longDescription="Strict JSON describing nodes and links.")
params = pc.bindParameters()

# Default trivial RSpec if no JSON
if not params.spec_json:
    r = pc.makeRequestRSpec()
    r.RawPC("node0")
    pc.printRequestRSpec(r)
    sys.exit(EXIT_OK)

# Parse JSON
try:
    cfg = json.loads(params.spec_json)
except Exception as e:
    die(EXIT_JSON, "Invalid JSON: %s" % e)

if not isinstance(cfg, dict):
    die(EXIT_SCHEMA, "Top-level JSON must be an object.")

nodes_cfg = get(cfg, "nodes")
links_cfg = get(cfg, "links", [])
if not isinstance(nodes_cfg, list) or not nodes_cfg:
    die(EXIT_SCHEMA, "'nodes' must be a non-empty array.")
if not isinstance(links_cfg, list):
    die(EXIT_SCHEMA, "'links' must be an array.")

# Validation
node_defs, node_kinds = {}, {}
names = set()
for n in nodes_cfg:
    if not isinstance(n, dict): die(EXIT_SCHEMA, "Each node must be an object.")
    kind, name = get(n, "kind"), get(n, "name")
    if kind not in ("rawpc", "xenvm"): die(EXIT_SCHEMA, "Unsupported node kind '%s'." % kind)
    if not isinstance(name, basestring) or not name: die(EXIT_SCHEMA, "Node 'name' must be string.")
    if name in names: die(EXIT_SCHEMA, "Duplicate node name '%s'." % name)
    names.add(name)
    node_defs[name], node_kinds[name] = n, kind
    # Blockstores
    blks = get(n, "blockstores")
    if blks is not None:
        if not isinstance(blks, list): die(EXIT_SCHEMA, "node '%s': blockstores must be list." % name)
        for b in blks:
            if not isinstance(b, dict): die(EXIT_SCHEMA, "node '%s': blockstore must be object." % name)
            if not get(b, "name") or not isinstance(get(b, "size"), int):
                die(EXIT_SCHEMA, "node '%s': blockstore needs 'name' and int 'size'." % name)

# xenvm host references
for n in nodes_cfg:
    if n["kind"] == "xenvm":
        host = get(n, "instantiate_on")
        if host and (host not in node_kinds or node_kinds[host] != "rawpc"):
            die(EXIT_SEMANTIC, "xenvm '%s' must reference valid rawpc." % n["name"])

# Links
link_names = set()
for l in links_cfg:
    if not isinstance(l, dict): die(EXIT_SCHEMA, "Each link must be object.")
    kind, name = get(l, "kind"), get(l, "name")
    if kind not in ("link", "lan", "bridged_link"):
        die(EXIT_SCHEMA, "Unsupported link kind '%s'." % kind)
    if not isinstance(name, basestring) or not name: die(EXIT_SCHEMA, "Link name must be string.")
    if name in link_names: die(EXIT_SCHEMA, "Duplicate link name '%s'." % name)
    link_names.add(name)
    ifs = get(l, "interfaces")
    if not isinstance(ifs, list) or not ifs:
        die(EXIT_SCHEMA, "Link '%s' requires interfaces." % name)
    for i in ifs:
        node_ref = get(i, "node")
        if node_ref not in node_defs:
            die(EXIT_SEMANTIC, "Link '%s' references unknown node '%s'." % (name, node_ref))

# Build RSpec
request = pc.makeRequestRSpec()
node_objs = {}

def add_blockstores(node_obj, blks):
    for b in blks or []:
        bs = node_obj.Blockstore(b["name"], get(b, "mount"))
        bs.size = int(b["size"])

def hydrate_common(node_obj, spec):
    if get(spec, "aggregate"): node_obj.component_manager_id = spec["aggregate"]
    if get(spec, "disk_image"): node_obj.disk_image = spec["disk_image"]
    if booly(get(spec, "routable_ip")): node_obj.routable_control_ip = True
    add_blockstores(node_obj, get(spec, "blockstores"))

def make_rawpc(n):
    node = request.RawPC(n["name"])
    if get(n, "hardware_type"): node.hardware_type = n["hardware_type"]
    if booly(get(n, "exclusive")): node.exclusive = True
    hydrate_common(node, n)
    return node

def make_xenvm(n):
    node = request.XenVM(n["name"])
    if get(n, "cores"): node.cores = int(n["cores"])
    if get(n, "ram"): node.ram = int(n["ram"])
    if get(n, "disk"): node.disk = int(n["disk"])
    hydrate_common(node, n)
    if get(n, "instantiate_on"): node.InstantiateOn(node_objs[n["instantiate_on"]])
    return node

# Build nodes
for n in nodes_cfg:
    if node_kinds[n["name"]] == "rawpc": node_objs[n["name"]] = make_rawpc(n)
for n in nodes_cfg:
    if node_kinds[n["name"]] == "xenvm": node_objs[n["name"]] = make_xenvm(n)

def add_ifaces(obj, ifaces):
    for i in ifaces:
        iface = node_objs[i["node"]].addInterface(get(i, "ifname"))
        obj.addInterface(iface)

def make_link(l):
    if l["kind"] == "link": link = request.Link(l["name"])
    elif l["kind"] == "lan": link = request.LAN(l["name"])
    else:
        link = request.BridgedLink(l["name"])
        if "bandwidth" in l: link.bandwidth = int(l["bandwidth"])
        if "latency" in l: link.latency = int(l["latency"])
        if "plr" in l: link.plr = float(l["plr"])
    add_ifaces(link, l["interfaces"])
    return link

for l in links_cfg:
    make_link(l)

# Emit RSpec
pc.printRequestRSpec(request)
sys.exit(EXIT_OK)
