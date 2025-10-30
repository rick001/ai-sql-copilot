import pytest
from pydantic import ValidationError
from app.schemas import ModelEnvelope


def test_valid_envelope_min():
    data = {"answer": "Hi"}
    m = ModelEnvelope.model_validate(data)
    assert m.answer == "Hi"


def test_valid_envelope_full():
    data = {
        "answer": "Summary",
        "sql": "SELECT * FROM retail_sales",
        "viz": {
            "type": "line",
            "x": "date",
            "y": ["net_sales"],
            "groupBy": ["region"],
            "aggregation": "sum",
            "explanations": ["foo"]
        }
    }
    m = ModelEnvelope.model_validate(data)
    assert m.viz is not None


def test_invalid_viz_type():
    data = {
        "answer": "Summary",
        "viz": {"type": "pie", "x": "date", "y": ["net_sales"]}
    }
    with pytest.raises(Exception):
        ModelEnvelope.model_validate(data)

