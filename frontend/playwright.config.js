const { defineConfig } = require('@playwright/test');
const path = require('path');
module.exports = defineConfig({
    testDir: './e2e',
    globalSetup: './e2e/prepare.js',
    timeout: 60000,
    workers: 1,
    use: {
        baseURL: process.env.E2E_BASE_URL || 'http://127.0.0.1:3001',
        browserName: 'chromium',
        channel: 'msedge',
        headless: true,
        launchOptions: {
            args: [
                '--use-fake-device-for-media-stream',
                '--use-fake-ui-for-media-stream',
                '--use-file-for-fake-video-capture=' +
                    path.resolve(__dirname, '../data/browser-qa/fake-camera.y4m'),
            ],
        },
    },
    reporter: [['list'], ['json', { outputFile: '../artifacts/browser-report.json' }]],
});
