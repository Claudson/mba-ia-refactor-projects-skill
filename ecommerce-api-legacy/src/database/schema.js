const SCHEMA = `
    PRAGMA foreign_keys = ON;
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, name TEXT, email TEXT, pass TEXT
    );
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY, title TEXT, price REAL, active INTEGER
    );
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        course_id INTEGER REFERENCES courses(id)
    );
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY,
        enrollment_id INTEGER REFERENCES enrollments(id) ON DELETE CASCADE,
        amount REAL,
        status TEXT
    );
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY, action TEXT, created_at DATETIME
    );
`;

const SEED_USER = { name: 'Leonan', email: 'leonan@fullcycle.com.br', password: '123' };

async function initSchema(db, { hashPassword }) {
    await db.exec(SCHEMA);

    const { total } = await db.get('SELECT COUNT(*) AS total FROM courses');
    if (total > 0) return;

    await db.transaction(async () => {
        await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [SEED_USER.name, SEED_USER.email, hashPassword(SEED_USER.password)]);
        await db.run("INSERT INTO courses (title, price, active) VALUES ('Clean Architecture', 997.00, 1), ('Docker', 497.00, 1)");
        await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
        await db.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (1, 997.00, 'PAID')");
    });
}

module.exports = { initSchema };
