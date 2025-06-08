


@app.post("/payfast/ipn")
def payfast_ipn_handler(request: Request):
    payload = await request.form()
    # Validate signature here...
    payment_status = payload.get("payment_status")
    subscription_id = payload.get("subscription_id")
    # Update invoices, cancel subscriptions, mark company as paid etc.

