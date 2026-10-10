function createAuditLogModel(db) {
    return Object.freeze({
        log: (action) => db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [action]),
    });
}

module.exports = { createAuditLogModel };
