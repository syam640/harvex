"""Tests for disease severity logic."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.ml.disease_knowledge import determine_severity


class TestDetermineSeverity:
    def test_healthy_high_confidence_returns_healthy(self):
        result = determine_severity("Tomato___healthy", 0.9967)
        assert result == "Healthy", f"Expected 'Healthy', got '{result}'"

    def test_healthy_medium_confidence_returns_healthy(self):
        result = determine_severity("Tomato___healthy", 0.65)
        assert result == "Healthy", f"Expected 'Healthy', got '{result}'"

    def test_healthy_low_confidence_returns_healthy(self):
        result = determine_severity("Tomato___healthy", 0.3)
        assert result == "Healthy", f"Expected 'Healthy', got '{result}'"

    def test_bacterial_spot_high_confidence(self):
        result = determine_severity("Tomato___Bacterial_spot", 0.92)
        assert result == "High", f"Expected 'High', got '{result}'"

    def test_bacterial_spot_medium_confidence(self):
        result = determine_severity("Tomato___Bacterial_spot", 0.7)
        assert result == "Medium", f"Expected 'Medium', got '{result}'"

    def test_bacterial_spot_low_confidence(self):
        result = determine_severity("Tomato___Bacterial_spot", 0.45)
        assert result == "Low", f"Expected 'Low', got '{result}'"

    def test_late_blight_high_confidence(self):
        result = determine_severity("Tomato___Late_blight", 0.95)
        assert result == "High", f"Expected 'High' (Late Blight is high-severity), got '{result}'"

    def test_late_blight_medium_confidence(self):
        result = determine_severity("Tomato___Late_blight", 0.65)
        assert result == "High", f"Expected 'High' (Late Blight base=High), got '{result}'"

    def test_late_blight_low_confidence(self):
        result = determine_severity("Tomato___Late_blight", 0.3)
        assert result == "Low", f"Expected 'Low' (below threshold), got '{result}'"

    def test_early_blight_high_confidence(self):
        result = determine_severity("Tomato___Early_blight", 0.88)
        assert result == "High", f"Expected 'High', got '{result}'"

    def test_mosaic_virus_medium_confidence(self):
        result = determine_severity("Tomato___Tomato_mosaic_virus", 0.72)
        assert result == "Medium", f"Expected 'Medium', got '{result}'"

    def test_unknown_class_returns_unknown(self):
        result = determine_severity("Unknown Disease", 0.9)
        assert result == "Unknown", f"Expected 'Unknown', got '{result}'"

    def test_empty_class_returns_unknown(self):
        result = determine_severity("", 0.9)
        assert result == "Unknown", f"Expected 'Unknown', got '{result}'"

    def test_none_class_returns_unknown(self):
        result = determine_severity(None, 0.9)
        assert result == "Unknown", f"Expected 'Unknown', got '{result}'"

    def test_negative_confidence_returns_unknown(self):
        result = determine_severity("Tomato___Bacterial_spot", -0.1)
        assert result == "Unknown", f"Expected 'Unknown' (negative confidence), got '{result}'"

    def test_confidence_above_one(self):
        result = determine_severity("Tomato___Bacterial_spot", 1.5)
        assert result == "Unknown", f"Expected 'Unknown' (confidence > 1), got '{result}'"

    def test_nan_confidence_returns_unknown(self):
        result = determine_severity("Tomato___Bacterial_spot", float('nan'))
        assert result == "Unknown", f"Expected 'Unknown' (NaN confidence), got '{result}'"

    def test_none_confidence_returns_unknown(self):
        result = determine_severity("Tomato___Bacterial_spot", None)
        assert result == "Unknown", f"Expected 'Unknown', got '{result}'"

    def test_confidence_boundary_08(self):
        result = determine_severity("Tomato___Bacterial_spot", 0.8)
        assert result == "High", f"Expected 'High' at boundary 0.8, got '{result}'"

    def test_confidence_boundary_06(self):
        result = determine_severity("Tomato___Bacterial_spot", 0.6)
        assert result == "Medium", f"Expected 'Medium' at boundary 0.6, got '{result}'"

    def test_confidence_below_threshold(self):
        result = determine_severity("Tomato___Bacterial_spot", 0.3)
        assert result == "Low", f"Expected 'Low' below threshold, got '{result}'"

    def test_string_confidence_returns_unknown(self):
        result = determine_severity("Tomato___Bacterial_spot", "high")
        assert result == "Unknown", f"Expected 'Unknown', got '{result}'"

    def test_leaf_mold_low_severity(self):
        result = determine_severity("Tomato___Leaf_Mold", 0.7)
        assert result == "Low", f"Expected 'Low' (Leaf Mold base=Low), got '{result}'"

    def test_leaf_mild_high_confidence(self):
        result = determine_severity("Tomato___Leaf_Mold", 0.9)
        assert result == "Medium", f"Expected 'Medium' (Leaf Mold high conf), got '{result}'"


if __name__ == "__main__":
    test = TestDetermineSeverity()
    methods = [m for m in dir(test) if m.startswith('test_')]
    passed = 0
    failed = 0
    for method_name in sorted(methods):
        method = getattr(test, method_name)
        try:
            method()
            print(f"  PASS: {method_name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {method_name} - {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
