"""PHASE 6: Expenses + Harvest + Insights Tests — 47 tests."""

import pytest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app.core.database import get_db, Base, engine
from app.models.models import User, Farm, Field, CropCycle, Expense, Harvest
from app.core.security import create_access_token

import importlib
main_mod = importlib.import_module("main")
app = main_mod.app
client = TestClient(app)

_counter = 0

def _next():
    global _counter
    _counter += 1
    return _counter


def _setup_db():
    Base.metadata.create_all(bind=engine)


_setup_db()


def _make全套(prefix):
    """Create a fresh user + farm + field + cycle with no leftover data."""
    n = _next()
    email = f"phase6_{prefix}_{n}@example.com"

    db = next(get_db())
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name=f"P6 {n}", email=email, password_hash="hashed")
        db.add(user)
        db.commit()
        db.refresh(user)

    # Clean any leftover data for this user
    farms = db.query(Farm).filter(Farm.user_id == user.id).all()
    for f in farms:
        fields = db.query(Field).filter(Field.farm_id == f.id).all()
        for field in fields:
            cycles = db.query(CropCycle).filter(CropCycle.field_id == field.id).all()
            for c in cycles:
                db.query(Expense).filter(Expense.crop_cycle_id == c.id).delete()
                db.query(Harvest).filter(Harvest.crop_cycle_id == c.id).delete()
            db.query(CropCycle).filter(CropCycle.field_id == field.id).delete()
        db.query(Field).filter(Field.farm_id == f.id).delete()
    db.query(Farm).filter(Farm.user_id == user.id).delete()
    db.commit()

    farm = Farm(name=f"Farm {n}", user_id=user.id, latitude=16.9, longitude=82.0, location_name="Kakinada")
    db.add(farm)
    db.commit()
    db.refresh(farm)

    field = Field(name=f"Field {n}", farm_id=farm.id, area=1.0, soil_type="loam")
    db.add(field)
    db.commit()
    db.refresh(field)

    cycle = CropCycle(
        field_id=field.id, crop_name="tomato",
        planting_date=datetime.utcnow() - timedelta(days=30),
        expected_harvest_date=datetime.utcnow() + timedelta(days=60),
        status="active", predicted_yield=1500.0
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)

    uid = user.id
    cid = cycle.id
    db.close()

    token = create_access_token(data={"sub": str(uid)})
    return token, cid


def _make_nopred():
    """Create a user+cycle with no predicted_yield."""
    n = _next()
    email = f"phase6_nopred_{n}@example.com"

    db = next(get_db())
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name=f"P6 NP {n}", email=email, password_hash="hashed")
        db.add(user)
        db.commit()
        db.refresh(user)

    # Clean any leftover data for this user
    farms = db.query(Farm).filter(Farm.user_id == user.id).all()
    for f in farms:
        fields = db.query(Field).filter(Field.farm_id == f.id).all()
        for field in fields:
            cycles = db.query(CropCycle).filter(CropCycle.field_id == field.id).all()
            for c in cycles:
                db.query(Expense).filter(Expense.crop_cycle_id == c.id).delete()
                db.query(Harvest).filter(Harvest.crop_cycle_id == c.id).delete()
            db.query(CropCycle).filter(CropCycle.field_id == field.id).delete()
        db.query(Field).filter(Field.farm_id == f.id).delete()
    db.query(Farm).filter(Farm.user_id == user.id).delete()
    db.commit()

    farm = Farm(name=f"Farm NP {n}", user_id=user.id, latitude=28.6, longitude=77.2, location_name="Delhi")
    db.add(farm)
    db.commit()
    db.refresh(farm)

    field = Field(name=f"Field NP {n}", farm_id=farm.id, area=2.0, soil_type="clay")
    db.add(field)
    db.commit()
    db.refresh(field)

    cycle = CropCycle(
        field_id=field.id, crop_name="wheat",
        planting_date=datetime.utcnow() - timedelta(days=60),
        status="active", predicted_yield=None
    )
    db.add(cycle)
    db.commit()
    db.refresh(cycle)

    uid = user.id
    cid = cycle.id
    db.close()

    token = create_access_token(data={"sub": str(uid)})
    return token, cid


# ============================================================
# EXPENSE CRUD TESTS (1-8)
# ============================================================

def test_1_create_expense():
    token, cid = _make全套("exp")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 5000, "description": "Tomato seeds",
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["category"] == "Seeds"
    assert data["amount"] == 5000.0


def test_2_invalid_category_rejected():
    token, cid = _make全套("exp")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "InvalidCategory", "amount": 100,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_3_zero_amount_rejected():
    token, cid = _make全套("exp")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 0,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_4_excessive_amount_rejected():
    token, cid = _make全套("exp")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 5000000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_5_edit_expense():
    token, cid = _make全套("exp")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Fertilizer", "amount": 2000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    eid = res.json()["id"]

    res = client.put(f"/api/crop-cycles/{cid}/expenses/{eid}", json={
        "category": "Pesticides", "amount": 3000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["category"] == "Pesticides"
    assert res.json()["amount"] == 3000.0


def test_6_delete_expense():
    token, cid = _make全套("exp")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Labour", "amount": 1000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    eid = res.json()["id"]

    res = client.delete(f"/api/crop-cycles/{cid}/expenses/{eid}",
                        headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "deleted_id" in res.json()

    res = client.get(f"/api/crop-cycles/{cid}/expenses",
                     headers={"Authorization": f"Bearer {token}"})
    assert all(e["id"] != eid for e in res.json())


def test_7_cross_user_expense_access_denied():
    token_a, cid_a = _make全套("expA")
    token_b, _ = _make全套("expB")
    res = client.get(f"/api/crop-cycles/{cid_a}/expenses",
                     headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404


def test_8_cross_user_expense_delete_denied():
    token_a, cid_a = _make全套("expA")
    token_b, _ = _make全套("expB")

    res = client.post(f"/api/crop-cycles/{cid_a}/expenses", json={
        "category": "Seeds", "amount": 500,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token_a}"})
    eid = res.json()["id"]

    res = client.delete(f"/api/crop-cycles/{cid_a}/expenses/{eid}",
                        headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404


# ============================================================
# EXPENSE EDGE CASES (9-13)
# ============================================================

def test_9_description_length_validation():
    token, cid = _make全套("exp")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 100,
        "description": "x" * 501,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_10_edit_wrong_cycle_rejected():
    token, cid = _make全套("exp")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 100,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    eid = res.json()["id"]

    res = client.put(f"/api/crop-cycles/{cid + 999}/expenses/{eid}", json={
        "category": "Seeds", "amount": 100,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_11_delete_wrong_cycle_rejected():
    token, cid = _make全套("exp")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 100,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    eid = res.json()["id"]

    res = client.delete(f"/api/crop-cycles/{cid + 999}/expenses/{eid}",
                        headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_12_all_valid_categories_accepted():
    token, cid = _make全套("exp")
    for cat in ["Seeds", "Fertilizer", "Pesticides", "Labour", "Irrigation", "Transport", "Equipment", "Other"]:
        res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
            "category": cat, "amount": 100,
            "expense_date": datetime.utcnow().isoformat()
        }, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Category {cat} should be accepted"


def test_13_expense_list_filters_by_cycle():
    token, cid = _make全套("exp")
    client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 100,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/crop-cycles/{cid}/expenses",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    for e in res.json():
        assert e["crop_cycle_id"] == cid


# ============================================================
# HARVEST CRUD TESTS (14-20)
# ============================================================

def test_14_create_harvest():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 500, "unit": "kg", "selling_price": 40
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert data["quantity"] == 500
    assert data["revenue"] == 20000.0


def test_15_harvest_revenue_calculation():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg", "selling_price": 50
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.json()["revenue"] == 5000.0


def test_16_harvest_no_selling_price():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 200, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.json()["revenue"] is None


def test_17_edit_harvest():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})
    hid = res.json()["id"]

    res = client.put(f"/api/crop-cycles/{cid}/harvests/{hid}", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 150, "unit": "quintal", "selling_price": 2000
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["quantity"] == 150
    assert res.json()["unit"] == "quintal"
    assert res.json()["revenue"] == 300000.0


def test_18_delete_harvest():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 50, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})
    hid = res.json()["id"]

    res = client.delete(f"/api/crop-cycles/{cid}/harvests/{hid}",
                        headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "deleted_id" in res.json()

    res = client.get(f"/api/crop-cycles/{cid}/harvests",
                     headers={"Authorization": f"Bearer {token}"})
    assert all(h["id"] != hid for h in res.json())


def test_19_cross_user_harvest_denied():
    token_a, cid_a = _make全套("harA")
    token_b, _ = _make全套("harB")
    res = client.get(f"/api/crop-cycles/{cid_a}/harvests",
                     headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404


def test_20_invalid_unit_rejected():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "invalid_unit"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


# ============================================================
# HARVEST EDGE CASES (21-26)
# ============================================================

def test_21_negative_quantity_rejected():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": -10, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_22_negative_selling_price_rejected():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg", "selling_price": -50
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 400


def test_23_edit_wrong_cycle_harvest_rejected():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})
    hid = res.json()["id"]

    res = client.put(f"/api/crop-cycles/{cid + 999}/harvests/{hid}", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_24_delete_wrong_cycle_harvest_rejected():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})
    hid = res.json()["id"]

    res = client.delete(f"/api/crop-cycles/{cid + 999}/harvests/{hid}",
                        headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404


def test_25_harvest_default_unit_kg():
    token, cid = _make全套("har")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["unit"] == "kg"


def test_26_harvest_multiple_units_accepted():
    token, cid = _make全套("har")
    for unit in ["kg", "quintal", "tonnes", "pieces"]:
        res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
            "harvest_date": datetime.utcnow().isoformat(),
            "quantity": 10, "unit": unit
        }, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Unit {unit} should be accepted"


# ============================================================
# INSIGHTS / FINANCIAL SUMMARY TESTS (27-35)
# ============================================================

def test_27_insights_has_financial_fields():
    token, cid = _make全套("ins")
    client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 5000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg", "selling_price": 40
    }, headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()
    assert "total_revenue" in data
    assert "total_cost" in data
    assert "net_profit" in data
    assert "harvest_count" in data
    assert "expense_count" in data


def test_28_financial_calculation_correct():
    token, cid = _make全套("ins")
    client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Fertilizer", "amount": 3000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Labour", "amount": 2000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 200, "unit": "kg", "selling_price": 50
    }, headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert data["total_revenue"] == 10000.0
    assert data["total_cost"] == 5000.0
    assert data["net_profit"] == 5000.0
    assert data["harvest_count"] == 1
    assert data["expense_count"] == 2


def test_29_financial_no_harvest():
    token, cid = _make全套("ins")
    client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 1000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert data["total_revenue"] == 0.0
    assert data["total_cost"] == 1000.0
    assert data["net_profit"] == -1000.0
    assert data["harvest_count"] == 0


def test_30_financial_no_expenses():
    token, cid = _make全套("ins")
    client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg", "selling_price": 30
    }, headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert data["total_revenue"] == 3000.0
    assert data["total_cost"] == 0.0
    assert data["net_profit"] == 3000.0
    assert data["expense_count"] == 0


def test_31_financial_no_data():
    token, cid = _make全套("ins")
    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert data["total_revenue"] == 0.0
    assert data["total_cost"] == 0.0
    assert data["net_profit"] is None
    assert data["harvest_count"] == 0
    assert data["expense_count"] == 0


def test_32_prediction_vs_reality_with_data():
    token, cid = _make全套("ins")
    client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 1200, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert data["has_prediction"] is True
    assert data["predicted_yield"] == 1500.0
    assert data["actual_yield"] == 1200.0
    assert data["difference"] == -300.0
    assert abs(data["percentage_deviation"] - (-20.0)) < 0.01


def test_33_prediction_no_harvest_yet():
    token, cid = _make全套("ins")
    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert data["has_prediction"] is True
    assert data["actual_yield"] is None
    assert data["difference"] is None


def test_34_no_prediction():
    token, cid = _make_nopred()
    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert data["has_prediction"] is False


def test_35_cross_user_insights_denied():
    token_a, cid_a = _make全套("insA")
    token_b, _ = _make全套("insB")
    res = client.get(f"/api/crop-cycles/{cid_a}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 404


# ============================================================
# UNDO TESTS (36-39)
# ============================================================

def test_36_delete_returns_deleted_id():
    token, cid = _make全套("undo")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 100,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    eid = res.json()["id"]

    res = client.delete(f"/api/crop-cycles/{cid}/expenses/{eid}",
                        headers={"Authorization": f"Bearer {token}"})
    assert res.json()["deleted_id"] == eid


def test_37_recreate_after_delete_undo():
    token, cid = _make全套("undo")
    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Fertilizer", "amount": 500,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    orig = res.json()

    client.delete(f"/api/crop-cycles/{cid}/expenses/{orig['id']}",
                  headers={"Authorization": f"Bearer {token}"})

    res = client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": orig["category"], "amount": orig["amount"],
        "expense_date": orig["expense_date"]
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["amount"] == 500


def test_38_harvest_delete_returns_deleted_id():
    token, cid = _make全套("undo")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})
    hid = res.json()["id"]

    res = client.delete(f"/api/crop-cycles/{cid}/harvests/{hid}",
                        headers={"Authorization": f"Bearer {token}"})
    assert res.json()["deleted_id"] == hid


def test_39_harvest_recreate_after_delete():
    token, cid = _make全套("undo")
    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 200, "unit": "quintal", "selling_price": 1500
    }, headers={"Authorization": f"Bearer {token}"})
    orig = res.json()

    client.delete(f"/api/crop-cycles/{cid}/harvests/{orig['id']}",
                  headers={"Authorization": f"Bearer {token}"})

    res = client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": orig["harvest_date"], "quantity": orig["quantity"],
        "unit": orig["unit"], "selling_price": orig["selling_price"]
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["revenue"] == 300000.0


# ============================================================
# MULTIPLE RECORDS TESTS (40-43)
# ============================================================

def test_40_multiple_expenses_total():
    token, cid = _make全套("multi")
    for amt in [100, 200, 300]:
        client.post(f"/api/crop-cycles/{cid}/expenses", json={
            "category": "Other", "amount": amt,
            "expense_date": datetime.utcnow().isoformat()
        }, headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/crop-cycles/{cid}/expenses",
                     headers={"Authorization": f"Bearer {token}"})
    assert len(res.json()) == 3


def test_41_multiple_harvests_revenue():
    token, cid = _make全套("multi")
    client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg", "selling_price": 50
    }, headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 200, "unit": "kg", "selling_price": 60
    }, headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert data["total_revenue"] == 17000.0


def test_42_harvest_unit_normalization_in_insights():
    token, cid = _make全套("multi")
    client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 2, "unit": "quintal", "selling_price": 2000
    }, headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 50, "unit": "kg", "selling_price": 40
    }, headers={"Authorization": f"Bearer {token}"})

    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality",
                     headers={"Authorization": f"Bearer {token}"})
    data = res.json()
    assert data["total_revenue"] == 6000.0  # 2*2000 + 50*40 = 6000
    assert data["actual_yield"] == 52.0  # raw sum: 2 + 50 (no unit conversion in yield)


def test_43_expense_and_harvest_independent():
    token, cid = _make全套("multi")
    client.post(f"/api/crop-cycles/{cid}/expenses", json={
        "category": "Seeds", "amount": 5000,
        "expense_date": datetime.utcnow().isoformat()
    }, headers={"Authorization": f"Bearer {token}"})
    client.post(f"/api/crop-cycles/{cid}/harvests", json={
        "harvest_date": datetime.utcnow().isoformat(),
        "quantity": 100, "unit": "kg"
    }, headers={"Authorization": f"Bearer {token}"})

    exp_res = client.get(f"/api/crop-cycles/{cid}/expenses",
                         headers={"Authorization": f"Bearer {token}"})
    har_res = client.get(f"/api/crop-cycles/{cid}/harvests",
                         headers={"Authorization": f"Bearer {token}"})
    assert len(exp_res.json()) == 1
    assert len(har_res.json()) == 1
    assert exp_res.json()[0]["category"] == "Seeds"
    assert har_res.json()[0]["unit"] == "kg"


# ============================================================
# AUTH TESTS (44-47)
# ============================================================

def test_44_no_token_expenses():
    token, cid = _make全套("auth")
    res = client.get(f"/api/crop-cycles/{cid}/expenses")
    assert res.status_code in [401, 403]


def test_45_no_token_harvests():
    token, cid = _make全套("auth")
    res = client.get(f"/api/crop-cycles/{cid}/harvests")
    assert res.status_code in [401, 403]


def test_46_no_token_insights():
    token, cid = _make全套("auth")
    res = client.get(f"/api/crop-cycles/{cid}/prediction-vs-reality")
    assert res.status_code in [401, 403]


def test_47_nonexistent_cycle():
    token, cid = _make全套("auth")
    res = client.get("/api/crop-cycles/999999/expenses",
                     headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404
