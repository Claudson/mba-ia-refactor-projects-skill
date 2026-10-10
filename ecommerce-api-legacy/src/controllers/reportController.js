function createReportController({ reportService }) {
    return Object.freeze({
        financialReport: () => reportService.financialReport(),
    });
}

module.exports = { createReportController };
