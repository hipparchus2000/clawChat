/**
 * Icon Generator Script
 * 
 * This script helps convert SVG icons to PNG format.
 * For production use, you can:
 * 
 * 1. Use an online converter like:
 *    - https://convertio.co/svg-png/
 *    - https://cloudconvert.com/svg-to-png
 * 
 * 2. Use Node.js with sharp or svg2png:
 *    npm install sharp
 *    
 *    const sharp = require('sharp');
 *    sharp('icons/icon-192x192.svg')
 *      .png()
 *      .toFile('icons/icon-192x192.png');
 * 
 * 3. Use a build tool like webpack with file-loader
 * 
 * 4. Use Inkscape CLI:
 *    inkscape icon-192x192.svg --export-filename=icon-192x192.png --export-width=192 --export-height=192
 * 
 * Required PNG sizes:
 * - 72x72 (Android)
 * - 96x96 (Android)
 * - 128x128 (Chrome Web Store)
 * - 144x144 (iOS, Windows)
 * - 152x152 (iOS)
 * - 192x192 (Android, PWA icon)
 * - 384x384 (Android)
 * - 512x512 (Android, PWA splash screen)
 */

const iconSizes = [72, 96, 128, 144, 152, 192, 384, 512];

console.log('Icon sizes needed:');
iconSizes.forEach(size => {
    console.log(`  - ${size}x${size}px`);
});

console.log('\nTo convert SVGs to PNGs, you can use:');
console.log('  1. Online converters (convertio.co, cloudconvert.com)');
console.log('  2. Node.js: npm install sharp, then run conversion');
console.log('  3. Inkscape CLI (see comments above)');
console.log('  4. ImageMagick: convert -background none icon.svg icon.png');
