"""
Mobile (MB) Domain Analyzer.
Handles Flutter (Dart), React Native (TS/JS), iOS (Swift), Android (Kotlin/Java).
Extracts native permissions, lifecycle states, offline caching, safe area/notches.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from guard.core.session import DomainContract, LockedInvariant
from guard.domains.base import BaseDomainAnalyzer


class MobileDomainAnalyzer(BaseDomainAnalyzer):
    @property
    def name(self) -> str:
        return "Mobile App (Flutter / React Native / iOS / Android)"

    def detect(self, repo_path: Path) -> bool:
        mb_indicators = [
            "pubspec.yaml",
            "android/build.gradle",
            "ios/Podfile",
            "app.json",
            "AndroidManifest.xml",
            "Info.plist",
        ]
        return any((repo_path / ind).exists() for ind in mb_indicators)

    def get_default_build_command(self, repo_path: Path) -> Optional[str]:
        if (repo_path / "pubspec.yaml").exists():
            return "flutter analyze"
        if (repo_path / "android" / "build.gradle").exists():
            return "./gradlew test"
        if (repo_path / "package.json").exists() and (repo_path / "ios").exists():
            return "npm run lint"
        return None

    def extract_baseline_contracts(self, repo_path: Path, files: List[str]) -> List[DomainContract]:
        contracts: List[DomainContract] = []
        mb_files = [f for f in files if any(f.endswith(ext) or "/" in f for ext in [".dart", ".swift", ".kt", "AndroidManifest.xml", "Info.plist"])]

        for rel_path in mb_files[:5]:
            p = repo_path / rel_path
            if not p.is_file():
                continue
            try:
                code = p.read_text(encoding="utf-8", errors="ignore")[:4000]

                # Check for runtime permissions
                perms = re.findall(r"""(uses-permission|permission|NSCameraUsageDescription|NSLocationWhenInUseUsageDescription)""", code)
                if perms:
                    contracts.append(DomainContract(
                        category="NATIVE_PERMISSION",
                        name=f"{Path(rel_path).stem}_permissions",
                        description=f"Preserve explicit user permission requests before accessing hardware in {rel_path}",
                    ))

                # Check for SafeArea / Notch padding
                if re.search(r"\b(SafeArea|safeAreaInsets|useSafeAreaInsets)\b", code):
                    contracts.append(DomainContract(
                        category="UI_SAFE_AREA",
                        name=f"{Path(rel_path).stem}_safe_area",
                        description=f"Preserve SafeArea wrapping for notch & home indicator in {rel_path}",
                    ))

                # Check for Offline / Local caching
                if re.search(r"\b(shared_preferences|AsyncStorage|Hive|Isar|Room|CoreData|sqflite)\b", code):
                    contracts.append(DomainContract(
                        category="OFFLINE_STORAGE",
                        name=f"{Path(rel_path).stem}_offline_cache",
                        description=f"Preserve offline cache fallback when network disconnects in {rel_path}",
                    ))
            except Exception:
                pass

        return contracts

    def generate_recommended_invariants(self, prompt: str, files: List[str]) -> List[LockedInvariant]:
        return [
            LockedInvariant(
                id="MB-INV-01",
                description="Must wrap views in `SafeArea` to prevent UI overlap with notches, dynamic islands, or navigation bars.",
                rationale="Ensure ergonomics across all iOS & Android form factors.",
            ),
            LockedInvariant(
                id="MB-INV-02",
                description="Always verify runtime permission status before accessing hardware devices (Camera, GPS, Microphone).",
                rationale="Prevent application crashes when users deny permissions.",
            ),
            LockedInvariant(
                id="MB-INV-03",
                description="When network connection is lost, application must render cached state or a user-friendly offline view.",
                rationale="Protect mobile UX under unstable network conditions.",
            ),
        ]

    def generate_targeted_test_plan(self, files: List[str], diff_text: str) -> List[str]:
        return [
            "Test application on devices with camera notches (iPhone) and navigation bars (Android).",
            "Simulate Airplane Mode to verify app renders offline cached data without crashing.",
            "Test user permission denial to ensure graceful degradation prompts.",
        ]
