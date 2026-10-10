const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 };

function createLogger(level = 'info') {
    const threshold = LEVELS[level] ?? LEVELS.info;
    const write = (name, stream) => (...args) => {
        if (LEVELS[name] < threshold) return;
        stream(`${new Date().toISOString()} [${name.toUpperCase()}]`, ...args);
    };
    return Object.freeze({
        debug: write('debug', console.log),
        info: write('info', console.log),
        warn: write('warn', console.warn),
        error: write('error', console.error),
    });
}

module.exports = { createLogger };
