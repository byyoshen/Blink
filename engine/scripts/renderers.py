#!/usr/bin/env python3
"""Client renderers: serialize canonical rules into client-compatible files.

One renderer exists per truly different serialization format, not per client:

- ``classical``: policy-free classical text (Surge / Shadowrocket / Loon /
  Stash consume the exact same bytes; see engine/docs/MULTI_CLIENT_AUDIT.md).
- ``classical-mihomo``: the same classical text minus USER-AGENT.  Clash
  kernels (mihomo and original Clash Premium) have no USER-AGENT rule type;
  unknown lines are skipped with a warning by the classical loader, which
  would be a silent downgrade, so this renderer drops them explicitly and
  the caller reports them.
- ``egern-yaml``: Egern's own ``*_set`` YAML rule-set schema.  Egern could
  also consume the classical file through ``rule_set.match``, but the YAML
  form is its native rule-set format and keeps USER-AGENT expressible while
  making the PROCESS-NAME downgrade explicit.
- ``quantumultx``: Quantumult X filter lines (``HOST*`` / ``IP-CIDR`` /
  ``IP6-CIDR`` / ``USER-AGENT``).  QX requires a policy field per line; every
  production publisher emits a placeholder there because the main config's
  ``force-policy`` overrides it.  PROCESS-NAME is not expressible and the
  ``no-resolve`` option has no production-proven slot, so both are dropped
  explicitly and reported by the caller.

Renderers never invent semantics: any rule kind or option combination a
client cannot express losslessly must either be dropped here and reported by
the caller, or raise ``RendererError``.
"""

from __future__ import annotations

import dataclasses
from typing import Iterable

import yaml


class RendererError(RuntimeError):
    """A rule cannot be serialized for a client without changing semantics."""


@dataclasses.dataclass(frozen=True)
class ClientTarget:
    key: str
    directory: str
    suffix: str
    renderer: str


# Order matters: the portal, workflow, and tests use this registry as the
# authoritative client list.
CLIENTS: dict[str, ClientTarget] = {
    "surge": ClientTarget("surge", "Surge", ".list", "classical"),
    "loon": ClientTarget("loon", "Loon", ".list", "classical"),
    "shadowrocket": ClientTarget("shadowrocket", "Shadowrocket", ".list", "classical"),
    "stash": ClientTarget("stash", "Stash", ".list", "classical"),
    "mihomo": ClientTarget("mihomo", "mihomo", ".list", "classical-mihomo"),
    "egern": ClientTarget("egern", "Egern", ".yaml", "egern-yaml"),
    "quantumultx": ClientTarget("quantumultx", "QuantumultX", ".list", "quantumultx"),
}

# Egern emits one bucket per canonical kind it can express.  Egern's own schema
# also has url_regex_set, but URL-REGEX is not in the canonical model
# (ALLOWED_RULE_TYPES), so no rule can ever reach it; parity_check.EGERN_TYPES
# does not know the key either and would reject the file as unknown.  Keep the
# two in lockstep instead of carrying an unreachable bucket.
EGERN_KEY_ORDER = (
    "no_resolve",
    "domain_set",
    "domain_keyword_set",
    "domain_suffix_set",
    "ip_cidr_set",
    "ip_cidr6_set",
    "user_agent_set",
)

# Quantumult X filter types for each canonical kind.  The placeholder policy
# field is overridden by ``force-policy`` in the main config; the lowercase
# literal ``policy`` mirrors the production convention and cannot be
# mistaken for a real policy name.
QUANTUMULTX_TYPES = {
    "DOMAIN": "HOST",
    "DOMAIN-SUFFIX": "HOST-SUFFIX",
    "DOMAIN-KEYWORD": "HOST-KEYWORD",
    "IP-CIDR": "IP-CIDR",
    "IP-CIDR6": "IP6-CIDR",
    "USER-AGENT": "USER-AGENT",
}
QUANTUMULTX_POLICY_PLACEHOLDER = "policy"


def render_classical_body(rules: Iterable[object]) -> list[str]:
    """One classical line per canonical rule: ``KIND,value[,options...]``."""
    return [",".join((rule.kind, rule.value, *rule.options)) for rule in rules]


def render_surge_domainset(rules: Iterable[object], app_name: str) -> str:
    """Serialize pure-domain rules into a Surge ``DOMAIN-SET`` payload.

    A Surge DOMAIN-SET payload holds one domain per line: an exact ``DOMAIN``
    value and a ``.+domain`` suffix for ``DOMAIN-SUFFIX``.  DOMAIN-KEYWORD,
    USER-AGENT, PROCESS-NAME, and IP rules cannot be expressed here, so callers
    must only pass a pure-domain view; any other kind fails loudly.
    """
    body: list[str] = []
    for rule in rules:
        if rule.kind == "DOMAIN":
            body.append(rule.value)
        elif rule.kind == "DOMAIN-SUFFIX":
            body.append("." + rule.value)
        else:
            raise RendererError(f"surge domainset cannot express rule kind {rule.kind!r}")
    if not body:
        raise RendererError("surge domainset output is empty")
    lines = [f"# 规则名称: {app_name}", f"# 规则统计: {len(body)}", "", *body]
    return "\n".join(lines) + "\n"


def render_mihomo_domainset(rules: Iterable[object], app_name: str) -> str:
    """Serialize pure-domain rules into a Mihomo ``behavior: domain`` payload.

    Mihomo's ``domain`` rule-provider expects one domain per line, with a
    ``+.<domain>`` prefix for subdomain/suffix matches and a bare value for an
    exact match (mirrors skk's ``ClashDomainSet``).
    """
    body: list[str] = []
    for rule in rules:
        if rule.kind == "DOMAIN":
            body.append(rule.value)
        elif rule.kind == "DOMAIN-SUFFIX":
            body.append("+." + rule.value)
        else:
            raise RendererError(f"mihomo domainset cannot express rule kind {rule.kind!r}")
    if not body:
        raise RendererError("mihomo domainset output is empty")
    lines = [f"# 规则名称: {app_name}", f"# 规则统计: {len(body)}", "", *body]
    return "\n".join(lines) + "\n"


# View serialization for the cross-client multi-view pilot.  View files are
# policy-free rule-set payloads (the referencing profile supplies the policy),
# so they reuse the existing classical / mihomo / QX renderers.
def render_view(client_key: str, view_name: str, rules: Iterable[object], app_name: str) -> str:
    if view_name == "domainset":
        if client_key in {"surge", "shadowrocket"}:
            return render_surge_domainset(rules, app_name)
        if client_key in {"stash", "mihomo"}:
            return render_mihomo_domainset(rules, app_name)
        if client_key in {"loon", "egern"}:
            return render_classical(rules, app_name)
        if client_key == "quantumultx":
            return render_quantumultx(rules, app_name)[0]
    if view_name in {"nonip", "ip"}:
        if client_key == "mihomo":
            return render_classical_mihomo(rules, app_name)[0]
        if client_key == "quantumultx":
            return render_quantumultx(rules, app_name)[0]
        if client_key == "egern":
            # Egern cannot express PROCESS-NAME (mirrors the Egern YAML output's
            # explicit drop); keep the classical payload honest.
            return render_classical(
                [rule for rule in rules if rule.kind != "PROCESS-NAME"], app_name
            )
        return render_classical(rules, app_name)
    raise RendererError(f"render_view: unknown view {view_name!r} for client {client_key!r}")


def render_classical(rules: Iterable[object], app_name: str) -> str:
    """Full classical file: two ``#`` header lines, blank line, rules.

    Byte-identical to the historical Surge output: Surge backward
    compatibility depends on this function never changing its output.
    """
    body = render_classical_body(rules)
    lines = [f"# 规则名称: {app_name}", f"# 规则统计: {len(body)}", "", *body]
    return "\n".join(lines) + "\n"


def render_classical_mihomo(rules: Iterable[object], app_name: str) -> tuple[str, list[str]]:
    """Serialize rules into a mihomo classical rule-provider payload.

    Clash kernels have no USER-AGENT rule type; the classical loader warns
    and silently skips unknown lines, which would hide the downgrade.  This
    renderer therefore drops USER-AGENT explicitly and reports it (matching
    the Egern / Quantumult X PROCESS-NAME precedent).  The remaining six
    canonical kinds serialize line-for-line identically to Surge.
    """
    body: list[str] = []
    dropped: list[str] = []
    for rule in rules:
        if rule.kind == "USER-AGENT":
            dropped.append(f"{rule.kind},{rule.value}")
            continue
        body.append(",".join((rule.kind, rule.value, *rule.options)))
    if not body:
        raise RendererError("mihomo output is empty after dropping unsupported rules")
    lines = [f"# 规则名称: {app_name}", f"# 规则统计: {len(body)}", "", *body]
    return "\n".join(lines) + "\n", dropped


def render_quantumultx(rules: Iterable[object], app_name: str) -> tuple[str, list[str]]:
    """Serialize rules into Quantumult X filter lines.

    Returns ``(text, dropped)``.  Dropped records every rule the format
    cannot express (PROCESS-NAME) so the downgrade stays auditable.  The
    ``no-resolve`` option has no production-proven slot in QX filter files
    (Repcz / QuixoticHeart / blackmatrix7 all omit it), so IP options are
    not serialized; this uniform behavior is documented in
    engine/docs/MULTI_CLIENT_AUDIT.md instead of being reported per line.
    """
    body: list[str] = []
    dropped: list[str] = []
    for rule in rules:
        qx_type = QUANTUMULTX_TYPES.get(rule.kind)
        if qx_type is None:
            if rule.kind == "PROCESS-NAME":
                dropped.append(f"{rule.kind},{rule.value}")
                continue
            raise RendererError(f"quantumultx cannot express rule kind {rule.kind!r}")
        body.append(f"{qx_type},{rule.value},{QUANTUMULTX_POLICY_PLACEHOLDER}")
    if not body:
        raise RendererError("quantumultx output is empty after dropping unsupported rules")
    lines = [f"# 规则名称: {app_name}", f"# 规则统计: {len(body)}", "", *body]
    return "\n".join(lines) + "\n", dropped


def render_egern_yaml(rules: Iterable[object], app_name: str) -> tuple[str, list[str]]:
    """Serialize rules into Egern's ``*_set`` YAML rule-set schema.

    Returns ``(text, dropped)``.  ``dropped`` records every rule the schema
    cannot express (currently only PROCESS-NAME) so the build report keeps
    the downgrade auditable; it is never silent.

    ``no_resolve`` is set-level in Egern: it is emitted only when every IP
    rule carries ``no-resolve``, omitted when none does, and a mixed input
    raises ``RendererError`` because neither choice preserves semantics.
    """
    buckets: dict[str, list[str]] = {}
    dropped: list[str] = []
    ip_has_no_resolve: list[bool] = []
    for rule in rules:
        if rule.kind == "DOMAIN":
            bucket = "domain_set"
        elif rule.kind == "DOMAIN-SUFFIX":
            bucket = "domain_suffix_set"
        elif rule.kind == "DOMAIN-KEYWORD":
            bucket = "domain_keyword_set"
        elif rule.kind == "IP-CIDR":
            bucket = "ip_cidr_set"
        elif rule.kind == "IP-CIDR6":
            bucket = "ip_cidr6_set"
        elif rule.kind == "USER-AGENT":
            bucket = "user_agent_set"
        elif rule.kind == "PROCESS-NAME":
            dropped.append(f"{rule.kind},{rule.value}")
            continue
        else:
            raise RendererError(f"egern cannot express rule kind {rule.kind!r}")
        buckets.setdefault(bucket, []).append(rule.value)
        if bucket in {"ip_cidr_set", "ip_cidr6_set"}:
            ip_has_no_resolve.append("no-resolve" in rule.options)
    # Only a genuine mix is unexpressible.  ``ip_has_no_resolve`` is a list of
    # booleans, so the guard has to test ``any`` against ``all``: a non-empty
    # list of all-False means every IP rule lacks no-resolve, which is expressed
    # by omitting the set-level flag, not by failing.
    if any(ip_has_no_resolve) and not all(ip_has_no_resolve):
        raise RendererError(
            "egern no_resolve is set-level: mixing IP rules with and without "
            "no-resolve cannot be expressed losslessly"
        )

    document: dict[str, object] = {}
    if ip_has_no_resolve and all(ip_has_no_resolve):
        document["no_resolve"] = True
    for key in EGERN_KEY_ORDER:
        values = buckets.get(key)
        if values:
            document[key] = values
    if not any(key in document for key in EGERN_KEY_ORDER[1:]):
        raise RendererError("egern output is empty after dropping unsupported rules")

    emitted = sum(len(values) for key, values in document.items() if isinstance(values, list))
    header = f"# 规则名称: {app_name}\n# 规则统计: {emitted}\n\n"
    return header + yaml.safe_dump(document, sort_keys=False, allow_unicode=True), dropped


def render_for_client(
    client: ClientTarget, rules: Iterable[object], app_name: str
) -> tuple[str, list[str]]:
    """Dispatch to the renderer declared by the client target."""
    if client.renderer == "classical":
        return render_classical(rules, app_name), []
    if client.renderer == "classical-mihomo":
        return render_classical_mihomo(rules, app_name)
    if client.renderer == "egern-yaml":
        return render_egern_yaml(rules, app_name)
    if client.renderer == "quantumultx":
        return render_quantumultx(rules, app_name)
    raise RendererError(f"unknown renderer {client.renderer!r} for client {client.key!r}")
