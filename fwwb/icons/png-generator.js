/**
 * Pure JavaScript PNG Generator for Tab Bar Icons
 * No external dependencies required
 *
 * Usage: node png-generator.js
 */

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const ICON_SIZE = 48;

// Color definitions
const COLORS = {
  inactive: { r: 153, g: 153, b: 153 }, // #999999
  active: { r: 76, g: 175, b: 80 }      // #4CAF50
};

// CRC32 implementation
function crc32(data) {
  let crc = 0xffffffff;
  const table = [];
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let j = 0; j < 8; j++) {
      c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
    }
    table[i] = c;
  }
  for (let i = 0; i < data.length; i++) {
    crc = table[(crc ^ data[i]) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

// Create PNG chunk
function createChunk(type, data) {
  const typeBuffer = Buffer.from(type, 'ascii');
  const length = Buffer.alloc(4);
  length.writeUInt32BE(data.length, 0);

  const crcData = Buffer.concat([typeBuffer, data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(crcData), 0);

  return Buffer.concat([length, typeBuffer, data, crc]);
}

// Create PNG file from RGBA data
function createPNG(rgbaData, width, height) {
  // PNG signature
  const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  // IHDR chunk
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;  // bit depth
  ihdr[9] = 6;  // color type (RGBA)
  ihdr[10] = 0; // compression
  ihdr[11] = 0; // filter
  ihdr[12] = 0; // interlace

  // Prepare raw data with filter bytes
  const rawData = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y++) {
    rawData[y * (width * 4 + 1)] = 0; // filter type: none
    for (let x = 0; x < width; x++) {
      const srcIdx = (y * width + x) * 4;
      const dstIdx = y * (width * 4 + 1) + 1 + x * 4;
      rawData[dstIdx] = rgbaData[srcIdx];
      rawData[dstIdx + 1] = rgbaData[srcIdx + 1];
      rawData[dstIdx + 2] = rgbaData[srcIdx + 2];
      rawData[dstIdx + 3] = rgbaData[srcIdx + 3];
    }
  }

  // Compress data
  const compressed = zlib.deflateSync(rawData, { level: 9 });

  // IEND chunk (empty)
  const iend = Buffer.alloc(0);

  // Assemble PNG
  return Buffer.concat([
    signature,
    createChunk('IHDR', ihdr),
    createChunk('IDAT', compressed),
    createChunk('IEND', iend)
  ]);
}

// Draw line using Bresenham's algorithm
function drawLine(pixels, x0, y0, x1, y1, color, lineWidth) {
  const dx = Math.abs(x1 - x0);
  const dy = Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1;
  const sy = y0 < y1 ? 1 : -1;
  let err = dx - dy;

  const halfWidth = Math.floor(lineWidth / 2);

  function setPixel(px, py) {
    for (let ox = -halfWidth; ox <= halfWidth; ox++) {
      for (let oy = -halfWidth; oy <= halfWidth; oy++) {
        const nx = Math.round(px + ox);
        const ny = Math.round(py + oy);
        if (nx >= 0 && nx < ICON_SIZE && ny >= 0 && ny < ICON_SIZE) {
          const idx = (ny * ICON_SIZE + nx) * 4;
          pixels[idx] = color.r;
          pixels[idx + 1] = color.g;
          pixels[idx + 2] = color.b;
          pixels[idx + 3] = 255;
        }
      }
    }
  }

  while (true) {
    setPixel(x0, y0);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 > -dy) { err -= dy; x0 += sx; }
    if (e2 < dx) { err += dx; y0 += sy; }
  }
}

// Draw rounded rectangle
function drawRoundedRect(pixels, x, y, w, h, r, color, lineWidth, fill = false) {
  const halfWidth = Math.floor(lineWidth / 2);

  for (let py = 0; py < ICON_SIZE; py++) {
    for (let px = 0; px < ICON_SIZE; px++) {
      // Check if point is inside rounded rectangle
      let inside = false;

      if (fill) {
        inside = isInsideRoundedRect(px, py, x, y, w, h, r);
      } else {
        // Draw border
        inside = isInsideRoundedRect(px, py, x, y, w, h, r) &&
                 !isInsideRoundedRect(px, py, x + lineWidth, y + lineWidth,
                                      w - 2*lineWidth, h - 2*lineWidth,
                                      Math.max(0, r - lineWidth));
      }

      if (inside) {
        const idx = (py * ICON_SIZE + px) * 4;
        pixels[idx] = color.r;
        pixels[idx + 1] = color.g;
        pixels[idx + 2] = color.b;
        pixels[idx + 3] = 255;
      }
    }
  }
}

function isInsideRoundedRect(px, py, x, y, w, h, r) {
  // Check main rectangle areas
  if (px >= x + r && px < x + w - r && py >= y && py < y + h) return true;
  if (px >= x && px < x + w && py >= y + r && py < y + h - r) return true;

  // Check corner circles
  const corners = [
    { cx: x + r, cy: y + r },
    { cx: x + w - r, cy: y + r },
    { cx: x + r, cy: y + h - r },
    { cx: x + w - r, cy: y + h - r }
  ];

  for (const corner of corners) {
    const dx = px - corner.cx;
    const dy = py - corner.cy;
    if (dx >= -r && dx < r && dy >= -r && dy < r) {
      if (dx * dx + dy * dy <= r * r) return true;
    }
  }

  return false;
}

// Draw circle
function drawCircle(pixels, cx, cy, radius, color, lineWidth, fill = false) {
  const r2 = radius * radius;
  const innerR2 = (radius - lineWidth) * (radius - lineWidth);

  for (let y = 0; y < ICON_SIZE; y++) {
    for (let x = 0; x < ICON_SIZE; x++) {
      const dx = x - cx;
      const dy = y - cy;
      const dist2 = dx * dx + dy * dy;

      let inside = false;
      if (fill) {
        inside = dist2 <= r2;
      } else {
        inside = dist2 <= r2 && dist2 > innerR2;
      }

      if (inside) {
        const idx = (y * ICON_SIZE + x) * 4;
        pixels[idx] = color.r;
        pixels[idx + 1] = color.g;
        pixels[idx + 2] = color.b;
        pixels[idx + 3] = 255;
      }
    }
  }
}

// Draw rectangle
function drawRect(pixels, x, y, w, h, color, fill = true) {
  for (let py = y; py < y + h && py < ICON_SIZE; py++) {
    for (let px = x; px < x + w && px < ICON_SIZE; px++) {
      if (px >= 0 && py >= 0) {
        const idx = (py * ICON_SIZE + px) * 4;
        pixels[idx] = color.r;
        pixels[idx + 1] = color.g;
        pixels[idx + 2] = color.b;
        pixels[idx + 3] = 255;
      }
    }
  }
}

// Create home icon
function createHomeIcon(color) {
  const pixels = Buffer.alloc(ICON_SIZE * ICON_SIZE * 4);

  // House outline
  drawLine(pixels, 24, 6, 6, 20, color, 3);
  drawLine(pixels, 24, 6, 42, 20, color, 3);
  drawLine(pixels, 6, 20, 6, 42, color, 3);
  drawLine(pixels, 42, 20, 42, 42, color, 3);
  drawLine(pixels, 6, 42, 18, 42, color, 3);
  drawLine(pixels, 30, 42, 42, 42, color, 3);
  drawLine(pixels, 18, 30, 18, 42, color, 3);
  drawLine(pixels, 30, 30, 30, 42, color, 3);
  drawLine(pixels, 18, 30, 30, 30, color, 3);

  // Door
  drawRect(pixels, 21, 30, 6, 12, color);

  return createPNG(pixels, ICON_SIZE, ICON_SIZE);
}

// Create chart/monitor icon
function createChartIcon(color) {
  const pixels = Buffer.alloc(ICON_SIZE * ICON_SIZE * 4);

  // Monitor outline
  drawRoundedRect(pixels, 6, 8, 36, 28, 3, color, 3, false);

  // Line chart
  drawLine(pixels, 12, 28, 18, 22, color, 2);
  drawLine(pixels, 18, 22, 24, 26, color, 2);
  drawLine(pixels, 24, 26, 30, 18, color, 2);
  drawLine(pixels, 30, 18, 36, 24, color, 2);

  // Stand
  drawLine(pixels, 18, 40, 30, 40, color, 3);
  drawLine(pixels, 24, 36, 24, 40, color, 3);

  return createPNG(pixels, ICON_SIZE, ICON_SIZE);
}

// Create control/settings icon
function createControlIcon(color) {
  const pixels = Buffer.alloc(ICON_SIZE * ICON_SIZE * 4);

  // Center circle
  drawCircle(pixels, 24, 24, 7, color, 3, false);

  // Spokes
  drawLine(pixels, 24, 6, 24, 14, color, 3);
  drawLine(pixels, 24, 34, 24, 42, color, 3);
  drawLine(pixels, 6, 24, 14, 24, color, 3);
  drawLine(pixels, 34, 24, 42, 24, color, 3);

  // Diagonal spokes
  drawLine(pixels, 11, 11, 17, 17, color, 3);
  drawLine(pixels, 31, 31, 37, 37, color, 3);
  drawLine(pixels, 11, 37, 17, 31, color, 3);
  drawLine(pixels, 31, 17, 37, 11, color, 3);

  return createPNG(pixels, ICON_SIZE, ICON_SIZE);
}

// Main function
function main() {
  const iconsDir = __dirname;

  const icons = [
    { name: 'home', generator: createHomeIcon, color: COLORS.inactive },
    { name: 'home-active', generator: createHomeIcon, color: COLORS.active },
    { name: 'chart', generator: createChartIcon, color: COLORS.inactive },
    { name: 'chart-active', generator: createChartIcon, color: COLORS.active },
    { name: 'control', generator: createControlIcon, color: COLORS.inactive },
    { name: 'control-active', generator: createControlIcon, color: COLORS.active }
  ];

  console.log('Generating PNG icons...\n');

  icons.forEach(icon => {
    const pngData = icon.generator(icon.color);
    const filePath = path.join(iconsDir, `${icon.name}.png`);
    fs.writeFileSync(filePath, pngData);
    console.log(`Created: ${icon.name}.png (${pngData.length} bytes)`);
  });

  console.log('\nDone! All PNG icons generated successfully.');
}

main();
