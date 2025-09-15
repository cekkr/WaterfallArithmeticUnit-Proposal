#!/usr/bin/env node

/**
 * Markdown Renderer for Mermaid and LaTeX
 * Converts Mermaid diagrams and LaTeX expressions to images in markdown files.
 * 
 * Setup Instructions for macOS:
 * 1. Initialize npm project (if not already):
 *    npm init -y
 * 
 * 2. Install dependencies:
 *    npm install @mermaid-js/mermaid-cli puppeteer mathjax-node-cli crypto
 * 
 * 3. For LaTeX support (optional):
 *    npm install mathjax-node
 * 
 * 4. Run the script:
 *    node md_renderer.js input.md
 */

const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const { spawn } = require('child_process');
const util = require('util');
const execPromise = util.promisify(require('child_process').exec);

// Configuration
const CONFIG = {
    mermaid: {
        theme: 'default',
        backgroundColor: 'white',
        width: 800,
        height: 600,
        puppeteerConfig: {
            headless: 'new',
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        }
    },
    latex: {
        fontSize: 12,
        dpi: 150
    }
};

// Utility functions
function getHash(content) {
    return crypto.createHash('md5').update(content).digest('hex').substring(0, 8);
}

async function fileExists(filePath) {
    try {
        await fs.access(filePath);
        return true;
    } catch {
        return false;
    }
}

async function ensureDir(dirPath) {
    try {
        await fs.mkdir(dirPath, { recursive: true });
    } catch (error) {
        if (error.code !== 'EEXIST') throw error;
    }
}

// Check if required commands are available
async function checkDependencies() {
    const issues = [];
    
    try {
        await execPromise('which mmdc');
    } catch {
        issues.push(`
mmdc (Mermaid CLI) not found.
Install globally: npm install -g @mermaid-js/mermaid-cli
Or locally: npm install @mermaid-js/mermaid-cli
`);
    }
    
    // Check for Chrome/Chromium
    const chromePaths = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/Applications/Chromium.app/Contents/MacOS/Chromium',
        process.env.PUPPETEER_EXECUTABLE_PATH
    ].filter(Boolean);
    
    let chromeFound = false;
    for (const chromePath of chromePaths) {
        if (await fileExists(chromePath)) {
            chromeFound = true;
            process.env.PUPPETEER_EXECUTABLE_PATH = chromePath;
            break;
        }
    }
    
    if (!chromeFound) {
        console.log('⚠️  Chrome not found in standard locations, Puppeteer will try to use its bundled version');
    }
    
    return issues;
}

// Process Mermaid diagrams
async function processMermaidDiagrams(content, outputDir) {
    const mermaidRegex = /```mermaid\s*([\s\S]*?)```/g;
    const matches = [...content.matchAll(mermaidRegex)];
    
    if (matches.length === 0) return content;
    
    console.log(`Found ${matches.length} Mermaid diagram(s)`);
    
    // Create mermaid config file
    const configPath = path.join(outputDir, 'mermaid.config.json');
    await fs.writeFile(configPath, JSON.stringify({
        theme: CONFIG.mermaid.theme,
        themeVariables: {
            primaryColor: '#fff',
            primaryTextColor: '#000',
            primaryBorderColor: '#7C0000',
            lineColor: '#F8B229'
        }
    }));
    
    let newContent = content;
    let processedCount = 0;
    
    for (const [fullMatch, mermaidCode] of matches) {
        const trimmedCode = mermaidCode.trim();
        const hash = getHash(trimmedCode);
        const filename = `mermaid_diagram_${processedCount.toString().padStart(2, '0')}_${hash}.png`;
        const outputPath = path.join(outputDir, filename);
        
        processedCount++;
        
        // Skip if already exists
        if (await fileExists(outputPath)) {
            console.log(`  Diagram ${processedCount}: Already exists, skipping`);
            newContent = newContent.replace(fullMatch, `![Mermaid Diagram ${processedCount}](${filename})`);
            continue;
        }
        
        console.log(`  Diagram ${processedCount}: Rendering...`);
        
        // Write mermaid code to temp file
        const tempFile = path.join(outputDir, `temp_${processedCount}.mmd`);
        await fs.writeFile(tempFile, trimmedCode);
        
        try {
            // Run mmdc command
            const env = { ...process.env };
            if (process.platform === 'darwin') {
                // macOS specific settings
                const chromePath = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
                if (await fileExists(chromePath)) {
                    env.PUPPETEER_EXECUTABLE_PATH = chromePath;
                }
            }
            
            await new Promise((resolve, reject) => {
                const mmdc = spawn('mmdc', [
                    '-i', tempFile,
                    '-o', outputPath,
                    '-c', configPath,
                    '-b', CONFIG.mermaid.backgroundColor,
                    '-w', CONFIG.mermaid.width.toString(),
                    '-H', CONFIG.mermaid.height.toString()
                ], { env });
                
                let stderr = '';
                mmdc.stderr.on('data', (data) => {
                    stderr += data.toString();
                });
                
                mmdc.on('close', (code) => {
                    if (code === 0) {
                        console.log(`    ✓ Success`);
                        resolve();
                    } else {
                        reject(new Error(`mmdc exited with code ${code}: ${stderr}`));
                    }
                });
                
                mmdc.on('error', reject);
            });
            
            // Replace in content
            newContent = newContent.replace(fullMatch, `![Mermaid Diagram ${processedCount}](${filename})`);
            
        } catch (error) {
            console.error(`    ✗ Error: ${error.message}`);
        } finally {
            // Clean up temp file
            try {
                await fs.unlink(tempFile);
            } catch {}
        }
    }
    
    // Clean up config file
    try {
        await fs.unlink(configPath);
    } catch {}
    
    return newContent;
}

// Process LaTeX expressions
async function processLatexExpressions(content, outputDir) {
    // Check if mathjax-node is available
    let mjAPI;
    try {
        mjAPI = require('mathjax-node');
        mjAPI.config({
            MathJax: {
                SVG: { font: 'STIX-Web' }
            }
        });
        mjAPI.start();
    } catch {
        console.log('ℹ️  mathjax-node not installed, skipping LaTeX processing');
        console.log('   Install with: npm install mathjax-node');
        return content;
    }
    
    // Find LaTeX expressions
    const displayRegex = /\$\$([^\$]+)\$\$/g;
    const inlineRegex = /(?<!\$)\$(?!\$)([^\$\n]+)\$(?!\$)/g;
    
    const allMatches = [];
    [...content.matchAll(displayRegex)].forEach(match => {
        allMatches.push({ type: 'display', full: match[0], latex: match[1], index: match.index });
    });
    [...content.matchAll(inlineRegex)].forEach(match => {
        allMatches.push({ type: 'inline', full: match[0], latex: match[1], index: match.index });
    });
    
    if (allMatches.length === 0) return content;
    
    console.log(`Found ${allMatches.length} LaTeX expression(s)`);
    
    // Sort by index (position in document) to replace from end to beginning
    allMatches.sort((a, b) => b.index - a.index);
    
    let newContent = content;
    let processedCount = 0;
    
    for (const match of allMatches) {
        const hash = getHash(match.latex);
        const filename = `latex_${match.type}_${processedCount.toString().padStart(2, '0')}_${hash}.svg`;
        const outputPath = path.join(outputDir, filename);
        
        processedCount++;
        
        // Skip if already exists
        if (await fileExists(outputPath)) {
            console.log(`  Expression ${processedCount}: Already exists, skipping`);
            newContent = newContent.substring(0, match.index) + 
                        `![LaTeX Expression](${filename})` + 
                        newContent.substring(match.index + match.full.length);
            continue;
        }
        
        console.log(`  Expression ${processedCount} (${match.type}): Rendering...`);
        
        try {
            // Render with MathJax
            const result = await new Promise((resolve, reject) => {
                mjAPI.typeset({
                    math: match.latex,
                    format: 'TeX',
                    svg: true,
                    ex: match.type === 'display' ? 8 : 6
                }, (data) => {
                    if (!data.errors) {
                        resolve(data.svg);
                    } else {
                        reject(new Error(data.errors.join(', ')));
                    }
                });
            });
            
            // Save SVG
            await fs.writeFile(outputPath, result);
            console.log(`    ✓ Success`);
            
            // Replace in content
            newContent = newContent.substring(0, match.index) + 
                        `![LaTeX Expression](${filename})` + 
                        newContent.substring(match.index + match.full.length);
            
        } catch (error) {
            console.error(`    ✗ Error: ${error.message}`);
        }
    }
    
    return newContent;
}

// Main processing function
async function processMarkdownFile(inputFile) {
    console.log(`Processing: ${inputFile}\n`);
    
    // Check dependencies
    const issues = await checkDependencies();
    if (issues.length > 0) {
        console.log('⚠️  Dependency issues found:');
        issues.forEach(issue => console.log(issue));
        console.log('Continuing anyway, but some features may not work...\n');
    }
    
    // Read input file
    let content;
    try {
        content = await fs.readFile(inputFile, 'utf-8');
    } catch (error) {
        console.error(`Error reading file: ${error.message}`);
        process.exit(1);
    }
    
    // Create output directory
    const baseName = path.basename(inputFile, path.extname(inputFile));
    const outputDir = `${baseName}_processed`;
    await ensureDir(outputDir);
    console.log(`Output directory: ${outputDir}\n`);
    
    // Process Mermaid diagrams
    content = await processMermaidDiagrams(content, outputDir);
    
    // Process LaTeX expressions
    content = await processLatexExpressions(content, outputDir);
    
    // Write output markdown
    const outputFile = path.join(outputDir, path.basename(inputFile));
    try {
        await fs.writeFile(outputFile, content, 'utf-8');
        console.log('\n✅ Processing complete!');
        console.log(`   Output markdown: ${outputFile}`);
        console.log(`   Images saved in: ${outputDir}`);
    } catch (error) {
        console.error(`Error writing output: ${error.message}`);
        process.exit(1);
    }
}

// CLI entry point
async function main() {
    const args = process.argv.slice(2);
    
    if (args.length !== 1) {
        console.log('Usage: node md_renderer.js <markdown_file>');
        console.log('\nThis script converts Mermaid diagrams and LaTeX expressions');
        console.log('in markdown files to images.');
        process.exit(1);
    }
    
    const inputFile = args[0];
    
    try {
        await processMarkdownFile(inputFile);
    } catch (error) {
        console.error(`Fatal error: ${error.message}`);
        process.exit(1);
    }
}

// Run if called directly
if (require.main === module) {
    main();
}

module.exports = { processMarkdownFile };