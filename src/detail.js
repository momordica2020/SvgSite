let zoomLevel = 1;
let panX = 0;
let panY = 0;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;

document.addEventListener('DOMContentLoaded', () => {
    if (currentImage && currentImage.id) {
        renderMarkdown();
    } else {
        const params = new URLSearchParams(window.location.search);
        const id = params.get('id');
        if (!id) {
            showNotFound();
            return;
        }
        loadDetail(id);
    }
    setupDownloadListeners();
    setupZoom();
    initTheme();
});

async function loadDetail(id) {
    try {
        const response = await fetch('data/images.json');
        const images = await response.json();

        currentImage = images.find(img => img.id === id);

        if (!currentImage) {
            showNotFound();
            return;
        }

        renderDetail();
    } catch (error) {
        console.error('加载详情失败:', error);
        showNotFound();
    }
}

function renderMarkdown() {
    const descEl = document.getElementById('detailDescription');
    if (currentImage && currentImage.description) {
        descEl.innerHTML = marked.parse(currentImage.description);
    }
}

function getSvgBasePath() {
    return window.location.pathname.includes('/detail/') ? '../svg/' : 'svg/';
}

function getOriginalsBasePath() {
    return window.location.pathname.includes('/detail/') ? '../originals/' : 'originals/';
}

function renderDetail() {
    const loading = document.getElementById('detailLoading');
    const content = document.getElementById('detailContent');

    loading.style.display = 'none';
    content.style.display = 'block';

    // 设置页面标题
    document.title = `${currentImage.name} - Svg Site`;

    // 名称
    document.getElementById('detailName').textContent = currentImage.name;

    // 标签 - 可点击跳转回主页面对应标签筛选
    const tagBasePath = window.location.pathname.includes('/detail/') ? '../index.html' : 'index.html';
    document.getElementById('detailTags').innerHTML = currentImage.tags.map(tag =>
        `<a href="${tagBasePath}?tag=${encodeURIComponent(tag)}" class="tag">${escapeHtml(tag)}</a>`
    ).join('');

    // SVG预览
    const svgImg = document.getElementById('detailSvgImg');
    if (svgImg) {
        svgImg.src = `${getSvgBasePath()}${encodeURIComponent(currentImage.svgFile)}`;
        svgImg.alt = currentImage.name;
    }

    // 原始来源图片
    if (currentImage.originalImage) {
        const card = document.getElementById('detailOriginalCard');
        const origContent = document.getElementById('detailOriginalContent');
        card.style.display = 'block';
        const origPath = `${getOriginalsBasePath()}${encodeURIComponent(currentImage.originalImage)}`;
        origContent.innerHTML = `<img src="${origPath}" alt="${escapeHtml(currentImage.name)} 原始图片" class="detail-original-image">`;
    }

    // Markdown描述
    const descEl = document.getElementById('detailDescription');
    if (currentImage.description) {
        descEl.innerHTML = marked.parse(currentImage.description);
    } else {
        descEl.innerHTML = '<p style="color: var(--text-secondary);">暂无描述</p>';
    }
}

function setupDownloadListeners() {
    document.getElementById('detailDownloadSvgBtn').addEventListener('click', downloadSvg);
    document.querySelectorAll('.detail-download-actions .download-btn-small').forEach(btn => {
        btn.addEventListener('click', () => {
            downloadPng(parseInt(btn.dataset.size));
        });
    });
}

function showNotFound() {
    document.getElementById('detailLoading').style.display = 'none';
    document.getElementById('detailNotFound').style.display = 'block';
}

// ========== 下载 ==========
function downloadSvg() {
    if (!currentImage) return;

    const a = document.createElement('a');
    a.href = `${getSvgBasePath()}${encodeURIComponent(currentImage.svgFile)}`;
    a.download = currentImage.svgFile;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function downloadPng(size) {
    if (!currentImage) return;

    const img = new Image();
    img.crossOrigin = 'anonymous';

    img.onload = () => {
        const aspect = img.width / img.height;
        let canvasWidth, canvasHeight;
        if (aspect >= 1) {
            canvasWidth = size;
            canvasHeight = Math.round(size / aspect);
        } else {
            canvasHeight = size;
            canvasWidth = Math.round(size * aspect);
        }

        const canvas = document.createElement('canvas');
        canvas.width = canvasWidth;
        canvas.height = canvasHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, canvasWidth, canvasHeight);

        const pngUrl = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = pngUrl;
        a.download = `${currentImage.name}_${size}px.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    };

    img.onerror = () => {
        console.error('PNG生成失败');
    };

    img.src = `${getSvgBasePath()}${encodeURIComponent(currentImage.svgFile)}`;
}

// ========== 缩放与拖拽 ==========
function setupZoom() {
    const wrapper = document.getElementById('detailPreviewWrapper');
    const canvas = document.getElementById('detailPreviewCanvas');
    const indicator = document.getElementById('detailZoomIndicator');

    if (!wrapper || !canvas) return;

    wrapper.addEventListener('wheel', (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        const newZoom = Math.max(0.2, Math.min(10, zoomLevel + delta));
        
        if (newZoom !== zoomLevel) {
            zoomLevel = newZoom;
            updateTransform(canvas);
            indicator.textContent = `${Math.round(zoomLevel * 100)}%`;
        }
    }, { passive: false });

    wrapper.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return;
        isDragging = true;
        dragStartX = e.clientX - panX;
        dragStartY = e.clientY - panY;
        canvas.style.cursor = 'grabbing';
        canvas.style.transition = 'none';
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        panX = e.clientX - dragStartX;
        panY = e.clientY - dragStartY;
        updateTransform(canvas);
    });

    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            canvas.style.cursor = '';
            canvas.style.transition = '';
        }
    });

    wrapper.addEventListener('dblclick', () => {
        zoomLevel = 1;
        panX = 0;
        panY = 0;
        updateTransform(canvas);
        indicator.textContent = '100%';
    });
}

function updateTransform(canvas) {
    canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;
}

// ========== 主题切换 ==========
function initTheme() {
    const btn = document.getElementById('themeToggleBtn');
    if (!btn) return;
    updateThemeIcon();
    
    btn.addEventListener('click', toggleTheme);
    
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            const saved = localStorage.getItem('svg-gallery-theme');
            if (!saved) {
                if (e.matches) {
                    document.documentElement.classList.add('dark-mode');
                } else {
                    document.documentElement.classList.remove('dark-mode');
                }
                updateThemeIcon();
            }
        });
    }
}

function toggleTheme() {
    const isDark = document.documentElement.classList.toggle('dark-mode');
    localStorage.setItem('svg-gallery-theme', isDark ? 'dark' : 'light');
    updateThemeIcon();
}

function updateThemeIcon() {
    const sun = document.getElementById('themeIconSun');
    const moon = document.getElementById('themeIconMoon');
    const isDark = document.documentElement.classList.contains('dark-mode');
    if (sun) sun.style.display = isDark ? 'block' : 'none';
    if (moon) moon.style.display = isDark ? 'none' : 'block';
}

// ========== 工具函数 ==========
function escapeHtml(text) {
    if (text == null) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}