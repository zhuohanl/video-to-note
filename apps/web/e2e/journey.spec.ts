import { expect, test } from "@playwright/test";

const clip = {
  id: "clip-a",
  order_index: 0,
  start_sec: "0.000",
  end_sec: "5.000",
  title: "Intro",
  summary: "Original summary",
  scene_caption: "Original caption",
  scene_at_sec: "1.000",
  scene_url: "local://frames/a.png",
  scene_source: "auto",
  needs_regen: false,
  etag: '"clip-v1"',
};

const clips = {
  clips: [clip],
  collection_etag: '"clips-v1"',
};

const note = {
  markdown: "## 1. Intro\n\nOriginal summary",
  include_summary: true,
  include_transcript: false,
  is_polished: true,
  clips_dirty: false,
  etag: '"note-v1"',
};

test("login to submit to edit to review to export with mocked backend", async ({ page }) => {
  await page.route("**/login", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    await route.fulfill({
      headers: { "set-cookie": "vtn_session=signed; Path=/; SameSite=Lax" },
      json: {},
      status: 200,
    });
  });
  await page.route("**/jobs", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        json: {
          job_id: "job-1",
          cost_estimate: {
            usd: "0.1000",
            breakdown: { expected_clips: 1, llm_calls: 3, ocr_frames: 4 },
          },
        },
        status: 202,
      });
      return;
    }
    await route.continue();
  });
  await page.route("**/jobs/job-1/events**", async (route) => {
    await route.fulfill({
      body: [
        "id: 1\nevent: stage\ndata: {\"stage\":\"acquiring_media\"}\n\n",
        "id: 2\nevent: stage\ndata: {\"stage\":\"transcribe\"}\n\n",
        "id: 3\nevent: stage\ndata: {\"stage\":\"index visual\"}\n\n",
        "id: 4\nevent: stage\ndata: {\"stage\":\"segmenting\"}\n\n",
        "id: 5\nevent: clip.ready\ndata: {\"clip_id\":\"clip-a\",\"order_index\":0}\n\n",
        "id: 6\nevent: done\ndata: {}\n\n",
      ].join(""),
      contentType: "text/event-stream",
      status: 200,
    });
  });
  await page.route("**/jobs/job-1/clips", async (route) => {
    await route.fulfill({ json: clips });
  });
  await page.route("**/jobs/job-1/note", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({ json: note });
      return;
    }
    await route.fulfill({ json: { ...note, markdown: "## 1. Intro\n\nPolished" } });
  });
  await page.route("**/jobs/job-1/versions", async (route) => {
    await route.fulfill({ json: { versions: [] } });
  });
  await page.route("**/clips/clip-a", async (route) => {
    if (route.request().url().includes("ack=1")) {
      await route.fulfill({ json: { ...clip, summary: "Edited summary", etag: '"clip-v2"' } });
      return;
    }
    await route.fulfill({
      json: { error: { code: "needs_ack", message: "Needs acknowledgement" } },
      status: 409,
    });
  });
  await page.route("**/jobs/job-1/export", async (route) => {
    await route.fulfill({ json: { download_url: "/download/job-1.zip" } });
  });
  await page.route("**/download/job-1.zip", async (route) => {
    await route.fulfill({
      body: "PK",
      contentType: "application/zip",
      headers: { "content-disposition": 'attachment; filename="job-1.zip"' },
    });
  });

  await page.goto("/login");
  await page.getByLabel("Username").fill("local");
  await page.getByLabel("Password").fill("secret");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page).toHaveURL(/\/submit$/);
  await page.getByLabel("Video URL").fill("https://www.youtube.com/watch?v=demo");
  await page.getByRole("button", { name: "Create note" }).click();
  await expect(page.getByText("$0.1000")).toBeVisible();
  await expect(page).toHaveURL(/\/edit\/job-1$/);

  await expect(page.getByText("Video ready")).toBeVisible();
  await expect(page.getByText("Transcript ready")).toBeVisible();
  await expect(page.getByText("Screenshots ready")).toBeVisible();
  await expect(page.getByText("Clip boundaries ready")).toBeVisible();
  await expect(page.getByText("Clip 1 summary ready")).toBeVisible();
  await expect(page.getByRole("button", { name: "Split" })).toBeEnabled();
  await expect(page.getByText("Note will refresh")).toBeVisible();

  await page.getByLabel("Summary").fill("Edited summary");
  await page.getByRole("button", { name: "Save clip" }).click();
  await expect(page.getByRole("dialog")).toContainText("This clip change will refresh");
  await page.getByRole("button", { name: "Keep editing" }).click();
  await expect(page.getByLabel("Summary")).toHaveValue("Edited summary");

  await page.goto("/review/job-1");
  await expect(page.getByLabel("Markdown editor")).toBeVisible();
  await expect(page.getByLabel("Scene caption")).toHaveValue("Original caption");

  await page.goto("/export/job-1");
  await expect(page.getByText("1 sections")).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download ZIP" }).click();
  expect((await download).suggestedFilename()).toBe("job-1.zip");
});
