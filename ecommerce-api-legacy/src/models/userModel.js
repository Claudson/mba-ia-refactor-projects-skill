function createUserModel(db) {
    return Object.freeze({
        findByEmail: (email) => db.get('SELECT id FROM users WHERE email = ?', [email]),

        async create({ name, email, passwordHash }) {
            const { lastID } = await db.run('INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
                [name, email, passwordHash]);
            return lastID;
        },

        // Matrículas e pagamentos do usuário saem junto (FK ON DELETE CASCADE).
        deleteById: (id) => db.transaction(() => db.run('DELETE FROM users WHERE id = ?', [id])),
    });
}

module.exports = { createUserModel };
