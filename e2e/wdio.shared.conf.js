const path = require("path");

const testFiles = [
    path.resolve(__dirname, 'tests/**/*.js'),
    path.resolve(__dirname, 'tests/**/*.ts')
];

console.log('Looking for test files in:', testFiles);

exports.config = {
    injectGlobals: false,
    specs: testFiles,
    exclude: [
        './node_modules/**/*.spec.ts',
        './node_modules/**/*.spec.js'
	],
    maxInstances: 5,
    logLevel: "trace",
    outputDir: path.resolve(__dirname, "logs"),
    baseUrl: "http://localhost:3000",
    waitforTimeout: 10000,
    connectionRetryTimeout: 90000,
    connectionRetryCount: 3,
    framework: "jasmine",
    specFileRetries: 1,
    specFileRetriesDeferred: true,
    reporters: ["spec"],
    jasmineOpts: {
        defaultTimeoutInterval: 60000,
    },
};