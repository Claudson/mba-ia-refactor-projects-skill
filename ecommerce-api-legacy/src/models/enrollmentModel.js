function createEnrollmentModel(db) {
    return Object.freeze({
        async create(userId, courseId) {
            const { lastID } = await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
                [userId, courseId]);
            return lastID;
        },
    });
}

module.exports = { createEnrollmentModel };
