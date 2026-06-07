import { expect, test } from "@playwright/test";

test.skip(process.env.RUN_REAL !== "1", "set RUN_REAL=1 to run deployed browser journey");
test.skip(!process.env.DEPLOYED_WEB_URL && !process.env.WEB_URL, "missing deployed web URL");
test.skip(!process.env.VTN_PASSWORD, "missing VTN_PASSWORD");

test.use({
  baseURL: process.env.DEPLOYED_WEB_URL ?? process.env.WEB_URL,
});

test("deployed browser login to export journey", async ({ page }) => {
  const username = process.env.VTN_USERNAME ?? "local";
  const password = process.env.VTN_PASSWORD ?? "";
  const videoUrl =
    process.env.VTN_REAL_VIDEO_URL ?? "https://www.youtube.com/watch?v=jNQXAC9IVRw";

  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/submit$/, { timeout: 30_000 });
  await page.getByLabel("Video URL").fill(videoUrl);
  await page.getByRole("button", { name: "Create note" }).click();

  await expect(page).toHaveURL(/\/edit\/[^/]+$/, { timeout: 30_000 });
  await expect(page.getByText("Review ready")).toBeVisible({ timeout: 900_000 });
  await expect(page.getByRole("button", { name: "Split" })).toBeEnabled();

  const jobId = page.url().split("/").pop();
  expect(jobId).toBeTruthy();

  await page.goto(`/review/${jobId}`);
  await expect(page.getByLabel("Markdown editor")).toBeVisible({ timeout: 30_000 });

  await page.goto(`/export/${jobId}`);
  await expect(page.getByText(/sections/)).toBeVisible({ timeout: 30_000 });
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download ZIP" }).click();
  expect((await download).suggestedFilename()).toMatch(/\.zip$/);
});
