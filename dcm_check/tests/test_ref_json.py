#!/usr/bin/env python

import pytest
import json

import dcm_check.dcm_check as dcm_check
from dcm_check.tests.utils import create_empty_dicom
from pydantic_core import PydanticUndefined
from typing import Literal

@pytest.fixture
def dicom_test_file(tmp_path):
    """Fixture to create a DICOM file used as test input."""
    dicom_path = tmp_path / "ref_dicom.dcm"
    ds = create_empty_dicom()

    ds.EchoTime = 3.0
    ds.RepetitionTime = 8.0
    ds.SeriesDescription = "T1-weighted"

    ds.save_as(dicom_path, enforce_file_format=True)
    return str(dicom_path)

@pytest.fixture
def json_ref_no_dcm(tmp_path_factory):
    """Fixture to create a JSON reference file for testing."""
    test_json = {
        "acquisitions": {
            "T1": {
                "fields": [
                    {"field": "EchoTime", "tolerance": 0.1, "value": 3.0},
                    {"field": "RepetitionTime", "value": 8.0},
                    {"field": "SeriesDescription", "value": "*T1*"}
                ]
            }
        }
    }
    
    json_path = tmp_path_factory.mktemp("data") / "json_ref_no_dcm.json"
    with open(json_path, 'w') as f:
        json.dump(test_json, f)
    
    return str(json_path)

@pytest.fixture
def json_ref_with_dcm(tmp_path_factory, dicom_test_file):
    """Fixture to create a JSON reference file for testing."""
    test_json = {
        "acquisitions": {
            "T1": {
                "ref": dicom_test_file,
                "fields": [
                    {"field": "EchoTime", "tolerance": 0.1},
                    {"field": "RepetitionTime"},
                    {"field": "SeriesDescription"}
                ]
            }
        }
    }
    
    json_path = tmp_path_factory.mktemp("data") / "json_ref_with_dcm.json"
    with open(json_path, 'w') as f:
        json.dump(test_json, f)
    
    return str(json_path)

def test_load_ref_json(json_ref_no_dcm):
    """Test that JSON configuration can be loaded and generates a reference model."""
    reference_model = dcm_check.load_ref_json(json_path=json_ref_no_dcm, scan_type="T1")

    # Verify that the model was created correctly with exact and pattern matching fields
    assert reference_model is not None
    assert "EchoTime" in reference_model.model_fields
    assert "RepetitionTime" in reference_model.model_fields
    assert "SeriesDescription" in reference_model.model_fields

    # Check EchoTime with tolerance
    assert reference_model.model_fields["EchoTime"].default == 3.0
    assert reference_model.model_fields["EchoTime"].metadata[1].ge == 2.9
    assert reference_model.model_fields["EchoTime"].metadata[1].le == 3.1

    # Check that RepetitionTime is required, with an exact match of 8.0
    assert reference_model.model_fields["RepetitionTime"].default is PydanticUndefined
    assert reference_model.model_fields["RepetitionTime"].annotation == Literal[8.0]

    # Check that pattern is correctly set on SeriesDescription using metadata
    assert reference_model.model_fields["SeriesDescription"].metadata[0].pattern == ".*T1.*"

def test_load_ref_json_with_dcm(json_ref_with_dcm):
    """Test that JSON configuration can be loaded with a reference DICOM file."""
    reference_model = dcm_check.load_ref_json(json_path=json_ref_with_dcm, scan_type="T1")

    # Verify that the model was created correctly with exact and pattern matching fields
    assert reference_model is not None
    assert "EchoTime" in reference_model.model_fields
    assert "RepetitionTime" in reference_model.model_fields
    assert "SeriesDescription" in reference_model.model_fields

    # Check EchoTime with tolerance
    assert reference_model.model_fields["EchoTime"].default == 3.0
    assert reference_model.model_fields["EchoTime"].metadata[1].ge == 2.9
    assert reference_model.model_fields["EchoTime"].metadata[1].le == 3.1

    # Check that RepetitionTime is required, with an exact match of 8.0
    assert reference_model.model_fields["RepetitionTime"].default is PydanticUndefined
    assert reference_model.model_fields["RepetitionTime"].annotation == Literal[8.0]

    # Test that pattern is correctly set on SeriesDescription using json_schema_extra
    assert reference_model.model_fields["SeriesDescription"].annotation == Literal['T1-weighted']

def test_load_ref_json_invalid_scan_type(json_ref_no_dcm):
    """Test that an invalid scan type raises an error."""
    with pytest.raises(ValueError):
        dcm_check.load_ref_json(json_path=json_ref_no_dcm, scan_type="T2")

def test_json_compliance_within_tolerance(json_ref_no_dcm, dicom_test_file):
    """Test compliance when values are within tolerance for JSON configuration."""
    t1_dicom_values = dcm_check.load_dicom(dicom_test_file)
    reference_model = dcm_check.load_ref_json(json_path=json_ref_no_dcm, scan_type="T1")

    # Adjust EchoTime within tolerance (original value is 3.0, tolerance 0.1)
    t1_dicom_values["EchoTime"] = 3.05
    compliance_summary = dcm_check.get_compliance_summary(reference_model, t1_dicom_values)

    assert dcm_check.is_compliant(reference_model, t1_dicom_values)
    assert len(compliance_summary) == 0

def test_json_compliance_within_tolerance_with_dcm(json_ref_with_dcm, dicom_test_file):
    """Test compliance when values are within tolerance for JSON configuration."""
    t1_dicom_values = dcm_check.load_dicom(dicom_test_file)
    reference_model = dcm_check.load_ref_json(json_path=json_ref_with_dcm, scan_type="T1")

    # Adjust EchoTime within tolerance (original value is 3.0, tolerance 0.1)
    t1_dicom_values["EchoTime"] = 3.05
    compliance_summary = dcm_check.get_compliance_summary(reference_model, t1_dicom_values)

    assert dcm_check.is_compliant(reference_model, t1_dicom_values)
    assert len(compliance_summary) == 0

def test_json_compliance_outside_tolerance(json_ref_no_dcm, dicom_test_file):
    """Test compliance when values exceed tolerance for JSON configuration."""
    t1_dicom_values = dcm_check.load_dicom(dicom_test_file)
    reference_model = dcm_check.load_ref_json(json_path=json_ref_no_dcm, scan_type="T1")

    # Adjust EchoTime beyond tolerance (original value is 3.0, tolerance 0.1)
    t1_dicom_values["EchoTime"] = 3.2
    compliance_summary = dcm_check.get_compliance_summary(reference_model, t1_dicom_values)
    assert len(compliance_summary) == 1
    assert compliance_summary[0]["Parameter"] == "EchoTime"
    assert compliance_summary[0]["Expected"] == "Input should be less than or equal to 3.1"
    assert compliance_summary[0]["Actual"] == 3.2
    assert not compliance_summary[0]["Pass"]

def test_json_compliance_outside_tolerance_with_dcm(json_ref_with_dcm, dicom_test_file):
    """Test compliance when values exceed tolerance for JSON configuration."""
    t1_dicom_values = dcm_check.load_dicom(dicom_test_file)
    reference_model = dcm_check.load_ref_json(json_path=json_ref_with_dcm, scan_type="T1")

    # Adjust EchoTime beyond tolerance (original value is 3.0, tolerance 0.1)
    t1_dicom_values["EchoTime"] = 3.2
    compliance_summary = dcm_check.get_compliance_summary(reference_model, t1_dicom_values)
    assert len(compliance_summary) == 1
    assert compliance_summary[0]["Parameter"] == "EchoTime"
    assert compliance_summary[0]["Expected"] == "Input should be less than or equal to 3.1"
    assert compliance_summary[0]["Actual"] == 3.2
    assert not compliance_summary[0]["Pass"]

def test_json_compliance_exact_match(json_ref_no_dcm, dicom_test_file):
    """Test compliance when exact match is required."""
    t1_dicom_values = dcm_check.load_dicom(dicom_test_file)
    reference_model = dcm_check.load_ref_json(json_path=json_ref_no_dcm, scan_type="T1")

    # Adjust RepetitionTime for exact match failure (original value is 8.0)
    t1_dicom_values["RepetitionTime"] = 9.0
    compliance_summary = dcm_check.get_compliance_summary(reference_model, t1_dicom_values)
    assert len(compliance_summary) == 1
    assert compliance_summary[0]["Parameter"] == "RepetitionTime"
    assert compliance_summary[0]["Expected"] == "8.0"
    assert compliance_summary[0]["Actual"] == 9.0
    assert not compliance_summary[0]["Pass"]

def test_json_compliance_exact_match_with_dcm(json_ref_with_dcm, dicom_test_file):
    """Test compliance when exact match is required."""
    t1_dicom_values = dcm_check.load_dicom(dicom_test_file)
    reference_model = dcm_check.load_ref_json(json_path=json_ref_with_dcm, scan_type="T1")

    # Adjust RepetitionTime for exact match failure (original value is 8.0)
    t1_dicom_values["RepetitionTime"] = 9.0
    compliance_summary = dcm_check.get_compliance_summary(reference_model, t1_dicom_values)
    assert len(compliance_summary) == 1
    assert compliance_summary[0]["Parameter"] == "RepetitionTime"
    assert compliance_summary[0]["Expected"] == "8.0"
    assert compliance_summary[0]["Actual"] == 9.0
    assert not compliance_summary[0]["Pass"]

def test_json_compliance_pattern_match(json_ref_no_dcm, dicom_test_file):
    """Test compliance with a pattern match for SeriesDescription."""
    t1_dicom_values = dcm_check.load_dicom(dicom_test_file)
    reference_model = dcm_check.load_ref_json(json_path=json_ref_no_dcm, scan_type="T1")

    # Change SeriesDescription to match pattern "*T1*"
    t1_dicom_values["SeriesDescription"] = "Another_T1_Sequence"
    compliance_summary = dcm_check.get_compliance_summary(reference_model, t1_dicom_values)
    assert len(compliance_summary) == 0  # Should pass pattern match

def test_json_compliance_pattern_match_fail(json_ref_no_dcm, dicom_test_file):
    """Test compliance failure when pattern match for SeriesDescription fails."""
    t1_dicom_values = dcm_check.load_dicom(dicom_test_file)
    reference_model = dcm_check.load_ref_json(json_path=json_ref_no_dcm, scan_type="T1")

    # Change SeriesDescription to something that does not match pattern "*T1*"
    t1_dicom_values["SeriesDescription"] = "Another_Sequence"
    compliance_summary = dcm_check.get_compliance_summary(reference_model, t1_dicom_values)
    assert len(compliance_summary) == 1
    assert compliance_summary[0]["Parameter"] == "SeriesDescription"
    assert compliance_summary[0]["Expected"] == "String should match pattern '.*T1.*'"
    assert compliance_summary[0]["Actual"] == "Another_Sequence"
    assert not compliance_summary[0]["Pass"]

if __name__ == "__main__":
    pytest.main(["-v", __file__])
