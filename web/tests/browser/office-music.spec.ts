import { expect, test } from "@playwright/test";

test("office music: opt-in playback, volume, loop, fullscreen and reload", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/office?mode=demo&scenario=team");
  const audio = page.locator(".office-music audio");
  const volume = page.getByRole("slider", { name: "Music volume", exact: true });
  await expect(page.getByRole("button", { name: "Play music", exact: true })).toBeVisible();
  expect(await audio.evaluate((el: HTMLAudioElement) => el.paused)).toBe(true);
  await expect(volume).toHaveValue("25");
  await page.getByRole("button", { name: "Play music", exact: true }).click();
  await expect(page.getByRole("button", { name: "Pause music", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect.poll(() => audio.evaluate((el: HTMLAudioElement) => el.currentTime)).toBeGreaterThan(.1);
  expect(await audio.evaluate((el: HTMLAudioElement) => el.currentSrc)).toContain("/office-audio/carefree.mp3");
  expect(await audio.evaluate((el: HTMLAudioElement) => el.duration)).toBeGreaterThan(200);
  await expect(page.getByRole("link", { name: "Carefree · Kevin MacLeod", exact: true })).toBeVisible();
  await volume.focus();
  await page.keyboard.press("Home");
  await page.keyboard.press("ArrowRight");
  await expect.poll(() => audio.evaluate((el: HTMLAudioElement) => el.volume)).toBe(.01);
  await page.getByRole("button", { name: "Fullscreen", exact: true }).click();
  await expect(page.getByRole("button", { name: "Pause music", exact: true })).toBeVisible();
  expect(await audio.evaluate((el: HTMLAudioElement) => el.paused)).toBe(false);
  await page.getByRole("button", { name: "Exit fullscreen", exact: true }).click();
  // Exercise a real decoded-file loop boundary, rather than only checking the loop flag.
  await audio.evaluate((el: HTMLAudioElement) => { el.currentTime = el.duration - .2; });
  await expect.poll(() => audio.evaluate((el: HTMLAudioElement) => el.currentTime)).toBeLessThan(5);
  await page.getByRole("button", { name: "Pause music", exact: true }).click();
  expect(await audio.evaluate((el: HTMLAudioElement) => el.paused)).toBe(true);
  await page.reload();
  await expect(page.getByRole("button", { name: "Play music", exact: true })).toBeVisible();
  await expect(volume).toHaveValue("1");
  expect(await audio.evaluate((el: HTMLAudioElement) => el.paused)).toBe(true);
  expect(errors).toEqual([]);
});
