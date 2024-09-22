const { config: sharedConfig } = require("./wdio.shared.conf.js");

exports.config = {
    ...sharedConfig,
    runner: 'local',
    capabilities: [{
        browserName: 'chrome',
        'goog:chromeOptions': {
            args: ['--headless', '--disable-gpu']
        }
    }],
    // Add any other local-specific configurations here
};