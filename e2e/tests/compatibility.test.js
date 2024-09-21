const { spawn } = require('child_process');
const { remote } = require('webdriverio');
const fs = require('fs');
const path = require('path');

let browser;

describe('Basic test', () => {
    it('should pass', () => {
        expect(true).toBe(true);
    });
});

describe('PeerJS Compatibility Test', () => {
    let pyProcess;

    beforeAll(async () => {
        browser = await remote({
            capabilities: {
                browserName: 'chrome',
                'goog:chromeOptions': {
                    args: ['--headless', '--disable-gpu']
                }
            }
        });

        await browser.url('http://localhost:8000/index.html');
        // Ensure jQuery is loaded
        await browser.execute(() => {
            return new Promise((resolve) => {
                if (window.jQuery) {
                    resolve();
                } else {
                    const script = document.createElement('script');
                    script.src = 'https://code.jquery.com/jquery-3.6.0.min.js';
                    script.onload = () => {
                        window.$ = window.jQuery;
                        resolve();
                    };
                    document.head.appendChild(script);
                }
            });
        });

        const jQueryLoaded = await browser.execute(() => {
            return typeof jQuery !== 'undefined';
        });
        console.log('jQuery loaded:', jQueryLoaded);
    
        if (!jQueryLoaded) {
            throw new Error('jQuery failed to load');
        }
    
        // Start Python client
        const clientPath = path.join(__dirname, '..', '..', 'py-client', 'client.py');
        pyProcess = spawn('python', [clientPath]);
        
        pyProcess.stdout.on('data', (data) => {
            console.log(`Python client: ${data}`);
        });

        // Wait for Python client to initialize
        await new Promise(resolve => setTimeout(resolve, 10000));
    });

    it('should establish connection and exchange messages', async () => {
        const status = await browser.$('#status');
        await status.waitForExist({ timeout: 10000 });
    
        console.log('Status before connecting:', await status.getText());
    
        const connectBtn = await browser.$('#connect');
        await connectBtn.click();
    
        console.log('Status after clicking connect:', await status.getText());
    
        // Increase timeout and add more logging
        await status.waitUntil(async function () {
            const text = await this.getText();
            console.log('Current status:', text);
            return text.includes('Connected to Python peer');
        }, { 
            timeout: 30000,
            timeoutMsg: 'Expected status to include "Connected to Python peer"'
        });

        const sendMsgBtn = await $('#sendMessage');
        await sendMsgBtn.click();

        await status.waitUntil(async function () {
            const text = await this.getText();
            return text.includes('Message received from Python peer');
        }, { timeout: 20000 });
    });

    it('should initiate and complete a voice call', async () => {
        const callBtn = await $('#call');
        await callBtn.click();

        const status = await $('#status');
        await status.waitUntil(async function () {
            const text = await this.getText();
            return text.includes('Voice call completed');
        }, { timeout: 20000 });

        // Check if the received audio file exists on the Python side
        const audioFileExists = fs.existsSync(path.join(__dirname, '..', 'py-client', 'received_audio.wav'));
        expect(audioFileExists).toBe(true);
    });

    afterAll(async () => {  // Add 'async' here
        // Stop Python client
        if (pyProcess) {
            pyProcess.kill();
        }
        if (browser) {
            await browser.deleteSession();
        }
    });
});