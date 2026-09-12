#!/usr/bin/env python3
"""Human-controlled Profile Engine: canonical profile intent -> candidates.

Reads ``engine/sources/profile/intent.yaml`` (the human-maintained Canonical Profile
Intent), validates it, and renders seven client candidate configs into
``Profiles/`` from the per-client base templates under
``engine/sources/profile/templates/``.

This tool is deliberately NOT part of the daily GitHub Actions rule update:
profile files evolve through human review and device testing only
(see engine/docs/MULTI_CLIENT_AUDIT.md and the project handoff notes).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

import repo_identity

REPO_ROOT = Path(__file__).resolve().parents[2]
INTENT_PATH = REPO_ROOT / "engine" / "sources" / "profile" / "intent.yaml"
TEMPLATE_DIR = REPO_ROOT / "engine" / "sources" / "profile" / "templates"
OUTPUT_DIR = REPO_ROOT / "Profiles"

CLIENTS = {
    "surge": ("surge.conf", "Surge.conf"),
    "shadowrocket": ("shadowrocket.conf", "Shadowrocket.conf"),
    "loon": ("loon.conf", "Loon.conf"),
    "stash": ("stash.yaml", "Stash.yaml"),
    "clash": ("clash.yaml", "Clash.yaml"),
    "egern": ("egern.yaml", "Egern.yaml"),
    "quantumultx": ("quantumultx.conf", "QuantumultX.conf"),
}

BUILTIN_POLICIES = {"DIRECT", "REJECT", "REJECT-DROP", "Sub"}
# Every published reference derives from repo_identity, so renaming the account
# is a one-line change instead of a find-and-replace across the generators.
BLINK_RAW = repo_identity.raw_url("Surge")
BLINK_RAW_CLASH = repo_identity.raw_url("Clash")
BLINK_RAW_QX = repo_identity.raw_url("QuantumultX")

# Per-client view file directory for the multi-view pilot (view payloads are
# policy-free rule-set content, referenced at use site).
BLINK_RAW_VIEW = repo_identity.RAW_BASE
VIEW_DIR = {
    "surge": "Surge",
    "shadowrocket": "Shadowrocket",
    "loon": "Loon",
    "stash": "Stash",
    "clash": "Clash",
    "egern": "Egern",
    "quantumultx": "QuantumultX",
}


def _view_url(client: str, app_name: str, view_name: str) -> str:
    return f"{BLINK_RAW_VIEW}/{VIEW_DIR[client]}/{app_name}-{view_name}.conf"


# Clients whose rule-set *reference line* can carry ``no-resolve`` (capability
# matrix: engine/docs/PHASE_OPTIMIZATION_PLAN.md, engine/docs/MULTI_CLIENT_AUDIT.md).
# Excluded on purpose, each annotated in its own template header instead of being
# dropped silently:
#   - loon:        [Remote Rule] reference lines have no no-resolve field; only the
#                  rule lines inside the referenced set can carry it.
#   - egern:       no_resolve is set-level, declared inside the rule set itself.
#   - quantumultx: no production-proven slot on a filter_remote line.
IP_NO_RESOLVE_CLIENTS = frozenset({"surge", "shadowrocket", "stash", "clash"})


def _no_resolve_suffix(client: str) -> str:
    """``,no-resolve`` for an IP-phase reference, or '' when the client has no slot."""
    return ",no-resolve" if client in IP_NO_RESOLVE_CLIENTS else ""


# Placeholders the templates may carry.  Each renderer fills the ones that
# make sense for its client; leftover markers fail the build loudly.
MARKERS = ("__SUBSCRIPTION__", "__POLICY_GROUPS__", "__FILTERS__", "__RULES__", "__REMOTE_RULES__")


class ProfileError(RuntimeError):
    """A deterministic intent or template error that must stop rendering."""


def load_intent(path: Path) -> dict:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ProfileError(f"cannot read intent {path}: {error}") from error
    except yaml.YAMLError as error:
        raise ProfileError(f"invalid YAML in {path}: {error}") from error
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ProfileError("intent must be a mapping with version: 1")
    return document


def validate_intent(intent: dict) -> None:
    subscription = intent.get("subscription")
    if not isinstance(subscription, dict):
        raise ProfileError("intent must define a subscription mapping")
    if not isinstance(subscription.get("url"), str) or not subscription["url"].startswith(
        "https://"
    ):
        raise ProfileError("subscription.url must be an https placeholder URL")
    if not isinstance(subscription.get("name"), str) or not subscription["name"]:
        raise ProfileError("subscription.name is required")

    groups = intent.get("policy_groups")
    if not isinstance(groups, list) or not groups:
        raise ProfileError("policy_groups must be a non-empty list")
    names: set[str] = set()
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get("name"), str):
            raise ProfileError(f"invalid policy group entry: {group!r}")
        name = group["name"]
        if name in BUILTIN_POLICIES or name in names:
            raise ProfileError(f"duplicate or reserved policy group name: {name!r}")
        names.add(name)
        gtype = group.get("type")
        if gtype not in {"select", "url-test"}:
            raise ProfileError(f"{name}: unsupported group type {gtype!r}")
        if gtype == "url-test" and not group.get("members"):
            raise ProfileError(f"{name}: url-test group requires members")
        for extra in ("interval", "tolerance"):
            value = group.get(extra)
            if value is not None and not isinstance(value, int):
                raise ProfileError(f"{name}: {extra} must be an integer")
        if group.get("filter") is not None and not isinstance(group["filter"], str):
            raise ProfileError(f"{name}: filter must be a string")

    for group in groups:
        for member in group.get("members", []):
            if member not in names and member not in BUILTIN_POLICIES:
                raise ProfileError(f"{group['name']}: unknown member {member!r}")

    # Cycle detection over group references.
    edges = {group["name"]: [m for m in group.get("members", []) if m in names] for group in groups}
    for start in names:
        seen: set[str] = set()
        stack = [start]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            for target in edges.get(current, []):
                if target == start and len(seen) > 1:
                    raise ProfileError(f"policy group cycle through {start!r}")
                stack.append(target)

    apps = intent.get("apps")
    if not isinstance(apps, dict) or not apps:
        raise ProfileError("apps must be a non-empty mapping")
    for app_name, app in apps.items():
        if not isinstance(app, dict):
            raise ProfileError(f"{app_name}: app entry must be a mapping")
        policy = app.get("policy")
        if policy not in names and policy not in {"DIRECT", "REJECT"}:
            raise ProfileError(f"{app_name}: policy {policy!r} does not exist")
        source = app.get("source")
        if source is not None and (
            not isinstance(source, str) or not source.startswith("https://")
        ):
            raise ProfileError(f"{app_name}: source must be an https URL")

    infra = intent.get("infrastructure", [])
    if not isinstance(infra, list):
        raise ProfileError("infrastructure must be a list")
    infra_names: set[str] = set()
    for rule in infra:
        if not isinstance(rule, dict) or not isinstance(rule.get("name"), str):
            raise ProfileError(f"invalid infrastructure entry: {rule!r}")
        if rule["name"] in infra_names:
            raise ProfileError(f"duplicate infrastructure name {rule['name']!r}")
        infra_names.add(rule["name"])
        clients = rule.get("clients")
        if clients is not None and any(client not in CLIENTS for client in clients):
            raise ProfileError(f"{rule['name']}: unknown client in clients {clients!r}")
        if rule.get("policy") is None:
            raise ProfileError(f"{rule['name']}: policy is required")
        if rule.get("kind", "rule-set") not in {"rule-set", "dest-port", "domain", "domain-set"}:
            raise ProfileError(f"{rule['name']}: unsupported kind {rule.get('kind')!r}")
        surge_options = rule.get("surge_options")
        if surge_options is not None and (
            not isinstance(surge_options, list)
            or not all(isinstance(option, str) and option for option in surge_options)
        ):
            raise ProfileError(f"{rule['name']}: surge_options must be a list of strings")
        if rule.get("phase") not in {None, "domain", "ip"}:
            raise ProfileError(f"{rule['name']}: phase must be 'domain' or 'ip'")
        if rule.get("kind", "rule-set") in {"rule-set", "domain-set"} and not rule.get("url"):
            raise ProfileError(f"{rule['name']}: kind {rule.get('kind')!r} requires url")


def _policy_for(rule: dict, client: str) -> str:
    policy = rule["policy"]
    if isinstance(policy, str):
        return policy
    if isinstance(policy, dict):
        if client in policy:
            return policy[client]
        if "all" in policy:
            return policy["all"]
        raise ProfileError(f"{rule['name']}: no policy declared for client {client!r}")
    raise ProfileError(f"{rule['name']}: invalid policy {policy!r}")


def _infra_for_client(rule: dict, client: str) -> dict | None:
    clients = rule.get("clients")
    if clients is not None and client not in clients:
        return None
    return rule


def _phase(rule: dict) -> str:
    """domain-first / IP-last: the phase an infrastructure rule belongs to."""
    phase = rule.get("phase")
    return phase if phase in {"domain", "ip"} else "domain"


def _infra_for_phase(intent: dict, client: str, phase: str) -> list[dict]:
    """Return the client-visible infrastructure entries of a given phase, in order."""
    return [
        entry
        for rule in intent.get("infrastructure", [])
        if _phase(rule) == phase and (entry := _infra_for_client(rule, client)) is not None
    ]


def _unsupported_reason(rule: dict, client: str) -> str:
    """Human-readable reason a Surge-bound infrastructure rule is unavailable client-side."""
    surge_options = rule.get("surge_options") or []
    if rule.get("kind") == "domain-set":
        return "Surge DOMAIN-SET 专属"
    if "pre-matching" in surge_options:
        return "Surge pre-matching 专属"
    if (
        client == "quantumultx"
        and not rule.get("qx_url")
        and rule.get("kind", "rule-set") == "rule-set"
    ):
        return "Quantumult X 无对应源"
    if "extended-matching" in surge_options:
        return "Surge extended-matching 专属"
    return "当前客户端不支持"


def _infra_unsupported_lines(intent: dict, client: str, phase: str, prefix: str) -> list[str]:
    """Per-item UNSUPPORTED notes for infrastructure the client omits, for a given phase."""
    lines: list[str] = []
    for rule in intent.get("infrastructure", []):
        if _phase(rule) != phase:
            continue
        if rule.get("clients") is not None and client not in rule["clients"]:
            lines.append(
                f"{prefix}# UNSUPPORTED: {rule['name']}（{_unsupported_reason(rule, client)}）本文件省略"
            )
    return lines


# --------------------------------------------------------------------------
# Per-client renderers.  Each returns a dict of marker -> text.  Anything a
# client cannot express is either adapted (documented inline as a comment)
# or omitted through the intent's per-client availability lists; nothing is
# silently invented.
# --------------------------------------------------------------------------


def _render_surge(intent: dict) -> dict[str, str]:
    sub = intent["subscription"]
    lines: list[str] = []
    lines.append(
        f"{sub['name']} = select, policy-path={sub['url']}, update-interval={sub['update_interval']},"
        " no-alert=0, hidden=0, include-all-proxies=0"
    )
    for group in intent["policy_groups"]:
        if group.get("filter") is not None:
            lines.append(
                f"{group['name']} = select, no-alert=0, hidden=0, include-all-proxies=0,"
                f' include-other-group="{sub["name"]}", policy-regex-filter={group["filter"]}'
            )
            continue
        members = ",".join(group.get("members", []))
        hidden = "1" if group.get("hidden") else "0"
        no_alert = "1" if group.get("hidden") else "0"
        if group["type"] == "url-test":
            lines.append(
                f"{group['name']} = url-test, {members}, interval={group.get('interval', 600)},"
                f" tolerance={group.get('tolerance', 100)}, no-alert={no_alert}, hidden={hidden},"
                " include-all-proxies=0"
            )
        else:
            lines.append(
                f"{group['name']} = select, {members}, no-alert={no_alert}, hidden={hidden},"
                " include-all-proxies=0"
            )
    rules: list[str] = []
    for entry in _infra_for_phase(intent, "surge", "domain"):
        policy = _policy_for(entry, "surge")
        option_parts: list[str] = []
        option = (entry.get("options") or {}).get("surge")
        if option:
            option_parts.append(option)
        option_parts.extend(entry.get("surge_options") or [])
        suffix = "," + ",".join(option_parts) if option_parts else ""
        if entry.get("kind") == "dest-port":
            rules.append(f"DEST-PORT,{entry['value']},{policy}")
        elif entry.get("kind") == "domain":
            rules.append(f"DOMAIN,{entry['value']},{policy}")
        elif entry.get("kind") == "domain-set":
            rules.append(f"DOMAIN-SET,{entry['url']},{policy}{suffix}")
        else:
            rules.append(f"RULE-SET,{entry['url']},{policy}{suffix}")
    for app_name, app in intent["apps"].items():
        if app.get("views"):
            # 分文件引用（domain-first / IP-last），按 app 声明的 view 列表
            for view_name in app["views"]:
                url = app.get(f"{view_name}_source") or _view_url("surge", app_name, view_name)
                if view_name == "domainset":
                    rules.append(f"DOMAIN-SET,{url},{app['policy']},extended-matching")
                elif view_name == "ip":
                    rules.append(f"RULE-SET,{url},{app['policy']}{_no_resolve_suffix('surge')}")
                else:  # nonip
                    rules.append(f"RULE-SET,{url},{app['policy']}")
            continue
        source = app.get("source") or f"{BLINK_RAW}/{app_name}.list"
        rules.append(f"RULE-SET,{source},{app['policy']}")
    for entry in _infra_for_phase(intent, "surge", "ip"):
        policy = _policy_for(entry, "surge")
        option_parts: list[str] = []
        option = (entry.get("options") or {}).get("surge")
        if option:
            option_parts.append(option)
        option_parts.extend(entry.get("surge_options") or [])
        suffix = "," + ",".join(option_parts) if option_parts else ""
        if entry.get("kind") == "dest-port":
            rules.append(f"DEST-PORT,{entry['value']},{policy}")
        elif entry.get("kind") == "domain":
            rules.append(f"DOMAIN,{entry['value']},{policy}")
        elif entry.get("kind") == "domain-set":
            rules.append(f"DOMAIN-SET,{entry['url']},{policy}{suffix}")
        else:
            rules.append(f"RULE-SET,{entry['url']},{policy}{suffix}")
    rules.append("FINAL,Final,dns-failed")
    return {"__POLICY_GROUPS__": "\n".join(lines), "__RULES__": "\n".join(rules)}


def _render_shadowrocket(intent: dict) -> dict[str, str]:
    sub = intent["subscription"]
    lines: list[str] = []
    for group in intent["policy_groups"]:
        if group.get("filter") is not None:
            lines.append(f"{group['name']} = select, policy-regex-filter={group['filter']}")
            continue
        members = ",".join(group.get("members", []))
        if group["type"] == "url-test":
            lines.append(
                f"{group['name']} = url-test, {members}, url=http://cp.cloudflare.com/generate_204,"
                f" interval={group.get('interval', 600)}, tolerance={group.get('tolerance', 100)}, timeout=5"
            )
        else:
            lines.append(f"{group['name']} = select, {members}")
    rules: list[str] = []

    def add_rule_entry(entry: dict) -> None:
        policy = _policy_for(entry, "shadowrocket")
        if entry.get("kind") == "dest-port":
            rules.append(f"DEST-PORT,{entry['value']},{policy}")
            return
        if entry.get("kind") == "domain":
            rules.append(f"DOMAIN,{entry['value']},{policy}")
            return
        # Shadowrocket shares Surge's rule syntax and supports no-resolve, so an
        # IP-phase rule set must keep the option declared in the intent.
        options = (entry.get("options") or {}).get("shadowrocket")
        suffix = f",{options}" if options else ""
        rules.append(f"RULE-SET,{entry['url']},{policy}{suffix}")

    for entry in _infra_for_phase(intent, "shadowrocket", "domain"):
        add_rule_entry(entry)
    rules.extend(_infra_unsupported_lines(intent, "shadowrocket", "domain", ""))
    for app_name, app in intent["apps"].items():
        if app.get("views"):
            for view_name in app["views"]:
                url = _view_url("shadowrocket", app_name, view_name)
                if view_name == "domainset":
                    rules.append(f"DOMAIN-SET,{url},{app['policy']}")
                elif view_name == "ip":
                    rules.append(
                        f"RULE-SET,{url},{app['policy']}{_no_resolve_suffix('shadowrocket')}"
                    )
                else:
                    rules.append(f"RULE-SET,{url},{app['policy']}")
            continue
        source = app.get("source") or f"{BLINK_RAW}/{app_name}.list"
        rules.append(f"RULE-SET,{source},{app['policy']}")
    for entry in _infra_for_phase(intent, "shadowrocket", "ip"):
        add_rule_entry(entry)
    rules.extend(_infra_unsupported_lines(intent, "shadowrocket", "ip", ""))
    rules.append("FINAL,Final")
    subscription = [
        "# ADAPTED：请在 Shadowrocket App 内添加下列唯一订阅，并将其命名为 Sub。",
        f"# {sub['url']}",
    ]
    return {
        "__POLICY_GROUPS__": "\n".join(lines),
        "__RULES__": "\n".join(rules),
        "__SUBSCRIPTION__": "\n".join(subscription),
    }


def _render_loon(intent: dict) -> dict[str, str]:
    sub = intent["subscription"]
    filters: list[str] = []
    groups: list[str] = []
    for group in intent["policy_groups"]:
        if group.get("filter") is not None:
            filters.append(f"{group['name']} = NameRegex, FilterKey = {group['filter']}")
            continue
        members = [m for m in group.get("members", []) if m != "Sub"]
        members = ",".join(members)
        if group["type"] == "url-test":
            groups.append(
                f"{group['name']} = url-test, {members}, interval={group.get('interval', 600)},"
                f" tolerance={group.get('tolerance', 100)}"
            )
        else:
            groups.append(f"{group['name']} = select, {members}")
    local_rules: list[str] = []
    remote_rules: list[str] = []
    for entry in _infra_for_phase(intent, "loon", "domain"):
        policy = _policy_for(entry, "loon")
        if entry.get("kind") == "dest-port":
            local_rules.append(f"DEST-PORT,{entry['value']},{policy}")
        elif entry.get("kind") == "domain":
            local_rules.append(f"DOMAIN,{entry['value']},{policy}")
        else:
            remote_rules.append(
                f"{entry['url']}, policy = {policy}, tag = {entry['name']}, enabled = true"
            )
    remote_rules.extend(_infra_unsupported_lines(intent, "loon", "domain", ""))
    for app_name, app in intent["apps"].items():
        if app.get("views"):
            for view_name in app["views"]:
                remote_rules.append(
                    f"{_view_url('loon', app_name, view_name)}, policy = {app['policy']}, "
                    f"tag = {app_name}-{view_name}, enabled = true"
                )
            continue
        source = app.get("source") or f"{BLINK_RAW}/{app_name}.list"
        remote_rules.append(f"{source}, policy = {app['policy']}, tag = {app_name}, enabled = true")
    for entry in _infra_for_phase(intent, "loon", "ip"):
        policy = _policy_for(entry, "loon")
        if entry.get("kind") == "dest-port":
            local_rules.append(f"DEST-PORT,{entry['value']},{policy}")
        elif entry.get("kind") == "domain":
            local_rules.append(f"DOMAIN,{entry['value']},{policy}")
        else:
            remote_rules.append(
                f"{entry['url']}, policy = {policy}, tag = {entry['name']}, enabled = true"
            )
    remote_rules.extend(_infra_unsupported_lines(intent, "loon", "ip", ""))
    local_rules.append("FINAL,Final")
    subscription = [
        "# ADAPTED：请在 Loon App 内添加下列唯一订阅；地区组通过 [Remote Filter] 筛选节点。",
        f"# {sub['url']}",
    ]
    return {
        "__FILTERS__": "\n".join(filters),
        "__POLICY_GROUPS__": "\n".join(groups),
        "__RULES__": "\n".join(local_rules),
        "__REMOTE_RULES__": "\n".join(remote_rules),
        "__SUBSCRIPTION__": "\n".join(subscription),
    }


def _render_stash(intent: dict) -> dict[str, str]:
    sub = intent["subscription"]
    subscription = [
        "proxy-providers:",
        f"  {sub['name']}:",
        "    type: http",
        f"    url: {sub['url']}",
        f"    interval: {sub['update_interval']}",
        "    health-check:",
        "      enable: true",
        "      url: http://1.1.1.1/generate_204",
        "      interval: 1800",
        "      timeout: 5000",
    ]
    group_lines: list[str] = ["proxy-groups:"]
    for group in intent["policy_groups"]:
        if group.get("filter") is not None:
            group_lines.append(
                f"  - {{name: {group['name']}, type: select, use: [{sub['name']}],"
                f" filter: '{group['filter']}', include-all: true}}"
            )
            continue
        members = ",".join(group.get("members", []))
        if group["type"] == "url-test":
            group_lines.append(
                f"  - {{name: {group['name']}, type: url-test, proxies: [{members}],"
                f" url: http://cp.cloudflare.com/generate_204, interval: {group.get('interval', 600)},"
                f" tolerance: {group.get('tolerance', 100)}}}"
            )
        else:
            group_lines.append(f"  - {{name: {group['name']}, type: select, proxies: [{members}]}}")
    providers: dict[str, str] = {}
    rules: list[str] = ["rules:"]

    def provider_name(name: str) -> str:
        base = re.sub(r"[^A-Za-z0-9]", "_", name)
        base = base.strip("_") or "ruleset"
        unique = base
        counter = 2
        while unique in providers and providers[unique] != name:
            unique = f"{base}_{counter}"
            counter += 1
        providers[unique] = name
        return unique

    provider_lines: list[str] = ["rule-providers:"]

    def add_rule_entry(entry: dict) -> None:
        policy = _policy_for(entry, "stash")
        # Inline rules are emitted at their declared phase position, like the
        # Surge renderer does.  Collecting them for the end would silently move
        # a domain-phase rule behind the IP phase.
        if entry.get("kind") == "dest-port":
            rules.append(f"  - DST-PORT,{entry['value']},{policy}")
            return
        if entry.get("kind") == "domain":
            rules.append(f"  - DOMAIN,{entry['value']},{policy}")
            return
        # Stash supports no-resolve on a RULE-SET reference; an IP-phase rule set
        # must keep the option declared in the intent (mirrors the Clash renderer).
        options = (entry.get("options") or {}).get("stash")
        suffix = f",{options}" if options else ""
        key = provider_name(entry["name"])
        provider_lines.append(f"  {key}:")
        provider_lines.append("    type: http")
        provider_lines.append("    behavior: classical")
        provider_lines.append("    format: text")
        provider_lines.append(f"    url: {entry['url']}")
        provider_lines.append("    interval: 86400")
        rules.append(f"  - RULE-SET,{key},{policy}{suffix}")

    for entry in _infra_for_phase(intent, "stash", "domain"):
        add_rule_entry(entry)
    rules.extend(_infra_unsupported_lines(intent, "stash", "domain", "  "))
    for app_name, app in intent["apps"].items():
        if app.get("views"):
            for view_name in app["views"]:
                behavior = "domain" if view_name == "domainset" else "classical"
                key = provider_name(f"{app_name}-{view_name}")
                provider_lines.append(f"  {key}:")
                provider_lines.append("    type: http")
                provider_lines.append(f"    behavior: {behavior}")
                provider_lines.append("    format: text")
                provider_lines.append(f"    url: {_view_url('stash', app_name, view_name)}")
                provider_lines.append("    interval: 86400")
                suffix = _no_resolve_suffix("stash") if view_name == "ip" else ""
                rules.append(f"  - RULE-SET,{key},{app['policy']}{suffix}")
            continue
        source = app.get("source") or f"{BLINK_RAW}/{app_name}.list"
        key = provider_name(app_name)
        provider_lines.append(f"  {key}:")
        provider_lines.append("    type: http")
        provider_lines.append("    behavior: classical")
        provider_lines.append("    format: text")
        provider_lines.append(f"    url: {source}")
        provider_lines.append("    interval: 86400")
        rules.append(f"  - RULE-SET,{key},{app['policy']}")
    for entry in _infra_for_phase(intent, "stash", "ip"):
        add_rule_entry(entry)
    rules.extend(_infra_unsupported_lines(intent, "stash", "ip", "  "))
    rules.append("  - MATCH,Final")
    return {
        "__SUBSCRIPTION__": "\n".join(subscription),
        "__POLICY_GROUPS__": "\n".join(group_lines),
        "__RULES__": "\n".join(provider_lines),
        "__REMOTE_RULES__": "\n".join(rules),
    }


def _render_clash(intent: dict) -> dict[str, str]:
    sub = intent["subscription"]
    subscription = [
        "proxy-providers:",
        f"  {sub['name']}:",
        "    type: http",
        f"    url: {sub['url']}",
        f"    interval: {sub['update_interval']}",
        "    health-check:",
        "      enable: true",
        "      url: http://www.gstatic.com/generate_204",
        "      interval: 300",
        "      timeout: 5000",
    ]
    group_lines: list[str] = ["proxy-groups:"]
    for group in intent["policy_groups"]:
        if group.get("filter") is not None:
            group_lines.append(
                f"  - {{name: {group['name']}, type: select, use: [{sub['name']}],"
                f" filter: '{group['filter']}', include-all: true}}"
            )
            continue
        # Clash ``proxies`` arrays cannot reference a provider name: the Sub
        # pool is covered by the region filter groups instead (same handling
        # as the Loon renderer).
        members = [member for member in group.get("members", []) if member != "Sub"]
        members_text = ",".join(members)
        if group["type"] == "url-test":
            group_lines.append(
                f"  - {{name: {group['name']}, type: url-test, proxies: [{members_text}],"
                f" url: http://cp.cloudflare.com/generate_204, interval: {group.get('interval', 600)},"
                f" tolerance: {group.get('tolerance', 100)}}}"
            )
        else:
            group_lines.append(
                f"  - {{name: {group['name']}, type: select, proxies: [{members_text}]}}"
            )
    providers: dict[str, str] = {}
    rules: list[str] = ["rules:"]

    def provider_name(name: str) -> str:
        base = re.sub(r"[^A-Za-z0-9]", "_", name)
        base = base.strip("_") or "ruleset"
        unique = base
        counter = 2
        while unique in providers and providers[unique] != name:
            unique = f"{base}_{counter}"
            counter += 1
        providers[unique] = name
        return unique

    provider_lines: list[str] = ["rule-providers:"]

    def add_rule_entry(entry: dict) -> None:
        policy = _policy_for(entry, "clash")
        options = (entry.get("options") or {}).get("clash")
        suffix = f",{options}" if options else ""
        # Emitted at the declared phase position (see the Stash renderer).
        if entry.get("kind") == "dest-port":
            rules.append(f"  - DST-PORT,{entry['value']},{policy}")
            return
        if entry.get("kind") == "domain":
            rules.append(f"  - DOMAIN,{entry['value']},{policy}")
            return
        key = provider_name(entry["name"])
        provider_lines.append(f"  {key}:")
        provider_lines.append("    type: http")
        provider_lines.append("    behavior: classical")
        provider_lines.append("    format: text")
        provider_lines.append(f"    url: {entry['url']}")
        provider_lines.append("    interval: 86400")
        rules.append(f"  - RULE-SET,{key},{policy}{suffix}")

    for entry in _infra_for_phase(intent, "clash", "domain"):
        add_rule_entry(entry)
    rules.extend(_infra_unsupported_lines(intent, "clash", "domain", "  "))
    for app_name, app in intent["apps"].items():
        if app.get("views"):
            for view_name in app["views"]:
                behavior = "domain" if view_name == "domainset" else "classical"
                key = provider_name(f"{app_name}-{view_name}")
                provider_lines.append(f"  {key}:")
                provider_lines.append("    type: http")
                provider_lines.append(f"    behavior: {behavior}")
                provider_lines.append("    format: text")
                provider_lines.append(f"    url: {_view_url('clash', app_name, view_name)}")
                provider_lines.append("    interval: 86400")
                suffix = _no_resolve_suffix("clash") if view_name == "ip" else ""
                rules.append(f"  - RULE-SET,{key},{app['policy']}{suffix}")
            continue
        # Blink 的 App 规则经 Clash/ 目录分发（classical 已去除 USER-AGENT）；
        # 显式指定外部 source 的 App（如 AppleMusic）按上游原样引用。
        source = app.get("source") or f"{BLINK_RAW_CLASH}/{app_name}.list"
        key = provider_name(app_name)
        provider_lines.append(f"  {key}:")
        provider_lines.append("    type: http")
        provider_lines.append("    behavior: classical")
        provider_lines.append("    format: text")
        provider_lines.append(f"    url: {source}")
        provider_lines.append("    interval: 86400")
        rules.append(f"  - RULE-SET,{key},{app['policy']}")
    for entry in _infra_for_phase(intent, "clash", "ip"):
        add_rule_entry(entry)
    rules.extend(_infra_unsupported_lines(intent, "clash", "ip", "  "))
    rules.append("  - MATCH,Final")
    return {
        "__SUBSCRIPTION__": "\n".join(subscription),
        "__POLICY_GROUPS__": "\n".join(group_lines),
        "__RULES__": "\n".join(provider_lines),
        "__REMOTE_RULES__": "\n".join(rules),
    }


def _render_egern(intent: dict) -> dict[str, str]:
    sub = intent["subscription"]
    group_lines: list[str] = [
        "- external:",
        f"    name: {sub['name']}",
        "    type: select",
        "    urls:",
    ]
    group_lines.append(f"    - {sub['url']}")
    group_lines.append(f"    update_interval: {sub['update_interval']}")
    group_lines.append("    hidden: false")
    for group in intent["policy_groups"]:
        if group.get("filter") is not None:
            group_lines.extend(
                [
                    "- select:",
                    f"    name: {group['name']}",
                    "    policies:",
                    f"    - {sub['name']}",
                    "    flatten: true",
                    f"    filter: '{group['filter']}'",
                ]
            )
            continue
        members = group.get("members", [])
        group_lines.append("- select:")
        group_lines.append(f"    name: {group['name']}")
        group_lines.append("    policies:")
        for member in members:
            group_lines.append(f"    - {member}")
        if group["type"] == "url-test":
            group_lines.append(
                "    # ADAPTED：Egern url-test 待真机验证（Needs Verification），暂以 select 呈现"
            )
    rules: list[str] = []

    def add_rule_entry(entry: dict) -> None:
        policy = _policy_for(entry, "egern")
        if entry.get("kind") == "domain":
            rules.append("- domain:")
            rules.append(f"    match: {entry['value']}")
            rules.append(f"    policy: {policy}")
        elif entry.get("kind") != "dest-port":
            rules.append("- rule_set:")
            rules.append(f"    match: {entry['url']}")
            rules.append(f"    policy: {policy}")

    for entry in _infra_for_phase(intent, "egern", "domain"):
        add_rule_entry(entry)
    rules.extend(_infra_unsupported_lines(intent, "egern", "domain", ""))
    for app_name, app in intent["apps"].items():
        if app.get("views"):
            for view_name in app["views"]:
                rules.append("- rule_set:")
                rules.append(f"    match: {_view_url('egern', app_name, view_name)}")
                rules.append(f"    policy: {app['policy']}")
            continue
        source = app.get("source") or f"{BLINK_RAW}/{app_name}.list"
        rules.append("- rule_set:")
        rules.append(f"    match: {source}")
        rules.append(f"    policy: {app['policy']}")
    for entry in _infra_for_phase(intent, "egern", "ip"):
        add_rule_entry(entry)
    rules.extend(_infra_unsupported_lines(intent, "egern", "ip", ""))
    rules.append("- default:")
    rules.append("    policy: Final")
    return {"__POLICY_GROUPS__": "\n".join(group_lines), "__RULES__": "\n".join(rules)}


def _render_quantumultx(intent: dict) -> dict[str, str]:
    sub = intent["subscription"]
    group_lines: list[str] = []
    for group in intent["policy_groups"]:
        if group.get("filter") is not None:
            group_lines.append(f"static={group['name']}, server-tag-regex={group['filter']}")
            continue
        members = [
            member.lower() if member in {"DIRECT", "REJECT", "REJECT-DROP"} else member
            for member in group.get("members", [])
            if member != "Sub"  # QX 订阅在 App 内添加，组内不引用池名；地区组覆盖池节点
        ]
        members = ",".join(members)
        if group["type"] == "url-test":
            group_lines.append(
                f"url-latency-benchmark={group['name']}, {members},"
                f" check-interval={group.get('interval', 600)}, tolerance={group.get('tolerance', 100)},"
                " alive-checking=false"
            )
        else:
            group_lines.append(f"static={group['name']}, {members}")
    remote_rules: list[str] = []
    local_rules: list[str] = []

    def qx_policy(policy: str) -> str:
        # QX 内置策略为小写（direct/reject），策略组名保持原大小写。
        return policy.lower() if policy in {"DIRECT", "REJECT", "REJECT-DROP"} else policy

    def add_rule_entry(entry: dict) -> None:
        policy = qx_policy(_policy_for(entry, "quantumultx"))
        if entry.get("kind") == "domain":
            # An inline host rule carries no URL: returning here keeps the
            # qx_url requirement scoped to remote rule sets.
            local_rules.append(f"host, {entry['value']}, {policy}")
            return
        if entry.get("kind") == "dest-port":
            return
        url = entry.get("qx_url")
        if url is None:
            raise ProfileError(
                f"{entry['name']}: quantumultx requires an explicit qx_url (QX does not parse Surge-format rule lists)"
            )
        remote_rules.append(
            f"{url}, tag={entry['name']}, force-policy={policy},"
            " update-interval=172800, opt-parser=false, enabled=true"
        )

    for entry in _infra_for_phase(intent, "quantumultx", "domain"):
        add_rule_entry(entry)
    for app_name, app in intent["apps"].items():
        if app.get("views"):
            for view_name in app["views"]:
                remote_rules.append(
                    f"{_view_url('quantumultx', app_name, view_name)}, tag={app_name}-{view_name}, "
                    f"force-policy={qx_policy(app['policy'])},"
                    " update-interval=172800, opt-parser=false, enabled=true"
                )
            continue
        source = app.get("qx_source") or f"{BLINK_RAW_QX}/{app_name}.list"
        remote_rules.append(
            f"{source}, tag={app_name}, force-policy={qx_policy(app['policy'])},"
            " update-interval=172800, opt-parser=false, enabled=true"
        )
    for entry in _infra_for_phase(intent, "quantumultx", "ip"):
        add_rule_entry(entry)
    local_rules.extend(_infra_unsupported_lines(intent, "quantumultx", "domain", ""))
    local_rules.extend(_infra_unsupported_lines(intent, "quantumultx", "ip", ""))
    local_rules.append("final, Final")
    subscription = [
        "# ADAPTED：请在 Quantumult X App 内添加下列唯一订阅；地区组通过 server-tag-regex 筛选节点。",
        f"# {sub['url']}",
    ]
    return {
        "__POLICY_GROUPS__": "\n".join(group_lines),
        "__REMOTE_RULES__": "\n".join(remote_rules),
        "__RULES__": "\n".join(local_rules),
        "__SUBSCRIPTION__": "\n".join(subscription),
    }


RENDERERS = {
    "surge": _render_surge,
    "shadowrocket": _render_shadowrocket,
    "loon": _render_loon,
    "stash": _render_stash,
    "clash": _render_clash,
    "egern": _render_egern,
    "quantumultx": _render_quantumultx,
}


def render_client(client: str, intent: dict) -> str:
    template_name, _output_name = CLIENTS[client]
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise ProfileError(f"missing template {template_path}")
    text = template_path.read_text(encoding="utf-8")
    values = RENDERERS[client](intent)
    for marker in MARKERS:
        text = text.replace(marker, values.get(marker, ""))
    leftover = [marker for marker in MARKERS if marker in text]
    if leftover:
        raise ProfileError(f"{client}: unfilled template markers {leftover}")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent", type=Path, default=INTENT_PATH)
    parser.add_argument(
        "--write", action="store_true", help="write Profiles/ candidates (default: check only)"
    )
    arguments = parser.parse_args(argv)
    try:
        intent = load_intent(arguments.intent)
        validate_intent(intent)
        outputs = {client: render_client(client, intent) for client in CLIENTS}
        if arguments.write:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            for client, text in outputs.items():
                _template, output_name = CLIENTS[client]
                target = OUTPUT_DIR / output_name
                temporary = target.with_suffix(target.suffix + ".tmp")
                temporary.write_text(text, encoding="utf-8", newline="\n")
                temporary.replace(target)
        report = {
            "mode": "write" if arguments.write else "check",
            "clients": {
                client: {"lines": len(text.splitlines())} for client, text in outputs.items()
            },
        }
        print(yaml.safe_dump(report, allow_unicode=True, sort_keys=False))
        return 0
    except ProfileError as error:
        print(f"profile build failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
