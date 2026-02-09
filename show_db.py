import sqlite3

conn = sqlite3.connect('data.db')
cur = conn.cursor()

print('\n=== CUSTOMERS TABLE ===')
print('ID | Name | Email')
print('-' * 50)
for row in cur.execute('SELECT * FROM customers'):
    print(f"{row[0]} | {row[1]} | {row[2]}")

print('\n=== PRODUCTS TABLE ===')
print('ID | Name | Category | Price | Stock')
print('-' * 60)
for row in cur.execute('SELECT * FROM products'):
    print(f"{row[0]} | {row[1]} | {row[2]} | ${row[3]} | {row[4]}")

print('\n=== ORDERS TABLE ===')
print('ID | Customer ID | Product | Amount')
print('-' * 50)
for row in cur.execute('SELECT * FROM orders'):
    print(f"{row[0]} | {row[1]} | {row[2]} | ${row[3]}")

conn.close()
print('\nDatabase located at: data.db')
