const original = { ...process.env };
afterEach(() => {
    process.env = { ...original };
    jest.resetModules();
});

test('cloud frontend accepts same-origin API routing without an unconfigured-address error', () => {
    process.env.NODE_ENV = 'production';
    process.env.REACT_APP_API_BASE_URL = 'same-origin';
    jest.isolateModules(() => {
        const api = require('./api');
        expect(api.http.defaults.baseURL).toBe('');
        expect(api.configurationError).toBe('');
    });
});

test('an absent production API setting still reports a configuration error', () => {
    process.env.NODE_ENV = 'production';
    delete process.env.REACT_APP_API_BASE_URL;
    jest.isolateModules(() => {
        expect(require('./api').configurationError).toContain('not been configured');
    });
});
