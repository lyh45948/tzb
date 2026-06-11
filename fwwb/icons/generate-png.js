/**
 * Script to convert SVG icons to PNG format
 * Run with: node generate-png.js
 * Requires: npm install sharp
 */

const fs = require('fs');
const path = require('path');

// Check if sharp is available
let sharp;
try {
  sharp = require('sharp');
} catch (e) {
  console.log('Sharp module not found. Installing...');
  console.log('Please run: npm install sharp');
  console.log('Then run this script again.');
  process.exit(1);
}

const iconsDir = __dirname;

const svgFiles = [
  'home.svg',
  'home-active.svg',
  'chart.svg',
  'chart-active.svg',
  'control.svg',
  'control-active.svg'
];

async function convertSvgToPng(svgFile) {
  const svgPath = path.join(iconsDir, svgFile);
  const pngFile = svgFile.replace('.svg', '.png');
  const pngPath = path.join(iconsDir, pngFile);

  try {
    await sharp(svgPath)
      .resize(48, 48)
      .png()
      .toFile(pngPath);
    console.log(`Created: ${pngFile}`);
  } catch (err) {
    console.error(`Error converting ${svgFile}:`, err.message);
  }
}

async function main() {
  console.log('Converting SVG icons to PNG format...\n');

  for (const svgFile of svgFiles) {
    await convertSvgToPng(svgFile);
  }

  console.log('\nDone! PNG files created in the icons directory.');
}

main();
