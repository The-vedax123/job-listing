import mysql.connector

# Connect to MySQL server (without specifying a database yet)
try:
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='' # Add your root password here if you have one
    )
    cursor = conn.cursor()

    # Read the SQL file
    with open('database.sql', 'r') as f:
        sql_script = f.read()

    # Execute the statements in the SQL file
    # split by ';' and filter out empty strings
    statements = [s.strip() for s in sql_script.split(';') if s.strip()]
    
    for statement in statements:
        cursor.execute(statement)

    print("Database initialized successfully!")

except mysql.connector.Error as err:
    print(f"Error connecting to MySQL: {err}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals() and conn.is_connected():
        conn.close()
