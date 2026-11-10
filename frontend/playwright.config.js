import { defineConfig } from '@playwright/test';

const port = Number(process.env.HB_TEST_PORT || 4176);
const baseURL = 'http://127.0.0.1:' + port;

export default defineConfig({
  testDir: './tests',
  use: { baseURL, channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome' },
  webServer: {
    command: 'npm run dev -- --port ' + port + ' --strictPort',
    url: baseURL,
  },
});

