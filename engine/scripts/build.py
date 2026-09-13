#!/usr/bin/env python3
"""Conservatively compile audited sources into canonical rules.

The default mode is a read-only preflight that renders every client target.
All seven client outputs and deterministic provenance are written only when
``--write`` is supplied after every selected app has compiled, rendered, and
passed the upstream semantic-change gate.
"""

from __future__ import annotations

import argparse
import dataclasses
import difflib
import hashlib
import ipaddress
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Callable, Iterable

import yaml

from renderers import (
    CLIENTS,
    RendererError,
    render_classical,
    render_classical_body,
    render_classical_mihomo,
    render_egern_yaml,
    render_for_client,
    render_quantumultx,
    render_surge_domainset,
    render_view,
)

# Re-exported on purpose: engine/tests asserts through the build.* namespace,
# so keep this module the single public surface (recognised by ruff's F401).
__all__ = [
    "CLIENTS",
    "RendererError",
    "render_classical",
    "render_classical_body",
    "render_classical_mihomo",
    "render_egern_yaml",
    "render_for_client",
    "render_quantumultx",
    "render_surge_domainset",
    "render_view",
]


# Canonical rule kinds.  The names happen to match Surge vocabulary, but the
# model is client-neutral: renderers own every client-specific serialization.
ALLOWED_RULE_TYPES = (
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "USER-AGENT",
    "PROCESS-NAME",
    "IP-CIDR",
    "IP-CIDR6",
)
SORT_ORDER = {rule_type: position for position, rule_type in enumerate(ALLOWED_RULE_TYPES)}
SAFE_INCLUDE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
SUPPORTED_SOURCE_FORMATS = {"v2fly-domain-list", "surge-rule-set"}
PROVENANCE_SCHEMA_VERSION = 1
PROVENANCE_FILENAME = "manifest.json"
BUILDER_VERSION = "2.0.0"

# Semantic phase of each canonical kind.  domain rules may be rendered as a
# DOMAIN-SET; nonip rules (user-agent / process-name / keyword) stay classical;
# ip rules always come after the domain/non-ip rules (domain-first / IP-last).
PHASE_BY_KIND = {
    "DOMAIN": "domain",
    "DOMAIN-SUFFIX": "domain",
    "DOMAIN-KEYWORD": "domain",
    "USER-AGENT": "nonip",
    "PROCESS-NAME": "nonip",
    "IP-CIDR": "ip",
    "IP-CIDR6": "ip",
}
VIEW_TYPES = {"domainset", "nonip", "ip"}


def phase_of(rule: Rule) -> str:
    return PHASE_BY_KIND.get(rule.kind, "nonip")


def semantic_views(rules: Iterable[Rule]) -> list[tuple[str, list[Rule]]]:
    """Split a canonical rule set into its semantic views.

    Returns ``(view_name, rules)`` pairs in matching order (non-ip before ip).
    A pure-domain (DOMAIN / DOMAIN-SUFFIX only, no keyword/UA/process) non-ip
    portion yields a ``domainset`` view; anything else yields a ``nonip``
    (classical) view.  Empty views are omitted, so a domain-only app never
    produces an empty IP file.
    """
    nonip = [rule for rule in rules if phase_of(rule) != "ip"]
    ip_rules = [rule for rule in rules if phase_of(rule) == "ip"]
    pure_domain = all(rule.kind in {"DOMAIN", "DOMAIN-SUFFIX"} for rule in nonip)
    views: list[tuple[str, list[Rule]]] = []
    if nonip:
        views.append(("domainset" if pure_domain else "nonip", nonip))
    if ip_rules:
        views.append(("ip", ip_rules))
    return views


class BuildError(RuntimeError):
    """A deterministic input or policy error that must stop a build."""


@dataclasses.dataclass(frozen=True)
class SourceLocation:
    source: str
    line: int
    chain: tuple[str, ...]

    def describe(self) -> str:
        chain = " -> ".join(self.chain)
        return f"{self.source}:{self.line} (include chain: {chain})"


@dataclasses.dataclass(frozen=True)
class ParsedEntry:
    kind: str
    value: str
    attributes: frozenset[str]
    location: SourceLocation


@dataclasses.dataclass(frozen=True)
class Rule:
    """One canonical, client-neutral, policy-free rule.

    ``kind``/``value`` describe what the rule matches; ``options`` keeps
    match modifiers such as ``no-resolve``.  Client serialization lives
    exclusively in ``renderers.py``.
    """

    kind: str
    value: str
    options: tuple[str, ...]
    location: SourceLocation

    @property
    def key(self) -> tuple[str, str, tuple[str, ...]]:
        return self.kind, self.value, self.options


@dataclasses.dataclass
class Compilation:
    app_name: str
    rules: list[Rule]
    skipped_attributes: list[ParsedEntry]
    denied_includes: list[tuple[str, SourceLocation]]
    provenance: dict[tuple[str, str, tuple[str, ...]], list[SourceLocation]]
    skipped_excluded: list[str] = dataclasses.field(default_factory=list)
    source_inputs: dict[str, str] = dataclasses.field(default_factory=dict)
    input_rules: int = 0
    views: list[tuple[str, list[Rule]]] = dataclasses.field(default_factory=list)
    # Hits per declared domain exclude, keyed by its ``type:value`` spec.  Every
    # declared exclude is present, so a zero means the exclude no longer matches
    # anything upstream.  Left empty when the canonical rules were reconstructed
    # from committed output instead of compiled, because only a live fetch can
    # establish it.
    excluded_domains: dict[str, int] = dataclasses.field(default_factory=dict)
    # IP rules whose text the canonical form changed, as ``before -> after``.
    # Reported, never silent: a host-bits-set CIDR widens what upstream wrote.
    rewritten_ip_rules: list[str] = dataclasses.field(default_factory=list)


FetchText = Callable[[str], str]


def load_manifest(path: Path) -> dict:
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise BuildError(f"cannot read manifest {path}: {error}") from error
    except yaml.YAMLError as error:
        raise BuildError(f"invalid YAML in {path}: {error}") from error
    if not isinstance(document, dict) or document.get("version") != 1:
        raise BuildError("manifest must be a mapping with version: 1")
    apps = document.get("apps")
    if not isinstance(apps, dict) or not apps:
        raise BuildError("manifest must contain a non-empty apps mapping")
    for app_name, app in apps.items():
        validate_app_config(app_name, app)
    return document


def validate_app_config(app_name: str, app: object) -> None:
    if not isinstance(app, dict):
        raise BuildError(f"{app_name}: app configuration must be a mapping")
    for key in (
        "enabled",
        "output",
        "sources",
        "supplement",
        "exclude",
        "include_policy",
        "attributes",
    ):
        if key not in app:
            raise BuildError(f"{app_name}: missing required field {key!r}")
    if not isinstance(app["enabled"], bool):
        raise BuildError(f"{app_name}: enabled must be boolean")
    if not isinstance(app["output"], str) or not app["output"].startswith("Surge/"):
        raise BuildError(f"{app_name}: output must be a path below Surge/")
    if not isinstance(app["supplement"], str) or not app["supplement"].startswith(
        "engine/sources/supplement/"
    ):
        raise BuildError(f"{app_name}: supplement must be a path below engine/sources/supplement/")
    if not isinstance(app["exclude"], list):
        raise BuildError(f"{app_name}: exclude must be a list")

    sources = app["sources"]
    if not isinstance(sources, list):
        raise BuildError(f"{app_name}: sources must be a list")
    primaries = 0
    supplementals = 0
    for source in sources:
        if not isinstance(source, dict):
            raise BuildError(f"{app_name}: each source must be a mapping")
        if source.get("format") not in SUPPORTED_SOURCE_FORMATS:
            raise BuildError(f"{app_name}: unsupported source format {source.get('format')!r}")
        if not isinstance(source.get("url"), str) or not source["url"].startswith("https://"):
            raise BuildError(f"{app_name}: source URL must use https")
        if source.get("role") == "primary":
            primaries += 1
        elif source.get("role") == "supplemental":
            supplementals += 1
        else:
            raise BuildError(f"{app_name}: source role must be primary or supplemental")
    if sources and (primaries != 1 or supplementals > 1):
        raise BuildError(
            f"{app_name}: require exactly one primary and at most one supplemental source"
        )
    # An empty sources list is a supplement-only app: every rule must come from
    # the local supplement file. It is reserved for apps where the source audit
    # proved that no upstream provides a usable rule set.

    include_policy = app["include_policy"]
    if not isinstance(include_policy, dict) or include_policy.get("mode") != "explicit":
        raise BuildError(f"{app_name}: include_policy.mode must be explicit")
    allow = include_policy.get("allow")
    deny = include_policy.get("deny")
    if (
        not isinstance(allow, list)
        or not isinstance(deny, list)
        or not all(isinstance(item, str) for item in allow + deny)
    ):
        raise BuildError(f"{app_name}: include_policy allow and deny must be string lists")
    overlap = set(allow) & set(deny)
    if overlap:
        raise BuildError(
            f"{app_name}: include targets cannot be both allowed and denied: {sorted(overlap)}"
        )

    attributes = app["attributes"]
    if not isinstance(attributes, dict) or attributes.get("mode") != "explicit":
        raise BuildError(f"{app_name}: attributes.mode must be explicit")
    selected = attributes.get("include")
    if not isinstance(selected, list) or not all(
        isinstance(item, str) and item and not item.startswith("!") for item in selected
    ):
        raise BuildError(
            f"{app_name}: attributes.include must be a list of positive attribute names"
        )


FETCH_ATTEMPTS = 3
FETCH_TIMEOUT_SECONDS = 20


def default_fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Blink/1"})
    last_network_error: Exception | None = None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
                content_type = response.headers.get_content_type()
                raw = response.read()
            break
        except urllib.error.HTTPError as error:
            # Deterministic upstream errors are not retried.
            raise BuildError(f"upstream HTTP {error.code} for {url}") from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            last_network_error = error
            if attempt < FETCH_ATTEMPTS:
                time.sleep(1.0 * attempt)
    else:
        raise BuildError(
            f"upstream fetch failed for {url}: {last_network_error}"
        ) from last_network_error
    if content_type == "text/html" or raw.lstrip().lower().startswith(
        (b"<!doctype html", b"<html")
    ):
        raise BuildError(f"upstream returned HTML instead of a rule list: {url}")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise BuildError(f"upstream is not UTF-8 text: {url}") from error


def parse_v2fly_text(text: str, source: str, chain: tuple[str, ...]) -> list[ParsedEntry]:
    entries: list[ParsedEntry] = []
    for line_number, original in enumerate(text.splitlines(), start=1):
        stripped = original.strip()
        if not stripped or stripped.startswith("#"):
            continue
        tokens = stripped.split()
        head, *tail = tokens
        attributes = frozenset(token[1:] for token in tail if token.startswith("@"))
        values = [token for token in tail if not token.startswith("@")]
        location = SourceLocation(source, line_number, chain)
        if any(attribute.startswith("!") for attribute in attributes):
            raise BuildError(
                f"v1 does not support negative attributes at {location.describe()}: {original}"
            )

        if ":" not in head:
            if values:
                raise BuildError(f"malformed v2fly line at {location.describe()}: {original}")
            entries.append(ParsedEntry("domain", head, attributes, location))
            continue

        directive, value = head.split(":", 1)
        if (
            directive not in {"domain", "full", "keyword", "regexp", "include"}
            or not value
            or values
        ):
            raise BuildError(
                f"unsupported or malformed v2fly directive at {location.describe()}: {original}"
            )
        if directive == "include" and attributes:
            raise BuildError(
                f"attribute-qualified include is unsupported in v1 at {location.describe()}: {original}"
            )
        entries.append(ParsedEntry(directive, value, attributes, location))
    return entries


def include_url(parent_url: str, include_name: str) -> str:
    if not SAFE_INCLUDE_NAME.fullmatch(include_name):
        raise BuildError(f"unsafe v2fly include name {include_name!r}")
    base, _, _ = parent_url.rpartition("/")
    if not base:
        raise BuildError(f"cannot resolve include from malformed source URL {parent_url!r}")
    return f"{base}/{include_name}"


def normalize_domain(value: str, location: SourceLocation) -> str:
    candidate = value.rstrip(".").lower()
    if not candidate or any(character in candidate for character in "/,:@ \t"):
        raise BuildError(f"invalid domain at {location.describe()}: {value!r}")
    try:
        encoded = candidate.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise BuildError(f"invalid IDNA domain at {location.describe()}: {value!r}") from error
    labels = encoded.split(".")
    if any(
        not label
        or len(label) > 63
        or not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in labels
    ):
        raise BuildError(f"invalid domain at {location.describe()}: {value!r}")
    return encoded


def convert_entry(entry: ParsedEntry) -> Rule:
    if entry.kind == "regexp":
        raise BuildError(
            f"unsupported v2fly regexp at {entry.location.describe()}: {entry.value!r}"
        )
    if entry.kind == "domain":
        return Rule(
            "DOMAIN-SUFFIX", normalize_domain(entry.value, entry.location), (), entry.location
        )
    if entry.kind == "full":
        return Rule("DOMAIN", normalize_domain(entry.value, entry.location), (), entry.location)
    if entry.kind == "keyword":
        value = entry.value.lower()
        if not value or any(character in value for character in ",\r\n"):
            raise BuildError(
                f"invalid domain keyword at {entry.location.describe()}: {entry.value!r}"
            )
        return Rule("DOMAIN-KEYWORD", value, (), entry.location)
    raise BuildError(f"cannot convert v2fly entry {entry.kind!r} at {entry.location.describe()}")


def normalize_surge_rule(
    kind: str,
    value: str,
    options: tuple[str, ...],
    location: SourceLocation,
) -> Rule:
    """Validate and canonicalize one policy-free native Surge rule."""
    if kind not in ALLOWED_RULE_TYPES:
        raise BuildError(f"unsupported Surge rule type at {location.describe()}: {kind!r}")
    if kind in {"DOMAIN", "DOMAIN-SUFFIX"}:
        if options:
            raise BuildError(f"unexpected option for {kind} at {location.describe()}: {options!r}")
        return Rule(kind, normalize_domain(value, location), (), location)
    if kind == "DOMAIN-KEYWORD":
        if options:
            raise BuildError(
                f"unexpected option for DOMAIN-KEYWORD at {location.describe()}: {options!r}"
            )
        normalized = value.lower()
        if not normalized or any(character in normalized for character in ",\r\n\t"):
            raise BuildError(f"invalid domain keyword at {location.describe()}: {value!r}")
        return Rule(kind, normalized, (), location)
    if kind in {"USER-AGENT", "PROCESS-NAME"}:
        if options:
            raise BuildError(f"unexpected option for {kind} at {location.describe()}: {options!r}")
        if not value or any(character in value for character in ",\r\n"):
            raise BuildError(f"invalid {kind} value at {location.describe()}: {value!r}")
        return Rule(kind, value, (), location)

    if options not in {(), ("no-resolve",)}:
        raise BuildError(f"unsupported {kind} option at {location.describe()}: {options!r}")
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as error:
        raise BuildError(f"invalid IP rule at {location.describe()}: {value!r}") from error
    expected = "IP-CIDR6" if network.version == 6 else "IP-CIDR"
    if kind != expected:
        raise BuildError(
            f"IP family does not match rule type at {location.describe()}: {kind},{value}"
        )
    return Rule(kind, str(network), options, location)


def parse_surge_rule_set_text(
    text: str,
    source: str,
    chain: tuple[str, ...],
    skip_kinds: set[str] | None = None,
    skipped: list[str] | None = None,
    rewritten: list[str] | None = None,
) -> list[Rule]:
    """Parse a deliberately small, policy-free subset of native Surge syntax.

    A source rule must be one of the explicitly supported output types.  It
    cannot carry a policy name: domain, keyword, user-agent, and process rules
    have exactly two fields; IP rules may additionally use ``no-resolve``.

    ``skip_kinds`` drops rule kinds that the manifest explicitly excluded at
    the type level (for example ``IP-ASN`` or ``URL-REGEX``) instead of failing
    the build.  Dropped lines are recorded in ``skipped`` so the decision stays
    auditable in the build report.

    ``rewritten`` collects IP rules whose text the canonicalization changed, as
    ``before -> after``.  ``ipaddress.ip_network(strict=False)`` turns
    ``IP-CIDR,1.2.3.4/24`` into ``1.2.3.0/24`` and a bare address into ``/32``;
    both are standard CIDR readings, but the first widens what the upstream
    author actually wrote, so the repository must not transform it silently.
    """
    rules: list[Rule] = []
    for line_number, original in enumerate(text.splitlines(), start=1):
        stripped = original.strip()
        if not stripped or stripped.startswith(("#", ";", "//")):
            continue
        location = SourceLocation(source, line_number, chain)
        parts = [part.strip() for part in stripped.split(",")]
        if len(parts) < 2 or any(not part for part in parts):
            raise BuildError(f"malformed Surge rule at {location.describe()}: {original}")
        kind, value, *option_parts = parts
        if skip_kinds and kind in skip_kinds:
            if skipped is not None:
                skipped.append(f"{kind},{value}")
            continue
        rule = normalize_surge_rule(kind, value, tuple(option_parts), location)
        if rewritten is not None and rule.kind in {"IP-CIDR", "IP-CIDR6"} and rule.value != value:
            rewritten.append(f"{kind},{value} -> {rule.value}")
        rules.append(rule)
    return rules


def parse_excludes(
    items: Iterable[object], app_name: str
) -> tuple[list[tuple[str, str, str]], set[str]]:
    """Return concrete domain excludes plus rule kinds to skip at parse time.

    Domain entries use ``type:value`` syntax.  ``ip-asn:*`` and ``url-regex:*``
    are type-level exclusions: those kinds are dropped from native Surge sources
    because v1 does not emit them, and the manifest decision stays explicit.
    ``regexp:*`` is the corresponding exclusion for v2fly ``regexp:`` entries.

    Each domain exclude keeps its original ``type:value`` spec as the third
    element so a drop can be attributed back to the manifest entry that caused
    it; type-level exclusions are already reported through ``skipped_excluded``.
    """
    excludes: list[tuple[str, str, str]] = []
    skipped_kinds: set[str] = set()
    mappings = {
        "domain": "DOMAIN",
        "domain-suffix": "DOMAIN-SUFFIX",
        "domain-keyword": "DOMAIN-KEYWORD",
    }
    type_only = {"ip-asn": "IP-ASN", "url-regex": "URL-REGEX", "regexp": "REGEX"}
    for item in items:
        if not isinstance(item, str) or ":" not in item:
            raise BuildError(f"{app_name}: exclude entries must use type:value syntax")
        kind, value = item.split(":", 1)
        if kind in type_only:
            if value != "*":
                raise BuildError(
                    f"{app_name}: type-level exclude {kind!r} must use '*' as its value"
                )
            skipped_kinds.add(type_only[kind])
            continue
        if kind not in mappings or not value:
            raise BuildError(f"{app_name}: unsupported exclude {item!r}")
        location = SourceLocation(f"manifest:{app_name}", 0, (app_name,))
        normalized = (
            value.lower() if kind == "domain-keyword" else normalize_domain(value, location)
        )
        excludes.append((mappings[kind], normalized, item))
    return excludes, skipped_kinds


def matching_exclude(rule: Rule, excludes: Iterable[tuple[str, str, str]]) -> str | None:
    """Return the ``type:value`` spec that drops this rule, or None.

    Matching is deliberately narrow: a ``domain-suffix`` exclude covers the
    suffix rule itself and any ``DOMAIN`` below it, but not a narrower
    ``DOMAIN-SUFFIX`` beneath it.  Returning the spec instead of a boolean lets
    the caller count hits per exclude, so an exclude that silently stopped
    matching upstream becomes visible in the provenance manifest.
    """
    for kind, value, spec in excludes:
        if kind == "DOMAIN" and rule.kind == "DOMAIN" and rule.value == value:
            return spec
        if kind == "DOMAIN-KEYWORD" and rule.kind == "DOMAIN-KEYWORD" and rule.value == value:
            return spec
        if kind == "DOMAIN-SUFFIX":
            if rule.kind == "DOMAIN-SUFFIX" and rule.value == value:
                return spec
            if rule.kind == "DOMAIN" and (rule.value == value or rule.value.endswith(f".{value}")):
                return spec
    return None


def parse_supplement(path: Path, app_name: str, rewritten: list[str] | None = None) -> list[Rule]:
    if not path.exists():
        return []
    try:
        return parse_surge_rule_set_text(
            path.read_text(encoding="utf-8-sig"),
            str(path),
            (app_name, "supplement"),
            rewritten=rewritten,
        )
    except BuildError as error:
        raise BuildError(f"invalid supplement rule in {path}: {error}") from error


def compile_app(
    app_name: str, app: dict, root: Path, fetch_text: FetchText = default_fetch_text
) -> Compilation:
    allow = set(app["include_policy"]["allow"])
    deny = set(app["include_policy"]["deny"])
    selected_attributes = set(app["attributes"]["include"])
    cached_entries: dict[str, list[ParsedEntry]] = {}
    cached_surge_rules: dict[str, list[Rule]] = {}
    stack: list[str] = []
    rules: list[Rule] = []
    skipped_attributes: list[ParsedEntry] = []
    denied_includes: list[tuple[str, SourceLocation]] = []
    skipped_excluded: list[str] = []
    rewritten_ip_rules: list[str] = []
    source_inputs: dict[str, str] = {}
    excludes, skip_kinds = parse_excludes(app["exclude"], app_name)

    def fetch_recorded(url: str) -> str:
        text = fetch_text(url)
        source_inputs[url] = text
        return text

    def resolve(url: str, list_name: str, chain: tuple[str, ...]) -> None:
        if list_name in stack:
            cycle = " -> ".join((*stack, list_name))
            raise BuildError(f"include cycle for {app_name}: {cycle}")
        stack.append(list_name)
        if url not in cached_entries:
            cached_entries[url] = parse_v2fly_text(fetch_recorded(url), url, chain)
        for parsed in cached_entries[url]:
            location = SourceLocation(parsed.location.source, parsed.location.line, chain)
            entry = dataclasses.replace(parsed, location=location)
            if entry.kind == "include":
                target = entry.value
                if target in allow:
                    resolve(include_url(url, target), target, (*chain, target))
                elif target in deny:
                    denied_includes.append((target, entry.location))
                else:
                    raise BuildError(
                        f"{app_name}: include {target!r} is not declared in include_policy at {entry.location.describe()}"
                    )
                continue
            if entry.attributes and not (set(entry.attributes) & selected_attributes):
                skipped_attributes.append(entry)
                continue
            if entry.kind == "regexp" and "REGEX" in skip_kinds:
                skipped_excluded.append(entry.value)
                continue
            rules.append(convert_entry(entry))
        stack.pop()

    for source in app["sources"]:
        source_name = source["name"]
        if source["format"] == "v2fly-domain-list":
            resolve(source["url"], source_name, (source_name,))
        else:
            source_url = source["url"]
            if source_url not in cached_surge_rules:
                cached_surge_rules[source_url] = parse_surge_rule_set_text(
                    fetch_recorded(source_url),
                    source_url,
                    (source_name,),
                    skip_kinds,
                    skipped_excluded,
                    rewritten_ip_rules,
                )
            rules.extend(cached_surge_rules[source_url])

    rules.extend(parse_supplement(root / app["supplement"], app_name, rewritten_ip_rules))
    input_rules = len(rules)
    provenance: dict[tuple[str, str, tuple[str, ...]], list[SourceLocation]] = defaultdict(list)
    unique: dict[tuple[str, str, tuple[str, ...]], Rule] = {}
    excluded_domains = {spec: 0 for _kind, _value, spec in excludes}
    for rule in rules:
        spec = matching_exclude(rule, excludes)
        if spec is not None:
            excluded_domains[spec] += 1
            continue
        provenance[rule.key].append(rule.location)
        unique.setdefault(rule.key, rule)
    ordered = sorted(unique.values(), key=lambda rule: (SORT_ORDER[rule.kind], rule.value))
    if not ordered:
        raise BuildError(f"{app_name}: final output is empty")
    return Compilation(
        app_name,
        ordered,
        skipped_attributes,
        denied_includes,
        dict(provenance),
        skipped_excluded,
        source_inputs,
        input_rules,
        semantic_views(ordered),
        excluded_domains,
        rewritten_ip_rules,
    )


def rendered_outputs(
    compilation: Compilation, manifest: dict, root: Path
) -> dict[str, tuple[Path, str, list[str]]]:
    """Render one compilation for every client and resolve output paths.

    The manifest ``output`` field keeps naming the Surge file (backward
    compatibility); other clients derive their path from the same stem under
    their own directory.  Returns ``{client_key: (path, text, dropped)}``.
    """
    app = manifest["apps"][compilation.app_name]
    surge_path = root / app["output"]
    stem = surge_path.stem
    outputs: dict[str, tuple[Path, str, list[str]]] = {}
    for key, client in CLIENTS.items():
        if key == "surge":
            path = surge_path
        else:
            path = root / client.directory / f"{stem}{client.suffix}"
        try:
            text, dropped = render_for_client(client, compilation.rules, compilation.app_name)
        except RendererError as error:
            raise BuildError(f"{compilation.app_name}: {key} render failed: {error}") from error
        outputs[key] = (path, text, dropped)
    return outputs


def client_view_outputs(
    compilation: Compilation, root: Path, *, enabled: bool
) -> dict[str, dict[str, tuple[Path, str, int]]]:
    """Render per-client semantic views (domainset / nonip / ip) for one app.

    Views are produced for every client only when ``enabled`` (an explicit
    ``views: true`` in apps.yaml).  View payloads are policy-free rule-set
    content; the legacy per-client main output stays unchanged.  View files use
    a ``.conf`` suffix so parity (which globs the main ``.list``/``.yaml``) does
    not mistake them for the main output.
    """
    if not enabled:
        return {}
    outputs: dict[str, dict[str, tuple[Path, str, int]]] = {}
    for client_key, client in CLIENTS.items():
        client_views: dict[str, tuple[Path, str, int]] = {}
        for view_name, view_rules in compilation.views:
            text = render_view(client_key, view_name, view_rules, compilation.app_name)
            path = root / client.directory / f"{compilation.app_name}-{view_name}.conf"
            client_views[view_name] = (path, text, len(view_rules))
        outputs[client_key] = client_views
    return outputs


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_rules_sha256(rules: Iterable[Rule]) -> str:
    payload = [list(rule.key) for rule in rules]
    return sha256_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))


def _relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def app_provenance_record(
    compilation: Compilation,
    app: dict,
    outputs: dict[str, tuple[Path, str, list[str]]],
    root: Path,
) -> dict:
    """Build one deterministic provenance record from the exact build inputs."""
    declared_sources = {source["url"]: source for source in app["sources"]}
    sources = []
    for url, text in sorted(compilation.source_inputs.items()):
        declared = declared_sources.get(url)
        source = {
            "url": url,
            "role": declared["role"] if declared else "include",
            "format": declared["format"] if declared else "v2fly-domain-list",
            "text_sha256": sha256_text(text),
            "bytes": len(text.encode("utf-8")),
            "lines": len(text.splitlines()),
        }
        if declared:
            source["name"] = declared["name"]
            source["author"] = declared.get("author", "")
        sources.append(source)

    supplement_path = root / app["supplement"]
    supplement = None
    if supplement_path.exists():
        content = supplement_path.read_bytes()
        supplement = {
            "path": _relative_path(supplement_path, root),
            "sha256": sha256_bytes(content),
            "bytes": len(content),
            "lines": len(content.decode("utf-8-sig").splitlines()),
        }

    output_records = {}
    for client, (path, text, dropped) in outputs.items():
        output_records[client] = {
            "path": _relative_path(path, root),
            "sha256": sha256_text(text),
            "rules": len(compilation.rules) - len(dropped),
            "dropped": dropped,
        }

    views = {}
    for client_key, client_views in client_view_outputs(
        compilation, root, enabled=bool(app.get("views"))
    ).items():
        views[client_key] = {}
        for view_name, (path, text, count) in client_views.items():
            views[client_key][view_name] = {
                "path": _relative_path(path, root),
                "sha256": sha256_text(text),
                "rules": count,
            }

    canonical = {
        "rules": len(compilation.rules),
        "sha256": canonical_rules_sha256(compilation.rules),
        "input_rules": compilation.input_rules,
        "skipped_attributes": len(compilation.skipped_attributes),
        "skipped_excluded": compilation.skipped_excluded,
        "denied_includes": sorted(name for name, _location in compilation.denied_includes),
        "views": [{"name": name, "rules": len(rules)} for name, rules in compilation.views],
    }
    # Domain-level excludes used to vanish without a trace, unlike the type-level
    # ones recorded in ``skipped_excluded``.  Recording hits per declared spec
    # makes the drop auditable and turns an exclude that stopped matching
    # upstream into a visible manifest diff on the next daily commit.  Omitted
    # for apps that declare no domain exclude, and when the record is being
    # refreshed from committed output (no live fetch to count against).
    if compilation.excluded_domains:
        canonical["excluded_domains"] = dict(sorted(compilation.excluded_domains.items()))

    return {
        "sources": sources,
        "supplement": supplement,
        "canonical": canonical,
        "outputs": output_records,
        "views": views,
    }


def build_provenance_manifest(
    compilations: list[Compilation],
    source_manifest: dict,
    rendered: list[dict[str, tuple[Path, str, list[str]]]],
    root: Path,
    *,
    preserve_unselected: bool,
) -> dict:
    """Return the deterministic repository-level artifact manifest."""
    path = root / PROVENANCE_FILENAME
    existing_apps: dict[str, object] = {}
    if preserve_unselected:
        if not path.exists():
            raise BuildError(
                "targeted --write requires an existing manifest.json; run a full --write once"
            )
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BuildError(f"cannot preserve existing provenance manifest: {error}") from error
        if not isinstance(existing, dict) or not isinstance(existing.get("apps"), dict):
            raise BuildError("existing manifest.json has an invalid apps mapping")
        existing_apps = dict(existing["apps"])

    for compilation, client_outputs in zip(compilations, rendered):
        existing_apps[compilation.app_name] = app_provenance_record(
            compilation,
            source_manifest["apps"][compilation.app_name],
            client_outputs,
            root,
        )

    enabled = {name for name, app in source_manifest["apps"].items() if app.get("enabled") is True}
    existing_apps = {name: existing_apps[name] for name in sorted(existing_apps) if name in enabled}
    if set(existing_apps) != enabled:
        missing = ", ".join(sorted(enabled - set(existing_apps)))
        raise BuildError(
            f"provenance manifest would be incomplete; missing enabled apps: {missing}"
        )

    source_definition = root / "engine" / "sources" / "apps.yaml"
    # Fingerprint the builder *in the repository being built*, which is exactly
    # what verify_manifest.py resolves and checks.  Using ``__file__`` would
    # instead describe whichever copy happens to be executing.
    builder_files = {}
    for relative in ("engine/scripts/build.py", "engine/scripts/renderers.py"):
        path = root.joinpath(*relative.split("/"))
        if not path.is_file():
            raise BuildError(f"cannot fingerprint the builder: missing {relative}")
        builder_files[relative] = sha256_bytes(path.read_bytes())
    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "builder": {
            "version": BUILDER_VERSION,
            "files": builder_files,
        },
        "source_definition": {
            "path": _relative_path(source_definition, root),
            "sha256": sha256_bytes(source_definition.read_bytes()),
        },
        "apps": existing_apps,
    }


def provenance_text(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _current_rule_keys(path: Path, app_name: str) -> set[tuple[str, str, tuple[str, ...]]]:
    if not path.exists():
        return set()
    rules = parse_surge_rule_set_text(
        path.read_text(encoding="utf-8-sig"), str(path), (app_name, "committed")
    )
    return {rule.key for rule in rules}


def assess_changes(
    compilations: list[Compilation],
    source_manifest: dict,
    root: Path,
    *,
    threshold_lines: int,
    threshold_ratio: float,
) -> tuple[list[dict], list[str]]:
    """Compare live canonical rules with committed Surge outputs before writing."""
    report = []
    violations = []
    for compilation in compilations:
        output = root / source_manifest["apps"][compilation.app_name]["output"]
        existed = output.exists()
        old = _current_rule_keys(output, compilation.app_name)
        new = {rule.key for rule in compilation.rules}
        added = sorted(new - old)
        removed = sorted(old - new)
        changed = len(added) + len(removed)
        ratio = changed / max(len(old), 1)
        new_kinds = sorted({key[0] for key in new} - {key[0] for key in old}) if existed else []
        entry = {
            "name": compilation.app_name,
            "old_rules": len(old),
            "new_rules": len(new),
            "added": len(added),
            "removed": len(removed),
            "change_ratio": round(ratio, 6),
            "new_rule_types": new_kinds,
            "added_sample": [list(key) for key in added[:5]],
            "removed_sample": [list(key) for key in removed[:5]],
        }
        report.append(entry)
        if existed and (
            max(len(added), len(removed)) > threshold_lines or ratio > threshold_ratio or new_kinds
        ):
            violations.append(
                f"{compilation.app_name}: +{len(added)}/-{len(removed)} "
                f"({ratio:.1%}), new types={new_kinds or 'none'}"
            )
    return report, violations


def verify_rendered_files(
    rendered: list[dict[str, tuple[Path, str, list[str]]]], root: Path
) -> list[str]:
    """Byte-compare every rendered client output against its committed file."""
    errors = []
    for client_outputs in rendered:
        for path, expected, _dropped in client_outputs.values():
            if not path.exists():
                errors.append(f"missing generated output: {_relative_path(path, root)}")
                continue
            actual = path.read_text(encoding="utf-8")
            if actual != expected:
                diff = "\n".join(
                    list(
                        difflib.unified_diff(
                            actual.splitlines(),
                            expected.splitlines(),
                            fromfile=f"committed/{_relative_path(path, root)}",
                            tofile=f"rebuilt/{_relative_path(path, root)}",
                            lineterm="",
                        )
                    )[:20]
                )
                errors.append(f"drift: {_relative_path(path, root)}\n{diff}")
    return errors


def verify_rendered_views(
    compilations: Iterable[Compilation], manifest: dict, root: Path
) -> list[str]:
    """Byte-compare the semantic-view files and report orphans.

    An orphan is a view file the current split no longer produces (an app that
    lost its last IP rule, or whose ``nonip`` view became a pure-domain
    ``domainset``).  ``validate_views.py`` rejects those as spurious, so naming
    them here keeps the diagnosis in the tool that can see why they appeared.
    """
    errors = []
    for compilation in compilations:
        app = manifest["apps"][compilation.app_name]
        enabled = bool(app.get("views"))
        produced: set[Path] = set()
        for client_views in client_view_outputs(compilation, root, enabled=enabled).values():
            for path, expected, _count in client_views.values():
                produced.add(path)
                if not path.exists():
                    errors.append(f"missing generated view: {_relative_path(path, root)}")
                elif path.read_text(encoding="utf-8") != expected:
                    errors.append(f"drift: {_relative_path(path, root)}")
        for client in CLIENTS.values():
            for view_name in sorted(VIEW_TYPES):
                path = root / client.directory / f"{compilation.app_name}-{view_name}.conf"
                if path not in produced and path.is_file():
                    errors.append(f"orphan view no longer produced: {_relative_path(path, root)}")
    return errors


def verify_rendered_outputs(
    rendered: list[dict[str, tuple[Path, str, list[str]]]], expected_manifest: dict, root: Path
) -> list[str]:
    """Return concise byte-drift diagnostics without mutating the repository."""
    errors = verify_rendered_files(rendered, root)
    manifest_path = root / PROVENANCE_FILENAME
    expected_text = provenance_text(expected_manifest)
    if not manifest_path.exists():
        errors.append(f"missing generated provenance: {PROVENANCE_FILENAME}")
    elif manifest_path.read_text(encoding="utf-8") != expected_text:
        errors.append(f"drift: {PROVENANCE_FILENAME}")
    return errors


def write_outputs(
    compilations: Iterable[Compilation],
    manifest: dict,
    root: Path,
    rendered: Iterable[dict[str, tuple[Path, str, list[str]]]] | None = None,
) -> None:
    compilations = list(compilations)
    client_outputs = (
        list(rendered)
        if rendered is not None
        else [rendered_outputs(compilation, manifest, root) for compilation in compilations]
    )
    for outputs in client_outputs:
        for output, text, _dropped in outputs.values():
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_suffix(output.suffix + ".tmp")
            temporary.write_text(text, encoding="utf-8", newline="\n")
            temporary.replace(output)


def write_client_views(compilations: Iterable[Compilation], manifest: dict, root: Path) -> None:
    """Write the per-client semantic-view files for apps that opted in via ``views: true``."""
    for compilation in compilations:
        app = manifest["apps"][compilation.app_name]
        if not app.get("views"):
            continue
        for client_views in client_view_outputs(compilation, root, enabled=True).values():
            for path, text, _count in client_views.values():
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(path.suffix + ".tmp")
                temporary.write_text(text, encoding="utf-8", newline="\n")
                temporary.replace(path)


def prune_stale_views(compilations: Iterable[Compilation], manifest: dict, root: Path) -> list[str]:
    """Delete view files the current semantic split no longer produces.

    ``semantic_views`` omits empty views, so an app that loses its last IP rule
    upstream, or whose ``nonip`` view becomes a pure-domain ``domainset``, leaves
    the previous file on disk.  ``validate_views.py`` then rejects it as spurious
    and every later daily run fails until someone deletes it by hand, even though
    the build itself was correct.

    Only the exact generated name ``<App>-<view>.conf`` inside the seven client
    directories is considered, and only for the apps of this build, so nothing
    outside the generated naming convention can be removed.  Removals are
    returned for the build report; they are never silent.
    """
    removed: list[str] = []
    for compilation in compilations:
        app = manifest["apps"][compilation.app_name]
        produced = {name for name, _rules in compilation.views} if app.get("views") else set()
        for view_name in sorted(VIEW_TYPES - produced):
            for client in CLIENTS.values():
                path = root / client.directory / f"{compilation.app_name}-{view_name}.conf"
                if path.is_file():
                    path.unlink()
                    removed.append(_relative_path(path, root))
    return removed


def write_provenance(document: dict, root: Path) -> None:
    output = root / PROVENANCE_FILENAME
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(provenance_text(document), encoding="utf-8", newline="\n")
    temporary.replace(output)


# Canonical facts only a live upstream fetch can establish.  A provenance
# refresh carries them over from the existing manifest instead of inventing them.
CARRIED_CANONICAL_FIELDS = (
    "input_rules",
    "skipped_attributes",
    "skipped_excluded",
    "denied_includes",
    "excluded_domains",
)


def compilation_from_committed(app_name: str, app: dict, root: Path) -> Compilation:
    """Reconstruct an app's canonical rules from its committed classical output.

    The Surge file is the canonical serialization, so the rule set, every client
    rendering and the semantic split are all derivable from it offline.  Counters
    that depend on the upstream input stay empty on purpose (see
    ``CARRIED_CANONICAL_FIELDS``).
    """
    output = root / app["output"]
    if not output.is_file():
        raise BuildError(f"{app_name}: missing committed output {app['output']}")
    rules = parse_surge_rule_set_text(
        output.read_text(encoding="utf-8"),
        _relative_path(output, root),
        (app_name, "committed"),
    )
    if not rules:
        raise BuildError(f"{app_name}: committed output is empty")
    return Compilation(app_name, rules, [], [], {}, views=semantic_views(rules))


def _carried_sources(app_name: str, app: dict, record: dict) -> list[dict]:
    """Re-attach apps.yaml metadata to the upstream fingerprints already recorded."""
    recorded = record.get("sources")
    if not isinstance(recorded, list):
        raise BuildError(f"{app_name}: existing provenance sources must be a list")
    declared = {source["url"]: source for source in app["sources"]}
    fingerprinted = {item.get("url") for item in recorded if isinstance(item, dict)}
    unknown = sorted(set(declared) - fingerprinted)
    if unknown:
        raise BuildError(
            f"{app_name}: apps.yaml declares upstream(s) with no recorded fingerprint "
            f"({', '.join(unknown)}); the content changed, so run a full --write instead"
        )
    sources = []
    for item in recorded:
        if not isinstance(item, dict) or not isinstance(item.get("url"), str):
            raise BuildError(f"{app_name}: invalid recorded source entry")
        entry = dict(item)
        source = declared.get(entry["url"])
        if source:
            entry["role"] = source["role"]
            entry["format"] = source["format"]
            entry["name"] = source["name"]
            entry["author"] = source.get("author", "")
        sources.append(entry)
    return sources


def refresh_provenance(manifest: dict, root: Path) -> dict:
    """Rebuild manifest.json from committed artifacts, without touching the network.

    Editing ``build.py`` or ``renderers.py`` invalidates the builder fingerprints
    the manifest records, which fails ``verify_manifest.py``.  Regenerating it with
    a live ``--write`` would drag that day's upstream content changes into what is
    meant to be a code-only commit, so this mode recomputes every fingerprint that
    is derivable from the committed artifacts and carries the rest over.

    It is only valid for changes that do not alter the pipeline's output, and it
    proves that: the committed outputs and views must still re-render byte-for-byte
    from the committed canonical rules, and the declared upstream set must still
    match what the existing manifest fingerprinted.  Otherwise it refuses and asks
    for a real ``--write``.
    """
    path = root / PROVENANCE_FILENAME
    if not path.exists():
        raise BuildError(f"--refresh-provenance requires an existing {PROVENANCE_FILENAME}")
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BuildError(f"cannot read {PROVENANCE_FILENAME}: {error}") from error
    if not isinstance(existing, dict) or not isinstance(existing.get("apps"), dict):
        raise BuildError(f"{PROVENANCE_FILENAME} has an invalid apps mapping")
    existing_apps = existing["apps"]

    names = [name for name, app in manifest["apps"].items() if app["enabled"]]
    missing = sorted(set(names) - set(existing_apps))
    if missing:
        raise BuildError(
            "--refresh-provenance cannot invent upstream fingerprints for "
            f"{', '.join(missing)}; run a full --write instead"
        )

    compilations = [
        compilation_from_committed(name, manifest["apps"][name], root) for name in names
    ]
    rendered = [rendered_outputs(compilation, manifest, root) for compilation in compilations]
    drift = verify_rendered_files(rendered, root) + verify_rendered_views(
        compilations, manifest, root
    )
    if drift:
        raise BuildError(
            "--refresh-provenance only refreshes fingerprints, but the committed artifacts no "
            "longer match what the current renderers produce from them; this is not a "
            "provenance-only change, so run a full --write:\n" + "\n".join(drift)
        )

    document = build_provenance_manifest(
        compilations, manifest, rendered, root, preserve_unselected=False
    )
    for name in names:
        record = existing_apps[name]
        if not isinstance(record, dict) or not isinstance(record.get("canonical"), dict):
            raise BuildError(f"{name}: existing provenance record is malformed")
        refreshed = document["apps"][name]
        refreshed["sources"] = _carried_sources(name, manifest["apps"][name], record)
        for field in CARRIED_CANONICAL_FIELDS:
            if field in record["canonical"]:
                refreshed["canonical"][field] = record["canonical"][field]
        # Carrying a stale exclude record forward would produce a manifest that
        # verify_manifest.py rejects.  A changed exclude also changes the rules,
        # so this is a content change and belongs to a real --write.
        carried_excludes = refreshed["canonical"].get("excluded_domains")
        declared_excludes = {
            item
            for item in manifest["apps"][name]["exclude"]
            if isinstance(item, str) and not item.endswith(":*")
        }
        if carried_excludes is not None and set(carried_excludes) != declared_excludes:
            raise BuildError(
                f"{name}: apps.yaml declares different domain excludes than the recorded "
                "ones; the canonical rules changed, so run a full --write instead"
            )
    return document


def select_apps(manifest: dict, requested: list[str]) -> list[str]:
    if requested:
        unknown = set(requested) - set(manifest["apps"])
        if unknown:
            raise BuildError(f"unknown app(s): {', '.join(sorted(unknown))}")
        return requested
    return [name for name, app in manifest["apps"].items() if app["enabled"]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("engine/sources/apps.yaml"))
    parser.add_argument(
        "--app", action="append", default=[], help="compile only this app; may be repeated"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write",
        action="store_true",
        help="write outputs and deterministic provenance after every selected app compiles",
    )
    mode.add_argument(
        "--verify-only",
        action="store_true",
        help="rebuild from live sources and fail if committed outputs or provenance drift",
    )
    mode.add_argument(
        "--refresh-provenance",
        action="store_true",
        help=(
            "offline: rewrite manifest.json from the committed artifacts after a "
            "builder change that does not alter any output"
        ),
    )
    parser.add_argument(
        "--strict-diff",
        action="store_true",
        help="compatibility alias; verify-only always uses strict byte comparison",
    )
    parser.add_argument(
        "--change-threshold-lines",
        type=int,
        default=20,
        help="block --write when added or removed rules exceed this count (default: 20)",
    )
    parser.add_argument(
        "--change-threshold-ratio",
        type=float,
        default=0.2,
        help="block --write when semantic change ratio exceeds this value (default: 0.2)",
    )
    parser.add_argument(
        "--accept-large-change",
        action="store_true",
        help="allow a reviewed upstream change that exceeds the write thresholds",
    )
    arguments = parser.parse_args(argv)
    root = arguments.manifest.resolve().parent.parent.parent
    try:
        if arguments.verify_only and arguments.app:
            raise BuildError(
                "--verify-only is a full-repository gate and cannot be combined with --app"
            )
        if arguments.change_threshold_lines < 0:
            raise BuildError("--change-threshold-lines must be non-negative")
        if not 0 <= arguments.change_threshold_ratio <= 1:
            raise BuildError("--change-threshold-ratio must be between 0 and 1")
        manifest = load_manifest(arguments.manifest)
        if arguments.refresh_provenance:
            if arguments.app:
                raise BuildError(
                    "--refresh-provenance covers the whole repository and cannot be "
                    "combined with --app"
                )
            document = refresh_provenance(manifest, root)
            write_provenance(document, root)
            print(
                json.dumps(
                    {
                        "mode": "refresh-provenance",
                        "apps": len(document["apps"]),
                        "manifest": PROVENANCE_FILENAME,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0
        names = select_apps(manifest, arguments.app)
        compilations = [compile_app(name, manifest["apps"][name], root) for name in names]
        # Render for every client even in check mode: an app that only fails
        # in a non-Surge renderer must fail the preflight, never the CI write.
        rendered = [rendered_outputs(compilation, manifest, root) for compilation in compilations]
        changes, violations = assess_changes(
            compilations,
            manifest,
            root,
            threshold_lines=arguments.change_threshold_lines,
            threshold_ratio=arguments.change_threshold_ratio,
        )
        provenance = None
        pruned: list[str] = []
        if arguments.write or arguments.verify_only:
            enabled_names = {
                name for name, app in manifest["apps"].items() if app.get("enabled") is True
            }
            provenance = build_provenance_manifest(
                compilations,
                manifest,
                rendered,
                root,
                preserve_unselected=set(names) != enabled_names,
            )
        if arguments.verify_only:
            assert provenance is not None
            errors = verify_rendered_outputs(rendered, provenance, root)
            if errors:
                raise BuildError("verify-only failed:\n" + "\n".join(errors))
        if arguments.write:
            if violations and not arguments.accept_large_change:
                raise BuildError(
                    "upstream change gate blocked the write; audit the diff, then rerun with "
                    "--accept-large-change if intentional:\n" + "\n".join(violations)
                )
            write_outputs(compilations, manifest, root, rendered)
            write_client_views(compilations, manifest, root)
            pruned = prune_stale_views(compilations, manifest, root)
            assert provenance is not None
            write_provenance(provenance, root)
        for item in compilations:
            for rewrite in item.rewritten_ip_rules:
                print(
                    f"warning: {item.app_name}: IP rule canonicalized ({rewrite}); "
                    "confirm the upstream range is what you intend",
                    file=sys.stderr,
                )
            for spec, hits in sorted(item.excluded_domains.items()):
                if hits == 0:
                    print(
                        f"warning: {item.app_name}: exclude {spec!r} matched no upstream rule; "
                        "confirm the upstream still carries it or drop the exclude",
                        file=sys.stderr,
                    )
        report = {
            "mode": "write" if arguments.write else "verify" if arguments.verify_only else "check",
            "pruned_views": pruned,
            "change_gate": {
                "threshold_lines": arguments.change_threshold_lines,
                "threshold_ratio": arguments.change_threshold_ratio,
                "accepted": bool(arguments.accept_large_change),
                "violations": violations,
                "apps": changes,
            },
            "apps": [
                {
                    "name": item.app_name,
                    "rules": len(item.rules),
                    "skipped_attributes": len(item.skipped_attributes),
                    "skipped_excluded": len(item.skipped_excluded),
                    "excluded_domains": dict(sorted(item.excluded_domains.items())),
                    "rewritten_ip_rules": item.rewritten_ip_rules,
                    "denied_includes": [name for name, _ in item.denied_includes],
                    "views": {name: len(rules) for name, rules in item.views},
                    "clients": {
                        key: {
                            "rules": len(item.rules) - len(dropped),
                            "dropped": dropped,
                        }
                        for key, (_path, _text, dropped) in client_outputs.items()
                    },
                }
                for item, client_outputs in zip(compilations, rendered)
            ],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except BuildError as error:
        print(f"build failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
