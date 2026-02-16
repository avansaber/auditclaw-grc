"""T6.7–T6.12 — ISO 27001 framework JSON data validation tests.

Validates that iso27001.json has correct structure, required fields,
valid priorities, and consistent cross-framework mappings.
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


class TestISO27001Structure:
    """T6.7 — ISO 27001 JSON structure validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("iso27001.json")

    def test_top_level_keys(self):
        """T6.7a — Required top-level keys exist."""
        required = {"$schema", "id", "name", "version", "description", "domains"}
        assert required.issubset(set(self.data.keys())), \
            f"Missing keys: {required - set(self.data.keys())}"

    def test_id_is_iso27001(self):
        """T6.7b — Framework ID is iso27001."""
        assert self.data["id"] == "iso27001"

    def test_has_14_domains(self):
        """T6.7c — Has all 14 Annex A domains (A.5-A.18)."""
        assert len(self.data["domains"]) == 14

    def test_domain_structure(self):
        """T6.7d — Each domain has required fields."""
        for domain in self.data["domains"]:
            assert "id" in domain
            assert "name" in domain
            assert "controls" in domain
            assert isinstance(domain["controls"], list)


class TestISO27001Controls:
    """T6.8 — ISO 27001 control validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("iso27001.json")
        self.all_controls = []
        for domain in self.data["domains"]:
            self.all_controls.extend(domain["controls"])

    def test_control_count(self):
        """T6.8a — ISO 27001 should have 114 controls."""
        assert len(self.all_controls) == 114, \
            f"Expected 114 controls, got {len(self.all_controls)}"

    def test_control_required_fields(self):
        """T6.8b — Every control has required fields."""
        required = {"id", "title", "description", "category", "priority"}
        for ctrl in self.all_controls:
            missing = required - set(ctrl.keys())
            assert not missing, \
                f"Control {ctrl.get('id', '?')} missing fields: {missing}"

    def test_control_ids_unique(self):
        """T6.8c — No duplicate control IDs."""
        ids = [c["id"] for c in self.all_controls]
        duplicates = [x for x in ids if ids.count(x) > 1]
        assert not duplicates, f"Duplicate control IDs: {set(duplicates)}"

    def test_control_id_format(self):
        """T6.8d — Control IDs follow A.x.x.x pattern."""
        pattern = re.compile(r"^A\d+\.\d+\.\d+$")
        for ctrl in self.all_controls:
            assert pattern.match(ctrl["id"]), \
                f"Control ID '{ctrl['id']}' does not match pattern A.x.x.x"

    def test_priorities_valid(self):
        """T6.8e — All priorities are 1-5."""
        for ctrl in self.all_controls:
            p = ctrl["priority"]
            assert isinstance(p, int) and 1 <= p <= 5, \
                f"Control {ctrl['id']} has invalid priority: {p}"

    def test_categories_not_empty(self):
        """T6.8f — No empty category strings."""
        for ctrl in self.all_controls:
            assert ctrl["category"].strip(), \
                f"Control {ctrl['id']} has empty category"

    def test_descriptions_not_empty(self):
        """T6.8g — No empty description strings."""
        for ctrl in self.all_controls:
            assert ctrl["description"].strip(), \
                f"Control {ctrl['id']} has empty description"


class TestISO27001Evidence:
    """T6.9 — ISO 27001 typical evidence validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("iso27001.json")
        self.all_controls = []
        for domain in self.data["domains"]:
            self.all_controls.extend(domain["controls"])

    def test_evidence_field_exists(self):
        """T6.9a — Every control has typical_evidence field."""
        for ctrl in self.all_controls:
            assert "typical_evidence" in ctrl, \
                f"Control {ctrl['id']} missing typical_evidence"

    def test_evidence_is_list(self):
        """T6.9b — typical_evidence is always a list."""
        for ctrl in self.all_controls:
            assert isinstance(ctrl["typical_evidence"], list), \
                f"Control {ctrl['id']} typical_evidence is not a list"

    def test_evidence_not_empty(self):
        """T6.9c — Each control has at least one evidence item."""
        for ctrl in self.all_controls:
            assert len(ctrl["typical_evidence"]) >= 1, \
                f"Control {ctrl['id']} has no typical evidence"


class TestISO27001Mappings:
    """T6.10 — ISO 27001 cross-framework mapping validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("iso27001.json")
        self.all_controls = []
        for domain in self.data["domains"]:
            self.all_controls.extend(domain["controls"])

    def test_mappings_field_exists(self):
        """T6.10a — Every control has mappings field."""
        for ctrl in self.all_controls:
            assert "mappings" in ctrl, \
                f"Control {ctrl['id']} missing mappings"

    def test_mappings_is_dict(self):
        """T6.10b — Mappings is always a dict."""
        for ctrl in self.all_controls:
            assert isinstance(ctrl["mappings"], dict), \
                f"Control {ctrl['id']} mappings is not a dict"

    def test_has_soc2_mappings(self):
        """T6.10c — Most controls map to SOC 2."""
        mapped = sum(1 for c in self.all_controls if "soc2" in c["mappings"])
        # At least 90% should map to SOC 2
        assert mapped >= len(self.all_controls) * 0.9, \
            f"Only {mapped}/{len(self.all_controls)} controls map to SOC 2"

    def test_soc2_mapping_format(self):
        """T6.10d — SOC 2 mappings follow CC/A/C/PI pattern."""
        pattern = re.compile(r"^(CC|A|C|PI)\d+\.\d+$")
        for ctrl in self.all_controls:
            for ref in ctrl["mappings"].get("soc2", []):
                assert pattern.match(ref), \
                    f"Control {ctrl['id']} has invalid SOC 2 mapping: {ref}"

    def test_nist_csf_mapping_format(self):
        """T6.10e — NIST CSF mappings follow XX.YY-N pattern."""
        pattern = re.compile(r"^[A-Z]{2}\.[A-Z]{2}-\d+$")
        for ctrl in self.all_controls:
            for ref in ctrl["mappings"].get("nist-csf", []):
                assert pattern.match(ref), \
                    f"Control {ctrl['id']} has invalid NIST CSF mapping: {ref}"


class TestISO27001DomainCoverage:
    """T6.11 — ISO 27001 domain coverage validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("iso27001.json")

    def test_expected_domains(self):
        """T6.11a — All 14 Annex A domains present."""
        domain_ids = {d["id"] for d in self.data["domains"]}
        expected = {"A5", "A6", "A7", "A8", "A9", "A10", "A11", "A12",
                    "A13", "A14", "A15", "A16", "A17", "A18"}
        assert expected == domain_ids, \
            f"Domain mismatch. Missing: {expected - domain_ids}, Extra: {domain_ids - expected}"

    def test_domain_control_counts(self):
        """T6.11b — Each domain has expected number of controls."""
        expected_counts = {
            "A5": 2, "A6": 7, "A7": 6, "A8": 10, "A9": 14,
            "A10": 2, "A11": 15, "A12": 14, "A13": 7, "A14": 13,
            "A15": 5, "A16": 7, "A17": 4, "A18": 8
        }
        for domain in self.data["domains"]:
            did = domain["id"]
            actual = len(domain["controls"])
            assert actual == expected_counts[did], \
                f"Domain {did}: expected {expected_counts[did]} controls, got {actual}"

    def test_access_control_has_most_p5(self):
        """T6.11c — A9 (Access Control) has the most P5 controls."""
        p5_by_domain = {}
        for domain in self.data["domains"]:
            count = sum(1 for c in domain["controls"] if c["priority"] == 5)
            p5_by_domain[domain["id"]] = count
        a9_p5 = p5_by_domain.get("A9", 0)
        assert a9_p5 >= 5, f"A9 should have >=5 P5 controls, got {a9_p5}"
        for did, count in p5_by_domain.items():
            if did != "A9":
                assert a9_p5 >= count, \
                    f"A9 ({a9_p5} P5) should have most P5, but {did} has {count}"

    def test_control_ids_match_domain(self):
        """T6.11d — Control IDs start with domain prefix."""
        for domain in self.data["domains"]:
            did = domain["id"]
            # A5 -> controls start with A5., A12 -> A12., etc.
            prefix = did  # e.g., "A5", "A12"
            for ctrl in domain["controls"]:
                assert ctrl["id"].startswith(prefix), \
                    f"Control {ctrl['id']} doesn't start with '{prefix}'"


class TestISO27001Integration:
    """T6.12 — ISO 27001 integration with activation flow."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.data = load_framework("iso27001.json")

    def test_json_parseable(self):
        """T6.12a — JSON is valid and parseable."""
        assert self.data is not None

    def test_has_schema_field(self):
        """T6.12b — Has $schema for validation."""
        assert "$schema" in self.data
        assert self.data["$schema"] == "framework-definition-v1"

    def test_total_control_count_matches_sum(self):
        """T6.12c — Total controls equals sum of domain controls."""
        total = sum(len(d["controls"]) for d in self.data["domains"])
        assert total == 114, f"Expected 114 total, got {total}"
