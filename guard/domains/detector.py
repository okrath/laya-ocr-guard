"""
Domain Detector & Dispatcher.
Auto-detects whether a repository is FE, BE, Infra, or Mobile,
and delegates contract extraction, build checks, and invariants.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from guard.core.laya_engine import DomainType
from guard.core.session import DomainContract, LockedInvariant
from guard.domains.backend import BackendDomainAnalyzer
from guard.domains.base import BaseDomainAnalyzer
from guard.domains.frontend import FrontendDomainAnalyzer
from guard.domains.infra import InfraDomainAnalyzer
from guard.domains.mobile import MobileDomainAnalyzer

ALL_ANALYZERS: List[BaseDomainAnalyzer] = [
    MobileDomainAnalyzer(),    # Check mobile first (contains specific platform markers)
    InfraDomainAnalyzer(),     # Check infra
    FrontendDomainAnalyzer(),  # Check web frontend
    BackendDomainAnalyzer(),   # Check backend
]


def get_analyzer_by_domain(domain: DomainType) -> BaseDomainAnalyzer:
    if domain == DomainType.FRONTEND:
        return FrontendDomainAnalyzer()
    elif domain == DomainType.BACKEND:
        return BackendDomainAnalyzer()
    elif domain == DomainType.INFRA:
        return InfraDomainAnalyzer()
    elif domain == DomainType.MOBILE:
        return MobileDomainAnalyzer()
    return BackendDomainAnalyzer()  # Default fallback


def detect_repo_domain(repo_path: Optional[Path] = None) -> BaseDomainAnalyzer:
    path = Path(repo_path or Path.cwd())
    for analyzer in ALL_ANALYZERS:
        if analyzer.detect(path):
            return analyzer
    return BackendDomainAnalyzer()


def detect_build_command(repo_path: Optional[Path] = None) -> Optional[str]:
    path = Path(repo_path or Path.cwd())
    # Try all analyzers in order
    for analyzer in ALL_ANALYZERS:
        if analyzer.detect(path):
            cmd = analyzer.get_default_build_command(path)
            if cmd:
                return cmd
    return None


def extract_contracts_and_invariants(
    repo_path: Path,
    prompt: str,
    domain: DomainType,
    files: List[str],
) -> Tuple[List[DomainContract], List[LockedInvariant]]:
    analyzer = get_analyzer_by_domain(domain)
    contracts = analyzer.extract_baseline_contracts(repo_path, files)
    invariants = analyzer.generate_recommended_invariants(prompt, files)
    return contracts, invariants
