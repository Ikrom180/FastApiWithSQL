import psycopg2

conn = psycopg2.connect("host=localhost dbname=postgres user=postgres password=1234 port=5432")
cur = conn.cursor()

#DO DB STUFF
cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INT PRIMARY KEY,
        name VARCHAR(255),
        age INT,
        gender CHAR               
);
""")

cur.execute("""INSERT INTO users (id, name, age, gender) VALUES  
             (1, 'Mike', 30, 'M'),
             (2, 'Flura', 35, 'F'),
             (3, 'Zina', 40, 'F'),
             (4, 'Michael', 45, 'M'),
             (5, 'Mure', 55, 'M');
""")

cur.execute("""Select * from users t where t.name = 'Mure'; """)
print(cur.fetchone())

cur.execute("""Select * from users t where t.age < 50; """)

# print(cur.fetchall())

for row in cur.fetchall():
        print(row)

sql = cur.mogrify("""select * from users t where starts_with(name, %s) AND age < %s;""", ('Z',50))

print(sql)
cur.execute(sql)

print(cur.fetchone())


conn.commit()

cur.close()
conn.close()