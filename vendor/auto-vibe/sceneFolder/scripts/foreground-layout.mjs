export const FOREGROUND_ALPHA_THRESHOLD = 64;
export const FOREGROUND_OUTLIER_FRACTION = 0.01;
export const FOREGROUND_SAFE_EDGE_FRACTION = 0.05;
export const FOREGROUND_MAX_CENTER_OFFSET_FRACTION = 0.08;
export const FOREGROUND_EDGE_CONTACT_FRACTION = 0.05;

const quantilePosition = (counts, total, fraction, reverse = false) => {
  const target = Math.max(1, Math.ceil(total * fraction));
  let seen = 0;

  for (let offset = 0; offset < counts.length; offset += 1) {
    const index = reverse ? counts.length - 1 - offset : offset;
    seen += counts[index];
    if (seen >= target) return index;
  }

  return reverse ? counts.length - 1 : 0;
};

export const analyzeForegroundAlpha = (alpha, width, height) => {
  const expectedLength = width * height;
  if (alpha.length !== expectedLength) {
    throw new Error(
      `Expected ${expectedLength} alpha samples, received ${alpha.length}`,
    );
  }

  const columns = new Uint32Array(width);
  const rows = new Uint32Array(height);
  let alphaSum = 0;
  let substantialPixels = 0;
  let substantialXSum = 0;
  let substantialYSum = 0;

  for (let y = 0; y < height; y += 1) {
    const rowOffset = y * width;
    for (let x = 0; x < width; x += 1) {
      const value = alpha[rowOffset + x];
      alphaSum += value;
      if (value < FOREGROUND_ALPHA_THRESHOLD) continue;

      columns[x] += 1;
      rows[y] += 1;
      substantialPixels += 1;
      substantialXSum += x;
      substantialYSum += y;
    }
  }

  const base = {
    meanAlpha: alphaSum / expectedLength,
    substantialPixels,
  };
  if (substantialPixels === 0) return base;

  const marginX = Math.round(width * FOREGROUND_SAFE_EDGE_FRACTION);
  const marginY = Math.round(height * FOREGROUND_SAFE_EDGE_FRACTION);
  const contactRows = Math.ceil(height * FOREGROUND_EDGE_CONTACT_FRACTION);
  const contactColumns = Math.ceil(width * FOREGROUND_EDGE_CONTACT_FRACTION);

  return {
    ...base,
    bounds: {
      left: quantilePosition(
        columns,
        substantialPixels,
        FOREGROUND_OUTLIER_FRACTION,
      ),
      right: quantilePosition(
        columns,
        substantialPixels,
        FOREGROUND_OUTLIER_FRACTION,
        true,
      ),
      top: quantilePosition(
        rows,
        substantialPixels,
        FOREGROUND_OUTLIER_FRACTION,
      ),
      bottom: quantilePosition(
        rows,
        substantialPixels,
        FOREGROUND_OUTLIER_FRACTION,
        true,
      ),
    },
    center: {
      x: substantialXSum / substantialPixels,
      y: substantialYSum / substantialPixels,
    },
    contacts: {
      left: columns[0] >= contactRows,
      right: columns[width - 1] >= contactRows,
      top: rows[0] >= contactColumns,
      bottom: rows[height - 1] >= contactColumns,
    },
    limits: {
      marginX,
      marginY,
      maxCenterOffsetX: width * FOREGROUND_MAX_CENTER_OFFSET_FRACTION,
      maxCenterOffsetY: height * FOREGROUND_MAX_CENTER_OFFSET_FRACTION,
    },
  };
};

export const foregroundAlphaIssue = (analysis) => {
  if (
    !Number.isFinite(analysis.meanAlpha) ||
    analysis.meanAlpha <= 0 ||
    analysis.meanAlpha >= 255
  ) {
    return "must contain both a visible foreground and transparent background";
  }
  if (analysis.substantialPixels === 0) {
    return `must contain foreground pixels with alpha >= ${FOREGROUND_ALPHA_THRESHOLD}`;
  }
  return null;
};

const axisIssues = ({
  lowName,
  highName,
  lowBound,
  highBound,
  lowLimit,
  highLimit,
  lowContact,
  highContact,
  center,
  canvasCenter,
  maxCenterOffset,
  axisName,
  checkCenterShift = true,
}) => {
  const issues = [];
  const lowIntrudes = lowBound < lowLimit;
  const highIntrudes = highBound > highLimit;
  const fullBleed = lowContact && highContact;

  if (!fullBleed && lowContact && lowIntrudes) {
    issues.push(`${lowName} canvas edge is clipped`);
  }
  if (!fullBleed && highContact && highIntrudes) {
    issues.push(`${highName} canvas edge is clipped`);
  }

  if (
    checkCenterShift &&
    !fullBleed &&
    (lowIntrudes || highIntrudes) &&
    Math.abs(center - canvasCenter) > maxCenterOffset
  ) {
    const direction = center < canvasCenter ? lowName : highName;
    issues.push(`${axisName} core is shifted ${direction} near the safe edge`);
  }

  return issues;
};

export const foregroundLayoutIssues = (analysis, width, height) => {
  if (!analysis.bounds) return [];

  return [
    ...axisIssues({
      lowName: "left",
      highName: "right",
      lowBound: analysis.bounds.left,
      highBound: analysis.bounds.right,
      lowLimit: analysis.limits.marginX,
      highLimit: width - 1 - analysis.limits.marginX,
      lowContact: analysis.contacts.left,
      highContact: analysis.contacts.right,
      center: analysis.center.x,
      canvasCenter: (width - 1) / 2,
      maxCenterOffset: analysis.limits.maxCenterOffsetX,
      axisName: "horizontal",
    }),
    ...axisIssues({
      lowName: "top",
      highName: "bottom",
      lowBound: analysis.bounds.top,
      highBound: analysis.bounds.bottom,
      lowLimit: analysis.limits.marginY,
      highLimit: height - 1 - analysis.limits.marginY,
      lowContact: analysis.contacts.top,
      highContact: analysis.contacts.bottom,
      center: analysis.center.y,
      canvasCenter: (height - 1) / 2,
      maxCenterOffset: analysis.limits.maxCenterOffsetY,
      axisName: "vertical",
      checkCenterShift: false,
    }),
  ];
};

export const formatForegroundLayout = (analysis) => {
  if (!analysis.bounds) return "no substantial foreground bounds";
  return (
    `bounds x=${analysis.bounds.left}..${analysis.bounds.right}, ` +
    `y=${analysis.bounds.top}..${analysis.bounds.bottom}; ` +
    `center=(${analysis.center.x.toFixed(1)}, ${analysis.center.y.toFixed(1)})`
  );
};
