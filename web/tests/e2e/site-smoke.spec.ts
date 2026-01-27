import { test, expect } from "@playwright/test";

const blockedPatterns = [
  /\/states\/[a-z]{2}\/index\.txt\?_rsc=/i,
  /\/tracker\/\d+\/index\.txt\?_rsc=/i,
];

function isBlockedUrl(url: string) {
  return blockedPatterns.some((pattern) => pattern.test(url));
}

test("home loads without RSC 404s", async ({ page }) => {
  const notFoundRsc: string[] = [];

  page.on("response", (response) => {
    if (response.status() === 404 && isBlockedUrl(response.url())) {
      notFoundRsc.push(response.url());
    }
  });

  await page.goto("/", { waitUntil: "networkidle" });
  await expect(page).toHaveTitle(/Civitas/i);

  expect(notFoundRsc, `Unexpected RSC 404s: ${notFoundRsc.join(", ")}`).toHaveLength(0);
});

test("states detail page loads", async ({ page }) => {
  const notFoundRsc: string[] = [];
  page.on("response", (response) => {
    if (response.status() === 404 && isBlockedUrl(response.url())) {
      notFoundRsc.push(response.url());
    }
  });

  await page.goto("/states/ak", { waitUntil: "networkidle" });
  await expect(page.getByText("This page could not be found.")).toHaveCount(0);

  const alaskaHeading = page.getByRole("heading", { name: /Alaska/i });
  const fetchError = page.getByText(/Failed to connect to server|Failed to load state data/i);
  await expect(alaskaHeading.or(fetchError)).toBeVisible();

  expect(notFoundRsc, `Unexpected RSC 404s: ${notFoundRsc.join(", ")}`).toHaveLength(0);
});

test("tracker page loads", async ({ page }) => {
  const notFoundRsc: string[] = [];
  page.on("response", (response) => {
    if (response.status() === 404 && isBlockedUrl(response.url())) {
      notFoundRsc.push(response.url());
    }
  });

  await page.goto("/tracker", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: /Project 2025 Tracker/i })).toBeVisible();

  expect(notFoundRsc, `Unexpected RSC 404s: ${notFoundRsc.join(", ")}`).toHaveLength(0);
});

test("resistance page loads", async ({ page }) => {
  const notFoundRsc: string[] = [];
  page.on("response", (response) => {
    if (response.status() === 404 && isBlockedUrl(response.url())) {
      notFoundRsc.push(response.url());
    }
  });

  await page.goto("/resistance", { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: /Resistance Strategy/i })).toBeVisible();

  expect(notFoundRsc, `Unexpected RSC 404s: ${notFoundRsc.join(", ")}`).toHaveLength(0);
});
