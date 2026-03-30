import csv
import sqlite3

def convert_csv_to_db(csv_file, db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            name TEXT,
            math INTEGER,
            science INTEGER,
            english INTEGER,
            total_marks INTEGER
        )
    ''')
    
    # Read CSV and insert
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute('''
                INSERT INTO students (name, math, science, english, total_marks)
                VALUES (?, ?, ?, ?, ?)
            ''', (row['name'], row['math'], row['science'], row['english'], row['total_marks']))
    
    conn.commit()
    conn.close()
    print(f"Database created at {db_file}")

if __name__ == '__main__':
    convert_csv_to_db('students.csv', 'students.db')
