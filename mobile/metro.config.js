// Learn more https://docs.expo.dev/guides/monorepos/#modify-the-metro-config
const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// This machine runs consistently low on free RAM. Metro's default worker
// pool (one process per CPU core) transforms files in parallel, and each
// worker holds its own copy of buffers/ASTs in memory — under memory
// pressure the postMessage handoff between workers and the main process
// fails with "DataCloneError: ... out of memory" partway through bundling.
// Capping workers to 1 trades bundling speed for a bundle that actually
// completes instead of crashing near the end.
config.maxWorkers = 1;

module.exports = config;
