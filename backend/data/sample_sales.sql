CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    department_id INTEGER,
    salary INTEGER,
    FOREIGN KEY(department_id) REFERENCES departments(id)
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER,
    amount INTEGER,
    date TEXT,
    FOREIGN KEY(employee_id) REFERENCES employees(id)
);

INSERT OR IGNORE INTO departments (id, name) VALUES (1, 'Sales'), (2, 'Engineering'), (3, 'HR');
INSERT OR IGNORE INTO employees (name, department_id, salary) VALUES ('Alice', 1, 60000), ('Bob', 1, 55000), ('Charlie', 2, 80000);
INSERT OR IGNORE INTO sales (employee_id, amount, date) VALUES (1, 5000, '2023-01-15'), (1, 6000, '2023-02-15'), (2, 4000, '2023-01-20');

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    location TEXT
);

INSERT OR IGNORE INTO customers (name, email, location) VALUES 
('John Doe', 'john@example.com', 'California'),
('Jane Smith', 'jane@example.com', 'New York'),
('Bob Johnson', 'bob@example.com', 'California'),
('Alice Brown', 'alice@example.com', 'Texas');
