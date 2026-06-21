import { test, expect } from '@playwright/test';

test.describe('User Identity & Profile Limits (14-Day Cooldown)', () => {
    test.beforeEach(async ({ page }) => {
        page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
        page.on('pageerror', err => console.log('BROWSER ERROR:', err.message));
    });

    test('should force onboarding, allow nickname change, and enforce 14-day limit on immediate subsequent change', async ({ page }) => {
        // 1. A new user logs in and is intercepted by Onboarding
        await page.goto('/login');
        
        // Perform login action (e.g., clicking mock Google login)
        await page.click('button:has-text("Login with Google")');
        
        // Assert interception by Onboarding page because nickname is missing
        await expect(page).toHaveURL(/.*\/onboarding/);
        await expect(page.locator('h1')).toContainText('Complete Your Profile');
        
        // Try to submit without a nickname
        await page.click('button:has-text("Save Profile")');
        await expect(page.locator('.error-message')).toContainText('Nickname is required');
        
        // Enter a nickname and save
        const initialNickname = `user_${Date.now()}`;
        await page.fill('input[name="nickname"]', initialNickname);
        await page.click('button:has-text("Save Profile")');
        
        // Assert successful onboarding redirect to home/dashboard
        await expect(page).toHaveURL('/');
        
        // 2. Navigate to Profile Settings
        await page.goto('/settings/profile');
        
        // Verify UI uses the nickname, real name is ignored in display
        await expect(page.locator('.profile-display-name')).toContainText(initialNickname);
        await expect(page.locator('.profile-real-name')).toBeHidden(); // Dead data, ignored by UI
        
        // 3. Change nickname (allowed once)
        const updatedNickname1 = `${initialNickname}_new`;
        await page.fill('input[name="nickname"]', updatedNickname1);
        await page.click('button:has-text("Update Profile")');
        
        // Success notification / state update
        await expect(page.locator('.success-message')).toBeVisible();
        await expect(page.locator('.profile-display-name')).toContainText(updatedNickname1);
        
        // 4. IMMEDIATELY try to change nickname again
        const updatedNickname2 = `${initialNickname}_again`;
        await page.fill('input[name="nickname"]', updatedNickname2);
        await page.click('button:has-text("Update Profile")');
        
        // Assert that the app blocks submission inline (HTTP 429 response handled by UI)
        const errorContainer = page.locator('.error-message-inline');
        await expect(errorContainer).toBeVisible();
        await expect(errorContainer).toContainText(/must wait|cooldown|days remaining/i);
        
        // Assert nickname field still reflects the previous allowed nickname, not the rejected one
        await expect(page.locator('.profile-display-name')).toContainText(updatedNickname1);
    });
});
