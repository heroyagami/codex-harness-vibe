import assert from "node:assert/strict";
import test from "node:test";
import {
  analyzeForegroundAlpha,
  foregroundAlphaIssue,
  foregroundLayoutIssues,
} from "./foreground-layout.mjs";

const WIDTH = 1080;
const HEIGHT = 1440;

const fillRect = (alpha, x, y, width, height, value) => {
  for (let row = y; row < y + height; row += 1) {
    alpha.fill(value, row * WIDTH + x, row * WIDTH + x + width);
  }
};

const inspect = (alpha) => analyzeForegroundAlpha(alpha, WIDTH, HEIGHT);

test("accepts a horizontally centered foreground with visible inset", () => {
  const alpha = Buffer.alloc(WIDTH * HEIGHT);
  fillRect(alpha, 90, 240, 900, 760, 255);

  const analysis = inspect(alpha);
  assert.equal(foregroundAlphaIssue(analysis), null);
  assert.deepEqual(foregroundLayoutIssues(analysis, WIDTH, HEIGHT), []);
});

test("rejects the observed left-clipped wide wrapper", () => {
  const alpha = Buffer.alloc(WIDTH * HEIGHT);
  fillRect(alpha, 0, 396, 908, 807, 255);

  const analysis = inspect(alpha);
  assert.match(
    foregroundLayoutIssues(analysis, WIDTH, HEIGHT).join("; "),
    /left canvas edge is clipped/,
  );
});

test("rejects a near-left wrapper even when it misses the outermost pixel", () => {
  const alpha = Buffer.alloc(WIDTH * HEIGHT);
  fillRect(alpha, 32, 686, 828, 288, 255);

  const analysis = inspect(alpha);
  assert.match(
    foregroundLayoutIssues(analysis, WIDTH, HEIGHT).join("; "),
    /horizontal core is shifted left/,
  );
});

test("ignores faint edge glow and sparse opaque decoration", () => {
  const alpha = Buffer.alloc(WIDTH * HEIGHT);
  fillRect(alpha, 120, 260, 840, 760, 255);
  fillRect(alpha, 0, 360, 54, 400, 32);
  fillRect(alpha, 0, 500, 8, 90, 255);

  const analysis = inspect(alpha);
  assert.deepEqual(foregroundLayoutIssues(analysis, WIDTH, HEIGHT), []);
});

test("allows an explicit horizontal full-bleed treatment", () => {
  const alpha = Buffer.alloc(WIDTH * HEIGHT);
  fillRect(alpha, 0, 220, WIDTH, 900, 128);

  const analysis = inspect(alpha);
  assert.deepEqual(foregroundLayoutIssues(analysis, WIDTH, HEIGHT), []);
});

test("does not require content to be vertically centered", () => {
  const alpha = Buffer.alloc(WIDTH * HEIGHT);
  fillRect(alpha, 160, 40, 760, 900, 255);

  const analysis = inspect(alpha);
  assert.deepEqual(foregroundLayoutIssues(analysis, WIDTH, HEIGHT), []);
});

test("preserves alpha visibility validation", () => {
  const opaque = inspect(Buffer.alloc(WIDTH * HEIGHT, 255));
  const faintOnly = Buffer.alloc(WIDTH * HEIGHT);
  fillRect(faintOnly, 200, 300, 680, 500, 32);

  assert.match(foregroundAlphaIssue(opaque), /transparent background/);
  assert.match(foregroundAlphaIssue(inspect(faintOnly)), /alpha >= 64/);
});
