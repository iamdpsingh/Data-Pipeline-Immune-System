from scripts.generate_synthetic_orders import generate_orders

def test_generate_orders():
    orders = generate_orders(10)
    assert len(orders) == 10
    assert "order_id" in orders[0]
