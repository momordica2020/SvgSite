/* Wikimedia Commons SVG list page */

let allSvgs = [];
let filteredSvgs = [];
let currentPage = 1;
const PAGE_SIZE = 48;
let currentCategory = 'all';
let currentSearch = '';

const CATEGORY_LABELS = {
    national: '🏳️ 国旗',
    coat_of_arms: '🛡️ 国徽/纹章',
    ensign: '⚓ 舰旗',
    naval: '🚢 海军',
    military: '🎖️ 军事',
    government: '🏛️ 政府',
    civil: '🏴 民船旗',
    standard: '👑 元首旗',
    historical: '📜 历史',
    air_force: '✈️ 空军',
    coast_guard: '🛟 海警',
    royal: '👑 王室',
    other: '📦 其他',
};

function getThumbUrl(item) {
    // Prefer local file if available
    if (item.local_file) {
        return item.local_file;
    }
    // Use Wikimedia Special:FilePath redirect for remote thumbnails (serves PNG)
    const fname = item.title.replace('File:', '');
    return `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(fname)}?width=400`;
}

function getFullSvgUrl(item) {
    if (item.local_file) return item.local_file;
    return item.url || '';
}

function getCategoryEmoji(cat) {
    const m = {
        coat_of_arms: '🛡️', national: '🏳️', ensign: '⚓', naval: '🚢',
        military: '🎖️', government: '🏛️', civil: '🏴', standard: '👑',
        historical: '📜', air_force: '✈️', coast_guard: '🛟', royal: '👑',
    };
    return m[cat] || '🏴';
}

function truncate(s, n) {
    if (!s) return '';
    s = s.replace(/\s+/g, ' ').trim();
    return s.length > n ? s.slice(0, n-1) + '…' : s;
}

async function loadData() {
    try {
        const resp = await fetch('web/data/commons_svgs.json');
        const data = await resp.json();
        allSvgs = data.svgs || [];
        document.getElementById('statsText').textContent = `共 ${allSvgs.length} 个SVG`;
        applyFilters();
    } catch (e) {
        document.getElementById('svgGrid').innerHTML = `<div class="fotw-error"><p>加载数据失败: ${e.message}</p></div>`;
    }
}

function applyFilters() {
    const q = currentSearch.toLowerCase().trim();
    filteredSvgs = allSvgs.filter(item => {
        if (currentCategory !== 'all') {
            if (!item.categories || !item.categories.includes(currentCategory)) return false;
        }
        if (!q) return true;
        const haystack = [
            item.title, item.object_name, item.description,
            item.artist, item.credit, (item.keywords || []).join(' ')
        ].join(' ').toLowerCase();
        const terms = q.split(/\s+/).filter(t => t);
        return terms.every(t => haystack.includes(t));
    });
    currentPage = 1;
    renderGrid();
}

function renderGrid() {
    const grid = document.getElementById('svgGrid');
    const start = (currentPage - 1) * PAGE_SIZE;
    const pageItems = filteredSvgs.slice(start, start + PAGE_SIZE);
    const totalPages = Math.max(1, Math.ceil(filteredSvgs.length / PAGE_SIZE));

    if (pageItems.length === 0) {
        grid.innerHTML = `<div class="fotw-empty"><p>没有找到匹配的SVG</p><p style="font-size:0.875rem;color:var(--text-secondary);margin-top:0.5rem;">尝试其他关键词或分类</p></div>`;
        document.getElementById('pagination').innerHTML = '';
        document.getElementById('statsText').textContent = `共 ${allSvgs.length} 个SVG · 筛选结果: 0`;
        return;
    }

    grid.innerHTML = pageItems.map(item => {
        const thumb = getThumbUrl(item);
        const cats = (item.categories || []).slice(0, 2);
        const badge = cats.length ? getCategoryEmoji(cats[0]) : '';
        const title = item.object_name || item.title.replace('File:', '').replace('.svg', '');
        const artist = item.artist ? `作者: ${truncate(item.artist, 40)}` : '';
        const license = item.license || '未知许可';
        const tags = cats.map(c => `<span class="commons-card-tag">${CATEGORY_LABELS[c] || c}</span>`).join('');
        const pageid = item.pageid || encodeURIComponent(item.title);
        return `<a class="commons-card" href="commons-detail.html?id=${pageid}">
            <div class="commons-card-img-wrap">
                ${badge ? `<span class="commons-card-badge">${badge}</span>` : ''}
                <img class="commons-card-img" src="${thumb}" alt="${title}" loading="lazy"
                     onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                <div class="commons-card-placeholder" style="display:none;">🖼️</div>
            </div>
            <div class="commons-card-info">
                <h3 class="commons-card-title">${title}</h3>
                ${artist ? `<div class="commons-card-meta">${artist}</div>` : ''}
                <div class="commons-card-tags">${tags}</div>
                <div class="commons-card-license">📜 ${license}</div>
            </div>
        </a>`;
    }).join('');

    // Pagination
    const pag = document.getElementById('pagination');
    if (totalPages > 1) {
        let html = '';
        html += `<button ${currentPage===1?'disabled':''} onclick="gotoPage(${currentPage-1})">‹ 上一页</button>`;
        const range = 2;
        let pages = new Set([1, totalPages]);
        for (let i = currentPage - range; i <= currentPage + range; i++) {
            if (i >= 1 && i <= totalPages) pages.add(i);
        }
        const sorted = [...pages].sort((a,b) => a-b);
        let prev = 0;
        for (const p of sorted) {
            if (p - prev > 1) html += '<span class="fotw-page-ellipsis">…</span>';
            html += `<button class="${p===currentPage?'active':''}" onclick="gotoPage(${p})">${p}</button>`;
            prev = p;
        }
        html += `<button ${currentPage===totalPages?'disabled':''} onclick="gotoPage(${currentPage+1})">下一页 ›</button>`;
        pag.innerHTML = html;
    } else {
        pag.innerHTML = '';
    }

    document.getElementById('statsText').textContent = `共 ${allSvgs.length} 个SVG · 筛选结果: ${filteredSvgs.length}`;
}

function gotoPage(p) {
    const totalPages = Math.max(1, Math.ceil(filteredSvgs.length / PAGE_SIZE));
    if (p < 1 || p > totalPages) return;
    currentPage = p;
    renderGrid();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    loadData();

    // Search
    const searchInput = document.getElementById('searchInput');
    let t;
    searchInput.addEventListener('input', () => {
        clearTimeout(t);
        t = setTimeout(() => {
            currentSearch = searchInput.value;
            applyFilters();
        }, 200);
    });

    // URL param search
    const params = new URLSearchParams(window.location.search);
    const q = params.get('q');
    const cat = params.get('cat');
    if (cat) {
        currentCategory = cat;
        document.querySelectorAll('.fotw-nav-tab').forEach(b => {
            b.classList.toggle('active', b.dataset.cat === cat);
        });
    }
    if (q) {
        searchInput.value = q;
        currentSearch = q;
    }

    // Category tabs
    document.querySelectorAll('.fotw-nav-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.fotw-nav-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentCategory = btn.dataset.cat;
            applyFilters();
        });
    });
});
