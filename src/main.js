let images = [];
let currentImage = null;

// 缩放状态
let zoomLevel = 1;
let panX = 0;
let panY = 0;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;
let zoomHideTimer = null;

document.addEventListener('DOMContentLoaded', () => {
    loadImages();
    setupEventListeners();
    initTheme();
});

async function loadImages() {
    try {
        const response = await fetch('data/images.json');
        images = await response.json();
        renderTags();
        renderGallery(images);

        // 应用 URL 参数中的 tag 筛选（用于详情页跳转回来）
        const params = new URLSearchParams(window.location.search);
        const tag = params.get('tag');
        if (tag) {
            handleTagClick(tag);
        }
    } catch (error) {
        console.error('加载图片数据失败:', error);
        images = [];
    }
}

function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', handleSearch);

    document.addEventListener('click', (e) => {
        // 模态框中的tag点击 - 关闭模态框并筛选该tag
        if (e.target.matches('.preview-tags .tag')) {
            const tag = e.target.dataset.tag;
            if (tag) {
                closeModal();
                handleTagClick(tag);
            }
            return;
        }
        if (e.target.classList.contains('tag-btn')) {
            handleTagClick(e.target.dataset.tag);
        }
        // 阻止gallery-item-detail-btn的点击冒泡到gallery-item
        if (e.target.closest('.gallery-item-detail-btn')) {
            e.stopPropagation();
            const btn = e.target.closest('.gallery-item-detail-btn');
            openDetailPage(btn.dataset.id);
            return;
        }
        if (e.target.closest('.gallery-item')) {
            const item = e.target.closest('.gallery-item');
            openModal(item.dataset.id);
        }
    });

    // SVG下载
    document.getElementById('downloadSvgBtn').addEventListener('click', downloadSvg);

    // PNG三种尺寸下载
    document.querySelectorAll('.download-btn-small').forEach(btn => {
        btn.addEventListener('click', () => {
            downloadPng(parseInt(btn.dataset.size));
        });
    });

    // 查看详情按钮
    document.getElementById('viewDetailBtn').addEventListener('click', () => {
        if (currentImage) {
            openDetailPage(currentImage.id);
        }
    });

    // 缩放和拖拽
    setupZoom();

    // ESC关闭
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
}

function renderTags() {
    const tagsList = document.getElementById('tagsList');
    const allTags = new Set();

    images.forEach(img => {
        img.tags.forEach(tag => allTags.add(tag));
    });

    const sortedTags = Array.from(allTags).sort();

    tagsList.innerHTML = sortedTags.map(tag =>
        `<button class="tag-btn" data-tag="${escapeHtml(tag)}">${escapeHtml(tag)}</button>`
    ).join('');
}

function renderGallery(items) {
    const gallery = document.getElementById('gallery');
    const emptyState = document.getElementById('emptyState');

    if (items.length === 0) {
        gallery.innerHTML = '';
        emptyState.style.display = 'block';
        return;
    }

    emptyState.style.display = 'none';

    gallery.innerHTML = items.map(item => `
        <div class="gallery-item" data-id="${escapeHtml(item.id)}">
            <div class="gallery-item-image">
                <img src="svg/${encodeURIComponent(item.svgFile)}" alt="${escapeHtml(item.name)}" loading="lazy">
            </div>
            <div class="gallery-item-info">
                <div class="gallery-item-title">${escapeHtml(item.name)}</div>
                <div class="gallery-item-tags">
                    ${item.tags.map(tag => `<span class="gallery-item-tag">${escapeHtml(tag)}</span>`).join('')}
                </div>
            </div>
            <button class="gallery-item-detail-btn" data-id="${escapeHtml(item.id)}" title="查看详情">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                    <polyline points="15 3 21 3 21 9"/>
                    <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
            </button>
        </div>
    `).join('');
}

function handleSearch(e) {
    const query = e.target.value.toLowerCase();
    const activeTagBtn = document.querySelector('.tag-btn.active');
    const activeTag = activeTagBtn ? activeTagBtn.dataset.tag : 'all';

    const filtered = images.filter(img => {
        const matchesSearch = img.name.toLowerCase().includes(query);
        const matchesTag = activeTag === 'all' || img.tags.includes(activeTag);
        return matchesSearch && matchesTag;
    });

    renderGallery(filtered);
}

function handleTagClick(tag) {
    document.querySelectorAll('.tag-btn').forEach(btn => btn.classList.remove('active'));
    const targetBtn = document.querySelector(`[data-tag="${tag}"]`);
    if (targetBtn) targetBtn.classList.add('active');

    const searchQuery = document.getElementById('searchInput').value.toLowerCase();

    const filtered = images.filter(img => {
        const matchesSearch = img.name.toLowerCase().includes(searchQuery);
        const matchesTag = tag === 'all' || img.tags.includes(tag);
        return matchesSearch && matchesTag;
    });

    renderGallery(filtered);
}

// ========== 模态框 ==========
function openModal(id) {
    currentImage = images.find(img => img.id === id);
    if (!currentImage) return;

    const modal = document.getElementById('previewModal');
    const previewTitle = document.getElementById('previewTitle');
    const previewTags = document.getElementById('previewTags');
    const previewSvgImg = document.getElementById('previewSvgImg');

    previewTitle.textContent = currentImage.name;
    previewTags.innerHTML = currentImage.tags.map(tag =>
        `<span class="tag" data-tag="${escapeHtml(tag)}" style="cursor: pointer;">${escapeHtml(tag)}</span>`
    ).join('');

    previewSvgImg.src = `svg/${encodeURIComponent(currentImage.svgFile)}`;
    previewSvgImg.alt = currentImage.name;

    // 重置缩放
    resetZoom();

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    const modal = document.getElementById('previewModal');
    modal.classList.remove('active');
    document.body.style.overflow = '';
    currentImage = null;
    resetZoom();
}

function openDetailPage(id) {
    const url = `detail/${id}.html`;
    window.open(url, '_blank');
}

// ========== 缩放与拖拽 ==========
function setupZoom() {
    const wrapper = document.getElementById('previewCanvasWrapper');
    const canvas = document.getElementById('previewCanvas');
    const zoomIndicator = document.getElementById('zoomIndicator');

    if (!wrapper || !canvas) return;

    // 鼠标滚轮缩放
    wrapper.addEventListener('wheel', (e) => {
        if (!currentImage) return;
        e.preventDefault();

        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        const newZoom = Math.max(0.2, Math.min(10, zoomLevel + delta));

        if (newZoom !== zoomLevel) {
            zoomLevel = newZoom;
            updateTransform();
            showZoomIndicator();
        }
    }, { passive: false });

    // 拖拽平移
    wrapper.addEventListener('mousedown', (e) => {
        if (!currentImage) return;
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
        updateTransform();
    });

    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            canvas.style.cursor = '';
            canvas.style.transition = '';
        }
    });

    // 双击重置
    wrapper.addEventListener('dblclick', () => {
        resetZoom();
        showZoomIndicator();
    });
}

function updateTransform() {
    const canvas = document.getElementById('previewCanvas');
    if (canvas) {
        canvas.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomLevel})`;
    }
}

function resetZoom() {
    zoomLevel = 1;
    panX = 0;
    panY = 0;
    updateTransform();
}

function showZoomIndicator() {
    const indicator = document.getElementById('zoomIndicator');
    if (!indicator) return;

    indicator.textContent = `${Math.round(zoomLevel * 100)}%`;
    indicator.classList.add('visible');

    if (zoomHideTimer) clearTimeout(zoomHideTimer);
    zoomHideTimer = setTimeout(() => {
        indicator.classList.remove('visible');
    }, 1500);
}

// ========== 下载 ==========
function downloadSvg() {
    if (!currentImage) return;

    const a = document.createElement('a');
    a.href = `svg/${encodeURIComponent(currentImage.svgFile)}`;
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

    img.src = `svg/${encodeURIComponent(currentImage.svgFile)}`;
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

// 暴露到全局作用域（供HTML inline onclick使用）
window.closeModal = closeModal;
window.openModal = openModal;