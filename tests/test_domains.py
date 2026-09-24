"""
Unit tests for Domain Analyzers and Automatic Detector.
"""

from pathlib import Path
import pytest

from guard.core.laya_engine import DomainType
from guard.domains.backend import BackendDomainAnalyzer
from guard.domains.detector import (
    detect_build_command,
    detect_repo_domain,
    extract_contracts_and_invariants,
    get_analyzer_by_domain,
)
from guard.domains.frontend import FrontendDomainAnalyzer
from guard.domains.infra import InfraDomainAnalyzer
from guard.domains.mobile import MobileDomainAnalyzer


def test_detect_frontend_repo(tmp_path):
    repo = tmp_path / "fe_app"
    repo.mkdir()
    (repo / "package.json").write_text('{"scripts": {"build": "vite build"}}', encoding="utf-8")
    (repo / "pnpm-lock.yaml").write_text("", encoding="utf-8")

    analyzer = detect_repo_domain(repo)
    assert isinstance(analyzer, FrontendDomainAnalyzer)
    cmd = detect_build_command(repo)
    assert cmd == "pnpm run build"


def test_detect_backend_go_repo(tmp_path):
    repo = tmp_path / "be_go"
    repo.mkdir()
    (repo / "go.mod").write_text("module myapp\ngo 1.22", encoding="utf-8")

    analyzer = detect_repo_domain(repo)
    assert isinstance(analyzer, BackendDomainAnalyzer)
    cmd = detect_build_command(repo)
    assert cmd == "go test ./... -v"


def test_detect_infra_repo(tmp_path):
    repo = tmp_path / "infra_iac"
    repo.mkdir()
    (repo / "docker-compose.yml").write_text("version: '3.8'\nservices:\n  app:\n    image: nginx\n", encoding="utf-8")

    analyzer = detect_repo_domain(repo)
    assert isinstance(analyzer, InfraDomainAnalyzer)
    cmd = detect_build_command(repo)
    assert cmd == "docker compose config"


def test_detect_mobile_flutter_repo(tmp_path):
    repo = tmp_path / "mb_flutter"
    repo.mkdir()
    (repo / "pubspec.yaml").write_text("name: flutter_app\ndependencies:\n  flutter:\n    sdk: flutter\n", encoding="utf-8")

    analyzer = detect_repo_domain(repo)
    assert isinstance(analyzer, MobileDomainAnalyzer)
    cmd = detect_build_command(repo)
    assert cmd == "flutter analyze"


def test_extract_fe_contracts(tmp_path):
    repo = tmp_path / "fe_extract"
    repo.mkdir()
    component = repo / "Modal.tsx"
    component.write_text("""
    export function Modal({ isOpen, onClose }) {
      const [isLoading, setIsLoading] = useState(false);
      return (
        <div className="backdrop sm:p-4" onClick={onClose}>
          <button disabled={isLoading}>Submit</button>
        </div>
      );
    }
    """, encoding="utf-8")

    analyzer = FrontendDomainAnalyzer()
    contracts = analyzer.extract_baseline_contracts(repo, ["Modal.tsx"])

    names = [c.name for c in contracts]
    categories = [c.category for c in contracts]
    assert any("loading_state" in n for n in names)
    assert any("disabled_behavior" in n for n in names)
    assert any("dismiss_interaction" in n for n in names)
    assert "UX_RESPONSIVE" in categories


def test_extract_contracts_and_invariants_bridge(tmp_path):
    repo = tmp_path / "be_extract"
    repo.mkdir()
    api_file = repo / "routes.py"
    api_file.write_text("""
    @router.post("/api/v1/orders")
    def create_order(user: Depends(get_current_user)):
        pass
    """, encoding="utf-8")

    contracts, invariants = extract_contracts_and_invariants(
        repo_path=repo,
        prompt="Add discount code to order api",
        domain=DomainType.BACKEND,
        files=["routes.py"],
    )

    assert len(invariants) >= 3
    assert any("BE-INV-01" == inv.id for inv in invariants)
    assert any("POST_/api/v1/orders" in c.name for c in contracts)
