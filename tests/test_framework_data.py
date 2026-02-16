"""T6.x — Framework JSON data validation tests.

Validates that framework JSON files have correct structure,
required fields, valid priorities, and consistent mappings.
"""

import json
import os
import re
import pytest

ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets", "frameworks"
)


def load_framework(filename):
    """Load a framework JSON file from assets/frameworks/."""
    path = os.path.join(ASSETS_DIR, filename)
    with open(path) as f:
        return json.load(f)


class TestSOC2Structure:
    """T6.1 — SOC 2 JSON structure validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("soc2.json")

    def test_top_level_keys(self):
        """T6.1a — Required top-level keys exist."""
        required = {"$schema", "id", "name", "version", "description", "domains"}
        assert required.issubset(set(self.data.keys())), \
            f"Missing keys: {required - set(self.data.keys())}"

    def test_has_domains(self):
        """T6.1b — At least one domain exists."""
        assert len(self.data["domains"]) > 0

    def test_domain_structure(self):
        """T6.1c — Each domain has required fields."""
        for domain in self.data["domains"]:
            assert "id" in domain, f"Domain missing 'id'"
            assert "name" in domain, f"Domain missing 'name'"
            assert "controls" in domain, f"Domain missing 'controls'"
            assert isinstance(domain["controls"], list)


class TestSOC2Controls:
    """T6.2 — SOC 2 control validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("soc2.json")
        self.all_controls = []
        for domain in self.data["domains"]:
            self.all_controls.extend(domain["controls"])

    def test_control_count(self):
        """T6.2a — Expected number of controls loaded."""
        assert len(self.all_controls) >= 40, \
            f"Expected >=40 controls, got {len(self.all_controls)}"

    def test_control_required_fields(self):
        """T6.2b — Every control has required fields."""
        required = {"id", "title", "description", "category", "priority"}
        for ctrl in self.all_controls:
            missing = required - set(ctrl.keys())
            assert not missing, \
                f"Control {ctrl.get('id', '?')} missing fields: {missing}"

    def test_control_ids_unique(self):
        """T6.2c — No duplicate control IDs."""
        ids = [c["id"] for c in self.all_controls]
        duplicates = [x for x in ids if ids.count(x) > 1]
        assert not duplicates, f"Duplicate control IDs: {set(duplicates)}"

    def test_control_id_format(self):
        """T6.2d — Control IDs follow expected pattern (e.g., CC1.1, A1.1)."""
        pattern = re.compile(r"^[A-Z]{1,3}\d+\.\d+$")
        for ctrl in self.all_controls:
            assert pattern.match(ctrl["id"]), \
                f"Control ID '{ctrl['id']}' does not match pattern XX9.9"

    def test_priorities_valid(self):
        """T6.2e — All priorities are 1-5."""
        for ctrl in self.all_controls:
            p = ctrl["priority"]
            assert isinstance(p, int) and 1 <= p <= 5, \
                f"Control {ctrl['id']} has invalid priority: {p}"

    def test_categories_not_empty(self):
        """T6.2f — No empty category strings."""
        for ctrl in self.all_controls:
            assert ctrl["category"].strip(), \
                f"Control {ctrl['id']} has empty category"

    def test_descriptions_not_empty(self):
        """T6.2g — No empty description strings."""
        for ctrl in self.all_controls:
            assert ctrl["description"].strip(), \
                f"Control {ctrl['id']} has empty description"


class TestSOC2Evidence:
    """T6.3 — SOC 2 typical evidence validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("soc2.json")
        self.all_controls = []
        for domain in self.data["domains"]:
            self.all_controls.extend(domain["controls"])

    def test_evidence_field_exists(self):
        """T6.3a — Every control has typical_evidence field."""
        for ctrl in self.all_controls:
            assert "typical_evidence" in ctrl, \
                f"Control {ctrl['id']} missing typical_evidence"

    def test_evidence_is_list(self):
        """T6.3b — typical_evidence is always a list."""
        for ctrl in self.all_controls:
            assert isinstance(ctrl["typical_evidence"], list), \
                f"Control {ctrl['id']} typical_evidence is not a list"

    def test_evidence_not_empty(self):
        """T6.3c — Each control has at least one evidence item."""
        for ctrl in self.all_controls:
            assert len(ctrl["typical_evidence"]) >= 1, \
                f"Control {ctrl['id']} has no typical evidence"

    def test_evidence_strings_not_blank(self):
        """T6.3d — No blank evidence strings."""
        for ctrl in self.all_controls:
            for ev in ctrl["typical_evidence"]:
                assert isinstance(ev, str) and ev.strip(), \
                    f"Control {ctrl['id']} has blank evidence entry"


class TestSOC2Mappings:
    """T6.4 — SOC 2 cross-framework mapping validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("soc2.json")
        self.all_controls = []
        for domain in self.data["domains"]:
            self.all_controls.extend(domain["controls"])

    def test_mappings_field_exists(self):
        """T6.4a — Every control has mappings field."""
        for ctrl in self.all_controls:
            assert "mappings" in ctrl, \
                f"Control {ctrl['id']} missing mappings"

    def test_mappings_is_dict(self):
        """T6.4b — Mappings is always a dict."""
        for ctrl in self.all_controls:
            assert isinstance(ctrl["mappings"], dict), \
                f"Control {ctrl['id']} mappings is not a dict"

    def test_mapping_values_are_lists(self):
        """T6.4c — Each mapping target is a list of strings."""
        for ctrl in self.all_controls:
            for target, refs in ctrl["mappings"].items():
                assert isinstance(refs, list), \
                    f"Control {ctrl['id']} mapping '{target}' is not a list"
                for ref in refs:
                    assert isinstance(ref, str) and ref.strip(), \
                        f"Control {ctrl['id']} has blank mapping ref in '{target}'"

    def test_known_mapping_targets(self):
        """T6.4d — Mappings reference known frameworks."""
        known_targets = {"iso27001", "nist-csf", "hipaa", "pci-dss", "gdpr"}
        for ctrl in self.all_controls:
            for target in ctrl["mappings"].keys():
                assert target in known_targets, \
                    f"Control {ctrl['id']} maps to unknown framework: {target}"

    def test_iso27001_mapping_format(self):
        """T6.4e — ISO 27001 mappings follow A.x.x.x pattern."""
        pattern = re.compile(r"^A\.\d+\.\d+\.\d+$")
        for ctrl in self.all_controls:
            for ref in ctrl["mappings"].get("iso27001", []):
                assert pattern.match(ref), \
                    f"Control {ctrl['id']} has invalid ISO mapping: {ref}"

    def test_nist_csf_mapping_format(self):
        """T6.4f — NIST CSF mappings follow XX.YY-N pattern."""
        pattern = re.compile(r"^[A-Z]{2}\.[A-Z]{2}-\d+$")
        for ctrl in self.all_controls:
            for ref in ctrl["mappings"].get("nist-csf", []):
                assert pattern.match(ref), \
                    f"Control {ctrl['id']} has invalid NIST CSF mapping: {ref}"


class TestSOC2DomainCoverage:
    """T6.5 — Domain coverage validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("soc2.json")

    def test_expected_domains(self):
        """T6.5a — All expected SOC 2 domains present."""
        domain_ids = {d["id"] for d in self.data["domains"]}
        expected = {"CC", "A", "C", "PI"}
        assert expected.issubset(domain_ids), \
            f"Missing domains: {expected - domain_ids}"

    def test_common_criteria_largest(self):
        """T6.5b — CC domain has the most controls."""
        domains = {d["id"]: len(d["controls"]) for d in self.data["domains"]}
        cc_count = domains.get("CC", 0)
        for did, count in domains.items():
            if did != "CC":
                assert cc_count > count, \
                    f"CC ({cc_count}) should have more controls than {did} ({count})"

    def test_control_ids_match_domain(self):
        """T6.5c — Control IDs start with their domain prefix."""
        for domain in self.data["domains"]:
            did = domain["id"]
            for ctrl in domain["controls"]:
                assert ctrl["id"].startswith(did), \
                    f"Control {ctrl['id']} doesn't start with domain '{did}'"

    def test_p5_controls_in_critical_areas(self):
        """T6.5d — P5 controls exist in access and security domains."""
        p5_ids = []
        for domain in self.data["domains"]:
            for ctrl in domain["controls"]:
                if ctrl["priority"] == 5:
                    p5_ids.append(ctrl["id"])
        cc6_p5 = [x for x in p5_ids if x.startswith("CC6")]
        cc7_p5 = [x for x in p5_ids if x.startswith("CC7")]
        assert len(cc6_p5) >= 1, "Expected P5 controls in CC6 (access controls)"
        assert len(cc7_p5) >= 1, "Expected P5 controls in CC7 (operations)"


class TestRiskMatrix:
    """T6.6 — Risk matrix JSON validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "risk_matrix.json"
        )
        with open(path) as f:
            self.data = json.load(f)

    def test_has_levels(self):
        """T6.6a — Risk matrix has risk levels defined."""
        assert "levels" in self.data or "matrix" in self.data or "risk_levels" in self.data, \
            "Risk matrix missing expected top-level structure"

    def test_is_valid_json(self):
        """T6.6b — Risk matrix is parseable (implicitly tested by fixture)."""
        assert self.data is not None
