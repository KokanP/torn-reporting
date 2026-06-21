import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
  use: {
    baseURL: 'http://localhost:3001',
    trace: 'on-first-retry',
  },
  webServer: [
    {
      command: 'python -m uvicorn main:app --host 127.0.0.1 --port 8081',
      cwd: './api',
      port: 8081,
      reuseExistingServer: true,
      timeout: 10000,
    },
    {
      command: 'node index.js',
      cwd: './server',
      port: 8080,
      reuseExistingServer: true,
      timeout: 10000,
    },
    {
      command: 'npm run dev',
      cwd: './web',
      port: 3001,
      reuseExistingServer: true,
      timeout: 10000,
    }
  ]
});
