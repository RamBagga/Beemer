import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const out = process.env.PARITY_DIR || path.join(process.cwd(), "test-results", "parity");
fs.mkdirSync(out, { recursive: true });

test("pages, drawer and night mode", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "India tech, measured." })).toBeVisible();
  await expect(page.getByText("10.1%/yr").first()).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("Beemer Picks")).toBeVisible();
  await page.screenshot({ path: path.join(out, "new-cockpit.png"), fullPage: true });
  await page.locator(".bmp-wrap").screenshot({ path: path.join(out, "new-belts.png") });

  await page.goto("/screener");
  await expect(page.getByRole("heading", { name: "Quality first. Then price." })).toBeVisible();
  await expect(page.getByText("matches")).toBeVisible({ timeout: 60_000 });
  await page.screenshot({ path: path.join(out, "new-screener.png"), fullPage: true });

  await page.goto("/company?symbol=INFY");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Infosys");
  await expect(page.getByText("Buffett checklist")).toBeVisible({ timeout: 60_000 });
  await page.screenshot({ path: path.join(out, "new-company-infy.png"), fullPage: true });

  await page.goto("/learn");
  await expect(page.getByRole("heading", { name: "Engineered understanding." })).toBeVisible();
  await expect(page.getByText("Made with ❤️ by baggak8s")).toBeVisible();
  await page.screenshot({ path: path.join(out, "new-academy.png"), fullPage: true });

  await page.goto("/");
  await page.locator("#bm-burger").click();
  await expect(page.locator("html")).toHaveClass(/bm-open/);
  await page.screenshot({ path: path.join(out, "new-drawer.png") });
  await page.keyboard.press("Escape");
  await expect(page.locator("html")).not.toHaveClass(/bm-open/);

  await page.locator("#bm-burger").click();
  await page.getByRole("button", { name: "Night" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.keyboard.press("Escape");
  await page.screenshot({ path: path.join(out, "new-night.png"), fullPage: false });

  expect(errors, errors.join("\n")).toEqual([]);
});
