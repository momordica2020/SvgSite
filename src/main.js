let images = [];
let currentImage = null;

// 列表状态
const PAGE_SIZE = 120;
let currentPage = 1;
let currentTag = 'all';
let searchQuery = '';
let tagCounts = {};

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
        computeTagCounts();
        renderTags();

        // 从 URL 读取 tag 和 page 参数（用于详情页跳转回来 / 分享链接）
        const params = new URLSearchParams(window.location.search);
        const tag = params.get('tag');
        const page = parseInt(params.get('page'));
        if (tag && tagCounts[tag] !== undefined) {
            currentTag = tag;
        }
        if (page && page > 0) {
            currentPage = page;
        }

        applyFilter();
    } catch (error) {
        console.error('加载图片数据失败:', error);
        images = [];
    }
}

function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', handleSearch);

    // 标签搜索（侧边栏内筛选标签）
    const tagSearchInput = document.getElementById('tagSearchInput');
    if (tagSearchInput) {
        tagSearchInput.addEventListener('input', filterTags);
    }

    // 移动端侧边栏抽屉控制
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', openSidebar);
    }
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', closeSidebar);
    }

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
        // 侧边栏标签按钮（含子元素点击）
        const tagBtn = e.target.closest('.tag-btn');
        if (tagBtn) {
            handleTagClick(tagBtn.dataset.tag);
            return;
        }
        // 分页按钮
        const pageBtn = e.target.closest('.page-btn');
        if (pageBtn && !pageBtn.disabled && !pageBtn.classList.contains('active')) {
            goToPage(parseInt(pageBtn.dataset.page));
            return;
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
            closeSidebar();
        }
    });
}

// 计算每个标签的图片数量（使用 tagsFlat 兼容新格式）
function computeTagCounts() {
    tagCounts = {};
    images.forEach(img => {
        const tags = img.tagsFlat || flattenTags(img.tags) || [];
        tags.forEach(tag => {
            tagCounts[tag] = (tagCounts[tag] || 0) + 1;
        });
    });
}

function renderTags() {
    const tagsList = document.getElementById('tagsList');
    // "全部" 按钮
    const allBtn = `<button class="tag-btn ${currentTag === 'all' ? 'active' : ''}" data-tag="all">
        <span class="tag-btn-name">全部</span>
        <span class="tag-btn-count">${images.length}</span>
    </button>`;

    // 按分类分组渲染标签
    let tagsHtml = '';
    if (typeof TAG_CATEGORIES !== 'undefined') {
        // 按分类分组
        for (const [cat, info] of Object.entries(TAG_CATEGORIES)) {
            // 收集该分类下所有有图片的tag
            const catTags = info.tags
                .filter(t => tagCounts[t] !== undefined)
                .sort((a, b) => tagCounts[b] - tagCounts[a]);
            // 也收集未在预定义列表中但属于该分类的tag（通过TAG_TO_CATEGORY查找）
            // 以及 other 分类中的tag
            if (cat === 'other') {
                const knownTags = new Set();
                for (const c of Object.keys(TAG_CATEGORIES)) {
                    TAG_CATEGORIES[c].tags.forEach(t => knownTags.add(t));
                }
                const otherTags = Object.keys(tagCounts)
                    .filter(t => !knownTags.has(t))
                    .sort((a, b) => tagCounts[b] - tagCounts[a]);
                catTags.push(...otherTags);
            }
            if (catTags.length === 0) continue;

            tagsHtml += `<div class="tag-category" data-category="${cat}">
                <div class="tag-category-header" data-category="${cat}">
                    <span class="tag-category-icon">${info.icon}</span>
                    <span class="tag-category-label">${info.label}</span>
                    <span class="tag-category-toggle">▾</span>
                </div>
                <div class="tag-category-items">`;
            tagsHtml += catTags.map(tag =>
                `<button class="tag-btn ${currentTag === tag ? 'active' : ''}" data-tag="${escapeHtml(tag)}">
                    <span class="tag-btn-name">${escapeHtml(tag)}</span>
                    <span class="tag-btn-count">${tagCounts[tag]}</span>
                </button>`
            ).join('');
            tagsHtml += `</div></div>`;
        }
    } else {
        // 降级：无分类配置时按数量降序
        const sortedTags = Object.keys(tagCounts).sort((a, b) => tagCounts[b] - tagCounts[a]);
        tagsHtml = sortedTags.map(tag =>
            `<button class="tag-btn ${currentTag === tag ? 'active' : ''}" data-tag="${escapeHtml(tag)}">
                <span class="tag-btn-name">${escapeHtml(tag)}</span>
                <span class="tag-btn-count">${tagCounts[tag]}</span>
            </button>`
        ).join('');
    }

    tagsList.innerHTML = allBtn + tagsHtml;

    // 绑定分类折叠/展开
    document.querySelectorAll('.tag-category-header').forEach(header => {
        header.addEventListener('click', () => {
            const cat = header.parentElement;
            cat.classList.toggle('collapsed');
        });
    });
}

// 侧边栏标签搜索筛选
function filterTags() {
    const query = document.getElementById('tagSearchInput').value.toLowerCase();
    document.querySelectorAll('.tags-nav .tag-btn').forEach(btn => {
        const name = btn.querySelector('.tag-btn-name').textContent.toLowerCase();
        btn.style.display = name.includes(query) ? '' : 'none';
    });
    // 搜索时展开所有分类，无搜索词时恢复
    document.querySelectorAll('.tag-category').forEach(cat => {
        if (query) {
            cat.classList.remove('collapsed');
            // 隐藏无匹配子标签的分类
            const hasVisible = Array.from(cat.querySelectorAll('.tag-btn')).some(b => b.style.display !== 'none');
            cat.style.display = hasVisible ? '' : 'none';
        } else {
            cat.style.display = '';
        }
    });
}

// 统一过滤逻辑
function getFilteredItems() {
    return images.filter(img => {
        const matchesSearch = !searchQuery || img.name.toLowerCase().includes(searchQuery);
        const tags = img.tagsFlat || flattenTags(img.tags) || [];
        const matchesTag = currentTag === 'all' || tags.includes(currentTag);
        return matchesSearch && matchesTag;
    });
}

// 应用筛选并渲染（分页 + 图库 + 计数）
function applyFilter() {
    const filtered = getFilteredItems();
    const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

    // 修正越界页码
    if (currentPage > totalPages) currentPage = totalPages;
    if (currentPage < 1) currentPage = 1;

    // 更新标签激活状态
    document.querySelectorAll('.tag-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tag === currentTag);
    });

    // 结果计数
    const resultCount = document.getElementById('resultCount');
    if (resultCount) {
        if (filtered.length === 0) {
            resultCount.textContent = '';
        } else {
            const start = (currentPage - 1) * PAGE_SIZE + 1;
            const end = Math.min(currentPage * PAGE_SIZE, filtered.length);
            resultCount.textContent = `${start}-${end} / 共 ${filtered.length} 张`;
        }
    }

    renderGallery(filtered);
    renderPagination(totalPages);
    updateUrl();
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

    // 仅渲染当前页
    const start = (currentPage - 1) * PAGE_SIZE;
    const pageItems = items.slice(start, start + PAGE_SIZE);

    gallery.innerHTML = pageItems.map(item => {
        const tags = item.tagsFlat || flattenTags(item.tags) || [];
        return `
        <div class="gallery-item" data-id="${escapeHtml(item.id)}">
            <div class="gallery-item-image">
                <img src="svg/${encodeURIComponent(item.svgFile)}" alt="${escapeHtml(item.name)}" loading="lazy">
            </div>
            <div class="gallery-item-info">
                <div class="gallery-item-title">${escapeHtml(item.name)}</div>
                <div class="gallery-item-tags">
                    ${tags.map(tag => `<span class="gallery-item-tag">${escapeHtml(tag)}</span>`).join('')}
                </div>
            </div>
            <button class="gallery-item-detail-btn" data-id="${escapeHtml(item.id)}" title="查看详情">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                    <polyline points="15 3 21 3 21 9"/>
                    <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
            </button>
        </div>`;
    }).join('');
}

// 分页控件
function renderPagination(totalPages) {
    const pagination = document.getElementById('pagination');
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';
    // 上一页
    html += `<button class="page-btn" data-page="${currentPage - 1}" ${currentPage === 1 ? 'disabled' : ''}>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
    </button>`;

    // 页码：显示首尾 + 当前页附近
    const delta = 1;
    const range = [];
    range.push(1);
    for (let i = currentPage - delta; i <= currentPage + delta; i++) {
        if (i > 1 && i < totalPages) range.push(i);
    }
    if (totalPages > 1) range.push(totalPages);

    let prev = 0;
    for (const p of range.sort((a, b) => a - b)) {
        if (p - prev > 1) {
            html += `<span class="page-ellipsis">…</span>`;
        }
        html += `<button class="page-btn ${p === currentPage ? 'active' : ''}" data-page="${p}">${p}</button>`;
        prev = p;
    }

    // 下一页
    html += `<button class="page-btn" data-page="${currentPage + 1}" ${currentPage === totalPages ? 'disabled' : ''}>
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
    </button>`;

    pagination.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    applyFilter();
    // 滚动到图库顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function handleSearch(e) {
    searchQuery = e.target.value.toLowerCase();
    currentPage = 1;
    applyFilter();
}

function handleTagClick(tag) {
    currentTag = tag;
    currentPage = 1;
    applyFilter();
    closeSidebar();
}

// 同步 tag 和 page 到 URL（支持分享链接和详情页返回）
function updateUrl() {
    const params = new URLSearchParams();
    if (currentTag !== 'all') params.set('tag', currentTag);
    if (currentPage > 1) params.set('page', currentPage);
    const qs = params.toString();
    const newUrl = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
    window.history.replaceState(null, '', newUrl);
}

// 侧边栏抽屉控制（移动端）
function openSidebar() {
    document.getElementById('sidebar').classList.add('open');
    document.getElementById('sidebarOverlay').classList.add('active');
}

function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebarOverlay').classList.remove('active');
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
    const tags = currentImage.tagsFlat || flattenTags(currentImage.tags) || [];
    previewTags.innerHTML = tags.map(tag =>
        `<span class="tag" data-tag="${escapeHtml(tag)}" style="cursor: pointer;">${escapeHtml(tag)}</span>`
    ).join('');

    previewSvgImg.src = `svg/${encodeURIComponent(currentImage.svgFile)}`;
    previewSvgImg.alt = currentImage.name;

    // 更新 3D 旗帜链接，携带当前 SVG id
    const flag3dLink = document.getElementById('flag3dLink');
    if (flag3dLink) {
        flag3dLink.href = `flag.html?svg=${encodeURIComponent(currentImage.id)}`;
    }

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