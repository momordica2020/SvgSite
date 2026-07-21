const fs = require('fs');
const path = require('path');

const projectRoot = path.join(__dirname, '..');
const svgDir = path.join(projectRoot, 'svg');
const dataDir = path.join(projectRoot, 'data');
const originalsDir = path.join(projectRoot, 'originals');
const detailDir = path.join(projectRoot, 'detail');

// 确保目录存在
if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
}
if (!fs.existsSync(originalsDir)) {
    fs.mkdirSync(originalsDir, { recursive: true });
}
if (!fs.existsSync(detailDir)) {
    fs.mkdirSync(detailDir, { recursive: true });
}

// 读取元数据文件
function readMetadata() {
    const metadataPath = path.join(dataDir, 'metadata.json');
    if (!fs.existsSync(metadataPath)) {
        console.log('metadata.json 不存在，将创建空文件');
        fs.writeFileSync(metadataPath, '[]');
        return [];
    }
    try {
        const content = fs.readFileSync(metadataPath, 'utf-8');
        return JSON.parse(content);
    } catch (e) {
        console.error('读取 metadata.json 失败:', e.message);
        return [];
    }
}

// 读取所有SVG文件
function readSvgFiles() {
    if (!fs.existsSync(svgDir)) {
        console.log('svg 目录不存在');
        return [];
    }
    return fs.readdirSync(svgDir).filter(file => file.endsWith('.svg'));
}

// 提取SVG尺寸信息（用于预加载
function extractSvgInfo(svgRaw) {
    const viewBoxMatch = svgRaw.match(/viewBox=["']([^"']+)["']/i);
    const viewBox = viewBoxMatch ? viewBoxMatch[1] : null;
    const widthMatch = svgRaw.match(/\bwidth=["']([^"']+)["']/i);
    const heightMatch = svgRaw.match(/\bheight=["']([^"']+)["']/i);
    return {
        viewBox: viewBox,
        width: widthMatch ? widthMatch[1] : null,
        height: heightMatch ? heightMatch[1] : null
    };
}

// 生成最终的images.json
function generateImagesJson() {
    const metadata = readMetadata();
    const svgFiles = readSvgFiles();

    const images = [];

    // 遍历元数据，合并SVG信息
    metadata.forEach(meta => {
        const svgPath = path.join(svgDir, meta.svgFile);
        let svgInfo = { viewBox: null, width: null, height: null };

        if (fs.existsSync(svgPath)) {
            const svgRaw = fs.readFileSync(svgPath, 'utf-8');
            svgInfo = extractSvgInfo(svgRaw);
        } else {
            console.warn(`警告: SVG文件不存在 - ${meta.svgFile}`);
        }

        // 检查原始图片是否存在
        let hasOriginal = false;
        if (meta.originalImage) {
            const origPath = path.join(originalsDir, meta.originalImage);
            hasOriginal = fs.existsSync(origPath);
            if (!hasOriginal) {
                console.warn(`警告: 原始图片不存在 - ${meta.originalImage}`);
            }
        }

        images.push({
            id: meta.id,
            name: meta.name,
            tags: meta.tags || [],
            svgFile: meta.svgFile,
            viewBox: svgInfo.viewBox,
            svgWidth: svgInfo.width,
            svgHeight: svgInfo.height,
            originalImage: hasOriginal ? meta.originalImage : null,
            description: meta.description || ''
        });
    });

    // 检查是否有SVG文件没有对应的元数据
    const metaSvgFiles = new Set(metadata.map(m => m.svgFile));
    svgFiles.forEach(file => {
        if (!metaSvgFiles.has(file)) {
            console.warn(`警告: SVG文件没有元数据 - ${file}`);
        }
    });

    // 按名称排序
    images.sort((a, b) => a.name.localeCompare(b.name));

    // 写入images.json
    const jsonContent = JSON.stringify(images, null, 2);
    fs.writeFileSync(path.join(dataDir, 'images.json'), jsonContent);
    console.log(`成功生成 ${images.length} 张图片的数据 -> data/images.json`);

    return images;
}

function generateDetailPages(images) {
    images.forEach(img => {
        const originalHtml = img.originalImage ? 
            `<img src="../originals/${encodeURIComponent(img.originalImage)}" alt="${escapeHtml(img.name)} 原始图片" class="detail-original-image">` : 
            '<div class="detail-no-original">暂无原始图片</div>';
        
        const tagsHtml = img.tags.map(tag =>
            `<a href="../index.html?tag=${encodeURIComponent(tag)}" class="tag">${escapeHtml(tag)}</a>`
        ).join('');

        const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${escapeHtml(img.name)} - SVG Gallery</title>
    <link rel="stylesheet" href="../src/style.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script>
        (function() {
            const saved = localStorage.getItem('svg-gallery-theme');
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            const isDark = saved ? saved === 'dark' : prefersDark;
            if (isDark) {
                document.documentElement.classList.add('dark-mode');
            }
        })();
    </script>
</head>
<body>
    <div class="detail-page">
        <header class="detail-header">
            <div class="container">
                <a href="../index.html" class="back-btn">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="19" y1="12" x2="5" y2="12"/>
                        <polyline points="12 19 5 12 12 5"/>
                    </svg>
                    返回图库
                </a>
                <div class="logo">
                    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                        <path d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM4 18V6h16v12H4zm14-6l-4-4-4 4-2-2-6 6 8 8 10-10-4-4z"/>
                    </svg>
                    <span>SVG Gallery</span>
                </div>
                <button class="theme-toggle-btn" id="themeToggleBtn" title="切换主题">
                    <svg id="themeIconSun" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" style="display: none;">
                        <circle cx="12" cy="12" r="5"/>
                        <line x1="12" y1="1" x2="12" y2="3"/>
                        <line x1="12" y1="21" x2="12" y2="23"/>
                        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
                        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
                        <line x1="1" y1="12" x2="3" y2="12"/>
                        <line x1="21" y1="12" x2="23" y2="12"/>
                        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
                        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
                    </svg>
                    <svg id="themeIconMoon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                    </svg>
                </button>
            </div>
        </header>
        <main class="detail-body">
            <div class="container">
                <div id="detailContent">
                    <div class="detail-layout">
                        <div class="detail-preview-section">
                            <div class="detail-preview-container" id="detailPreviewWrapper">
                                <div class="detail-preview-canvas" id="detailPreviewCanvas">
                                    <img id="detailSvgImg" src="../svg/${encodeURIComponent(img.svgFile)}" alt="${escapeHtml(img.name)}" draggable="false">
                                </div>
                            </div>
                            <div class="detail-zoom-indicator" id="detailZoomIndicator">100%</div>
                            <div class="detail-download-actions">
                                <button class="download-btn" id="detailDownloadSvgBtn">
                                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                                        <polyline points="7 10 12 15 17 10"/>
                                        <line x1="12" y1="15" x2="12" y2="3"/>
                                    </svg>
                                    下载 SVG
                                </button>
                                <div class="png-download-group">
                                    <span class="png-label">PNG:</span>
                                    <button class="download-btn-small" data-size="256">256px</button>
                                    <button class="download-btn-small" data-size="512">512px</button>
                                    <button class="download-btn-small" data-size="1024">1024px</button>
                                    <button class="download-btn-small" data-size="2048">2048px</button>
                                    <button class="download-btn-small" data-size="4096">4096px</button>
                                </div>
                            </div>
                        </div>
                        <div class="detail-info-section">
                            <div class="detail-info-card">
                                <h1 class="detail-name" id="detailName">${escapeHtml(img.name)}</h1>
                                <div class="detail-tags" id="detailTags">${tagsHtml}</div>
                            </div>
                            <div class="detail-info-card" ${!img.originalImage ? 'style="display: none;"' : ''} id="detailOriginalCard">
                                <h3>
                                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                                        <circle cx="8.5" cy="8.5" r="1.5"/>
                                        <polyline points="21 15 16 10 5 21"/>
                                    </svg>
                                    原始来源图片
                                </h3>
                                <div id="detailOriginalContent">${originalHtml}</div>
                            </div>
                            <div class="detail-info-card">
                                <h3>
                                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                                        <polyline points="14 2 14 8 20 8"/>
                                        <line x1="16" y1="13" x2="8" y2="13"/>
                                        <line x1="16" y1="17" x2="8" y2="17"/>
                                        <polyline points="10 9 9 9 8 9"/>
                                    </svg>
                                    详细描述
                                </h3>
                                <div class="markdown-body" id="detailDescription">${img.description ? '<p style="color: var(--text-secondary);">加载中...</p>' : '<p style="color: var(--text-secondary);">暂无描述</p>'}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>
    <script>
        const currentImage = ${JSON.stringify(img)};
    </script>
    <script src="../src/detail.js"></script>
</body>
</html>`;

        const detailPath = path.join(detailDir, `${img.id}.html`);
        fs.writeFileSync(detailPath, html);
    });
    console.log(`成功生成 ${images.length} 个详情页 -> detail/`);
}

function escapeHtml(text) {
    if (text == null) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

const images = generateImagesJson();
generateDetailPages(images);