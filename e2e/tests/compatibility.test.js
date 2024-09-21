const { spawn } = require('child_process');
const { remote } = require('webdriverio');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

let browser;

function checkPythonLogs() {
    return new Promise((resolve, reject) => {
        exec('grep "Python client:" compatibility.test.log', (error, stdout, stderr) => {
            if (error) {
                console.error(`Error checking Python logs: ${error}`);
                reject(error);
            }
            console.log('Python client logs:', stdout);
            resolve(stdout);
        });
    });
}

describe('Basic test', () => {
    it('should pass', () => {
        expect(true).toBe(true);
    });
});

describe('PeerJS Compatibility Test', () => {
    let pyProcess;

    let logInterval;

    async function logBrowserConsole() {
        const logs = await browser.getLogs('browser');
        logs.forEach(log => {
            console.log(`[Browser] ${new Date(log.timestamp).toISOString()} - ${log.message}`);
        });
    }

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
        const clientPath = path.join(__dirname, '..', 'py-client', 'client.py');
        console.log(`Attempting to start Python client at: ${clientPath}`);

        pyProcess = spawn('python', [clientPath]);

        pyProcess.stdout.on('data', (data) => {
            console.log(`Python client stdout: ${data}`);
        });

        pyProcess.stderr.on('data', (data) => {
            console.error(`Python client stderr: ${data}`);
        });

        pyProcess.on('error', (error) => {
            console.error(`Error starting Python client: ${error.message}`);
        });

        pyProcess.on('close', (code) => {
            console.log(`Python client process exited with code ${code}`);
        });


        // Wait for Python client to initialize
        await new Promise(resolve => setTimeout(resolve, 10000));

        // Check if Python process is still running
        if (pyProcess.exitCode !== null) {
            throw new Error(`Python client exited prematurely with code ${pyProcess.exitCode}`);
        }

        logInterval = setInterval(logBrowserConsole, 1000);
    });
    
    async function getBrowserLogs() {
        const logs = await browser.getLogs('browser');
        console.log('Browser console logs:');
        logs.forEach(log => console.log(`[${log.level}] ${log.message}`));
        return logs;
    }

    it('should establish connection and exchange JSON messages', async () => {
        console.log('==========should establish connection and exchange JSON message=================');
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
            timeout: 30000, // Increase timeout to 30 seconds
            timeoutMsg: 'Expected status to include "Connected to Python peer"'
        });
    
        const sendMsgBtn = await browser.$('#sendMessage');
        await sendMsgBtn.click();
        console.log('==========sendMsgBtn')
    
        await status.waitUntil(async function () {
            const text = await this.getText();
            console.log('Current status after sending message:', text);
            return text.includes('Echo: Hello from JavaScript!');
        }, { 
            timeout: 30000,
            timeoutMsg: 'Expected to receive message from Python peer'
        });
        console.log('==========should establish connection and exchange JSON message:Browser logs =================');
        await logBrowserConsole();
        console.log('==========should establish connection and exchange JSON message: Done=================');
    });

    it('should initiate and complete a voice call', async () => {
        console.log('==========should initiate and complete a voice call=================');
        const callBtn = await browser.$('#call');
        await callBtn.click();
        console.log('==========click call button')
    
        const status = await browser.$('#status');
        await status.waitUntil(async function () {
            const text = await this.getText();
            console.log('test2: Current status:', text);  // Add this line for more detailed logging
            return text.includes('Voice call completed');
        }, { 
            timeout: 60000,  // Increase timeout to 60 seconds
            timeoutMsg: 'Expected voice call to complete within 60 seconds'
        });
    
        // Check if the received audio file exists on the Python side
        const audioFileExists = fs.existsSync(path.join(__dirname, '..', 'py-client', 'received_audio.wav'));
        expect(audioFileExists).toBe(true);
    
        const jsAudioReceived = await browser.execute(() => {
            return document.getElementById('remoteAudio').src !== '';
        });
        expect(jsAudioReceived).toBe(true);
        console.log('==========should establish connection and exchange JSON message:Browser logs =================');
        await logBrowserConsole();
        console.log('==========should initiate and complete a voice call: Done=================');
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