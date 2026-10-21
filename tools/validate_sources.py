"""Validate the YAML configuration and run each provider's health check over the declared sources.

Works without MongoDB: sources are built from configs/users/* exactly as the registry would store them.

Usage (from the repo root):
    uv run python -m tools.validate_sources              # also opens Medium in Chrome and calls the GitHub API
    uv run python -m tools.validate_sources --offline    # configs + local checks only
    uv run python -m tools.validate_sources --user omar  # one user's sources

Writes data/manifests/source_health.json. Exits 1 if configuration is invalid or a provider is unhealthy.
"""

import argparse
import json
import sys
from collections import defaultdict

from llm_engineering.crawl_config.yaml_loader import YamlLoader
from llm_engineering.exceptions import ConfigError
from llm_engineering.raw_data.sources.base.context import CrawlContext
from llm_engineering.raw_data.sources.registry import PROVIDERS, create_extractor
from llm_engineering.registry.models.source import Source
from llm_engineering.settings.paths import SOURCE_HEALTH_FILE


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="skip network/browser checks")
    parser.add_argument("--user", help="only this user's sources")
    args = parser.parse_args()

    config = YamlLoader()
    try:
        declarations = [config.get_user(args.user)] if args.user else list(config.users.values())
        providers = config.providers
    except ConfigError as exc:
        print(f"✗ invalid configuration:\n{exc}")
        return 1
    print(f"topics: {len(config.topics)} | users: {[d.user.id for d in declarations]}")

    # same dedup as the registry: one Source per canonical key, however many users declare it
    sources: dict[str, Source] = {}
    for declaration in declarations:
        for spec in declaration.sources:
            source = Source.from_spec(spec, declaration.user.id)
            sources.setdefault(source.id, source)
    by_provider: dict[str, list[Source]] = defaultdict(list)
    for source in sources.values():
        by_provider[source.provider].append(source)

    context = CrawlContext(run_id="validate", topics=config.topics, users={d.user.id: d.user for d in declarations})
    report: dict[str, dict] = {}
    unhealthy = 0
    for name in PROVIDERS:
        provider_sources = by_provider.get(name, [])
        print(f"\n== {name}: {len(provider_sources)} source(s)")
        if not provider_sources:
            continue
        health = create_extractor(name, providers[name], provider_sources, context).health_check(offline=args.offline)
        report[name] = health.model_dump()
        print(f"  {'✓' if health.ok else '✗'} {health.summary}")
        unhealthy += not health.ok

    SOURCE_HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_HEALTH_FILE.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"\nreport written to {SOURCE_HEALTH_FILE}")
    return 1 if unhealthy else 0


if __name__ == "__main__":
    sys.exit(main())
