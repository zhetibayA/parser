from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

def get_average_price(brand, model, issued_at, year, month):
    conn = sqlite3.connect('kolesa.db')
    cur = conn.cursor()
    
    # Найти model_id
    cur.execute('''
        SELECT id FROM models WHERE brand = ? AND model = ?
    ''', (brand, model))
    model_result = cur.fetchone()
    if not model_result:
        conn.close()
        return None
    model_id = model_result[0]

    # Найти vehicle_id
    cur.execute('''
        SELECT id FROM vehicle WHERE model_id = ? AND issued_at = ?
    ''', (model_id, issued_at))
    vehicle_result = cur.fetchone()
    if not vehicle_result:
        conn.close()
        return None
    vehicle_id = vehicle_result[0]

    # Найти среднюю цену
    cur.execute('''
        SELECT AVG(avg_price)
        FROM price
        WHERE vehicle_id = ? 
        AND CAST(strftime('%Y', date) AS INTEGER) = ? 
        AND CAST(strftime('%m', date) AS INTEGER) = ?
    ''', (vehicle_id, year, month))
    price_result = cur.fetchone()
    conn.close()

    if price_result and price_result[0] is not None:
        return price_result[0]
    else:
        return None

@app.route('/get_average_price', methods=['GET'])
def get_average_price_route():
    brand = request.args.get('brand')
    model = request.args.get('model')
    issued_at = request.args.get('issued_at')
    year = request.args.get('year')
    month = request.args.get('month')
    if not (brand and model and issued_at and year and month):
        return jsonify({"error": "Missing parameters"}), 400
    try:
        issued_at = int(issued_at)
        year = int(year)
        month = int(month)
    except ValueError:
        return jsonify({"error": "issued_at, year and month must be integers"}), 400
    average_price = get_average_price(brand, model, issued_at, year, month)
    if average_price is not None:
        return jsonify({"average_price": average_price})
    else:
        return jsonify({"error": "No data found for the given parameters"}), 404

if __name__ == '__main__':
    app.run(debug=True)