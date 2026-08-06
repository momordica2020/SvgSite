/* Wikimedia Commons SVG detail page */

let svgData = null;
let allSvgs = [];

function getThumbUrl(item, width) {
    width = width || 600;
    if (item.local_file) return item.local_file;
    const fname = item.title.replace('File:', '');
    return `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(fname)}?width=${width}`;
}

function findSvgById(id) {
    if (!svgData) return null;
    // id can be pageid (number) or title (url-encoded)
    const pid = parseInt(id, 10);
    if (!isNaN(pid)) {
        const found = svgData.svgs.find(s => s.pageid === pid);
        if (found) return found;
    }
    const decoded = decodeURIComponent(id);
    return svgData.svgs.find(s => s.title === decoded || s.title === 'File:' + decoded);
}

async function loadDetail() {
    try {
        const resp = await fetch('web/data/commons_svgs.json');
        svgData = await resp.json();
        allSvgs = svgData.svgs || [];

        const params = new URLSearchParams(window.location.search);
        const id = params.get('id');
        if (!id) {
            showError('未指定SVG ID');
            return;
        }

        const item = findSvgById(id);
        if (!item) {
            showError('未找到该SVG: ' + id);
            return;
        }

        renderDetail(item);
    } catch (e) {
        showError('加载失败: ' + e.message);
    }
}

function showError(msg) {
    document.getElementById('detailContent').innerHTML = `<div class="fotw-error"><p>${msg}</p></div>`;
}

function renderDetail(item) {
    const title = item.object_name || item.title.replace('File:', '').replace('.svg', '');
    document.title = `${title} - SVG 详情 - Wikimedia Commons`;
    document.getElementById('crumbTitle').textContent = title;
    document.getElementById('commonsSourceLink').href = item.descriptionurl || item.descriptionshorturl || `https://commons.wikimedia.org/wiki/${encodeURIComponent(item.title.replace(' ','_'))}`;

    const srcUrl = item.local_file ? item.local_file : (item.url || getThumbUrl(item, 1200));
    const thumbUrl = getThumbUrl(item, 800);

    // Categories
    const catHtml = (item.categories || []).map(c => {
        const label = {
            national: '🏳️ 国旗', coat_of_arms: '🛡️ 国徽/纹章', ensign: '⚓ 舰旗',
            naval: '🚢 海军', military: '🎖️ 军事', government: '🏛️ 政府',
            civil: '🏴 民船旗', standard: '👑 元首旗', historical: '📜 历史',
            air_force: '✈️ 空军', coast_guard: '🛟 海警', royal: '👑 王室',
        }[c] || c;
        return `<a href="commons.html?cat=${encodeURIComponent(c)}" class="commons-category-tag">${label}</a>`;
    }).join('');

    // Metadata rows
    const rows = [];
    if (item.artist) rows.push(mkRow('作者', item.artist_html || escapeHtml(item.artist)));
    if (item.date_time) rows.push(mkRow('日期', escapeHtml(item.date_time)));
    if (item.license) {
        const licUrl = item.license_url || '';
        const licText = licUrl ? `<a href="${licUrl}" target="_blank">${escapeHtml(item.license)}</a>` : escapeHtml(item.license);
        rows.push(mkRow('许可', licText));
    }
    if (item.credit) rows.push(mkRow('署名', item.credit_html || escapeHtml(item.credit)));
    if (item.source) rows.push(mkRow('来源', item.source_html || escapeHtml(item.source)));
    if (item.usage_terms) rows.push(mkRow('使用条款', escapeHtml(item.usage_terms)));
    if (item.width && item.height) rows.push(mkRow('尺寸', `${item.width} × ${item.height} px`));
    if (item.size) rows.push(mkRow('文件大小', formatSize(item.size)));

    // Description
    const descHtml = item.description_html || escapeHtml(item.description) || '<em style="color:var(--text-secondary);">无描述</em>';

    // Keywords (link to search)
    const kwHtml = (item.keywords || []).map(k =>
        `<a href="commons.html?q=${encodeURIComponent(k)}" style="display:inline-block;font-size:0.75rem;padding:0.2rem 0.5rem;background:var(--background-color);border-radius:3px;color:var(--text-secondary);text-decoration:none;margin:0.15rem;">${escapeHtml(k)}</a>`
    ).join('');

    // Check for related FOTW flags (simple name match)
    const relatedFotw = findRelatedFotw(item);
    let relatedHtml = '';
    if (relatedFotw.length) {
        relatedHtml = `<div class="commons-related-fotw">
            <h4>🔍 在 FOTW 中查找相关旗帜</h4>
            ${relatedFotw.slice(0, 5).map(c =>
                `<a href="flag.html?code=${encodeURIComponent(c.code)}" style="display:inline-block;font-size:0.8rem;padding:0.25rem 0.6rem;background:var(--fotw-navy);color:white;border-radius:4px;text-decoration:none;margin:0.15rem;">${escapeHtml(c.title || c.code)}</a>`
            ).join('')}
        </div>`;
    }

    document.getElementById('detailContent').innerHTML = `
        <div class="commons-detail-layout">
            <div>
                <div class="commons-svg-viewer">
                    <img src="${srcUrl}" alt="${escapeHtml(title)}"
                         onerror="this.onerror=null;this.src='${thumbUrl}';">
                </div>
                ${item.description || item.description_html ? `
                <div class="commons-meta-card" style="margin-top:1rem;">
                    <h3>📝 描述</h3>
                    <div class="commons-desc">${descHtml}</div>
                </div>` : ''}
            </div>

            <div class="commons-meta-panel">
                <div class="commons-meta-card">
                    <h3>🖼️ 文件信息</h3>
                    <div class="commons-meta-row">
                        <span class="commons-meta-label">标题</span>
                        <span class="commons-meta-value">${escapeHtml(title)}</span>
                    </div>
                    ${rows.join('')}
                </div>

                <div class="commons-meta-card">
                    <h3>🏷️ 分类</h3>
                    <div class="commons-categories-list">${catHtml || '<em style="color:var(--text-secondary);font-size:0.85rem;">未分类</em>'}</div>
                    ${kwHtml ? `<div style="margin-top:0.75rem;">${kwHtml}</div>` : ''}
                    ${relatedHtml}
                </div>

                <div class="commons-meta-card">
                    <h3>🔗 链接与操作</h3>
                    <div class="commons-actions">
                        <a class="commons-action-btn" href="${item.descriptionurl}" target="_blank">📄 查看 Wikimedia 原始页 ↗</a>
                        ${item.url ? `<a class="commons-action-btn secondary" href="${item.url}" target="_blank">⬇️ 下载原始 SVG</a>` : ''}
                        <a class="commons-action-btn secondary" href="commons.html">← 返回 SVG 列表</a>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function mkRow(label, value) {
    return `<div class="commons-meta-row">
        <span class="commons-meta-label">${label}</span>
        <span class="commons-meta-value">${value}</span>
    </div>`;
}

function escapeHtml(s) {
    if (!s) return '';
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + ' KB';
    return (bytes/(1024*1024)).toFixed(2) + ' MB';
}

async function findRelatedFotw(item) {
    try {
        const resp = await fetch('web/data/countries.json');
        const data = await resp.json();
        const countries = data.countries || [];
        // Extract country/entity name from title
        const title = item.object_name || item.title;
        const words = title.replace(/File:|\.svg|Flag of|Coat of arms of|the|flag|of/gi, ' ').trim().toLowerCase().split(/\s+/).filter(w => w.length > 3);
        return countries.filter(c => {
            const t = (c.title || '').toLowerCase();
            return words.some(w => t.includes(w));
        }).slice(0, 5);
    } catch (e) {
        return [];
    }
}

document.addEventListener('DOMContentLoaded', loadDetail);
