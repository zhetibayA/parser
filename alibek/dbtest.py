
import sqlite3

conn = sqlite3.connect('testcar.db')
cur = conn.cursor()
date = '2024-05'
date += "%"
cur.execute('''
    SELECT * FROM price WHERE date LIKE ?
''', (date,))
result = cur.fetchall()
print(f"Result: {result}")