const { PAYMENT_STATUS } = require('../models/paymentModel');

function createReportService({ courseModel }) {
    return Object.freeze({
        async financialReport() {
            const rows = await courseModel.findAllWithEnrollmentPayments();
            const byCourse = new Map();

            for (const row of rows) {
                if (!byCourse.has(row.course_id)) {
                    byCourse.set(row.course_id, { course: row.title, revenue: 0, students: [] });
                }
                if (row.enrollment_id === null) continue;

                const entry = byCourse.get(row.course_id);
                if (row.status === PAYMENT_STATUS.PAID) entry.revenue += row.amount;
                entry.students.push({
                    student: row.student_name ?? 'Unknown',
                    paid: row.amount ?? 0,
                });
            }
            return [...byCourse.values()];
        },
    });
}

module.exports = { createReportService };
