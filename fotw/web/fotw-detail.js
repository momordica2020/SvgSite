// FOTW Flags Encyclopedia - 详情页JS v2
(function() {
    'use strict';

    function getImageUrl(imgPath) {
        if (!imgPath) return '';
        if (imgPath.startsWith('images/')) {
            return `images-png/${imgPath.slice(7).replace('.gif', '.png')}`;
        }
        return imgPath.replace('.gif', '.png');
    }

    function getGifUrl(imgPath) {
        if (!imgPath) return '';
        return imgPath;
    }

    window.detailImgError = function(img, gifSrc, tagsStr) {
        img.onerror = function() {
            img.style.display = 'none';
            var parent = img.parentElement;
            if (parent && !parent.querySelector('.fotw-detail-img-placeholder')) {
                var tags = tagsStr ? tagsStr.split(',') : [];
                var emoji = '🏳️';
                var emojiMap = {
                    'national': '🇨🇮', 'military': '⚔️', 'naval': '⚓', 'ensign': '🚢',
                    'political': '🗳️', 'sports': '⚽', 'corporate': '🏢', 'government': '🏛️',
                    'historical': '📜', 'regional': '🗺️', 'international': '🌐',
                    'service': '🚓', 'cultural': '🎭', 'organization': '🌐'
                };
                for (var i = 0; i < tags.length; i++) {
                    if (emojiMap[tags[i]]) { emoji = emojiMap[tags[i]]; break; }
                }
                var ph = document.createElement('div');
                ph.className = 'fotw-detail-img-placeholder';
                ph.innerHTML = '<span style="font-size:4rem;">' + emoji + '</span>';
                parent.appendChild(ph);
            }
        };
        img.src = gifSrc;
    };

    function getParam(name) {
        const params = new URLSearchParams(window.location.search);
        return params.get(name);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function renderInlineText(text) {
        if (!text) return '';
        let html = escapeHtml(text);
        html = html.replace(/\{L:([^|}]+)\|([^}]+)\}/g, (match, code, label) => {
            const parts = code.trim().split('#');
            const codeClean = parts[0];
            const anchor = parts[1] ? '#' + parts[1] : '';
            const labelClean = label.trim();
            return `<a href="flag.html?code=${encodeURIComponent(codeClean)}${anchor}">${labelClean}</a>`;
        });
        html = html.replace(/\{A:([^|]+)\|([^}]+)\}/g, (match, anchor, label) => {
            const anchorClean = anchor.trim();
            return `<a href="${anchorClean}" class="fotw-anchor-link">${label.trim()}</a>`;
        });
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        html = html.replace(/^\s*\d+\s*:\s*\d+\s*/, '');
        html = html.replace(/image\s*by\s*[^,.|]*(?:,\s*\d+\s+\w+\s+\d+)?\.?\s*/gi, '');
        html = html.replace(/^\s*by\s+/i, '');
        html = html.replace(/(?:Proportions?|ISO Code|FIPS|MARC Code|IOC Code)\s*:?\s*[^A-Z]*/gi, '');
        html = html.replace(/\s{2,}/g, ' ');
        return html.trim();
    }

    function renderImageBlock(img) {
        if (!img || !img.src) return '';
        const src = img.src;
        const alt = img.alt || src.split('/').pop();
        const imgPng = getImageUrl(src);
        const imgGif = getGifUrl(src);
        const imgId = img.id || '';
        const arrowSvg = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>';
        return `
            <div id="${imgId}" class="fotw-content-image fotw-img-inline">
                <a href="#top" class="fotw-back-to-top" title="回到顶部">${arrowSvg}</a>
                <img src="${imgPng}" alt="${escapeHtml(alt)}"
                     onerror="this.onerror=null;this.src='${imgGif}'">
                ${alt && alt.length < 150 ? `<div class="fotw-img-caption">${renderInlineText(alt)}</div>` : ''}
            </div>`;
    }

    function renderParagraphBlock(text) {
        if (!text) return '';
        const clean = renderInlineText(text);
        if (!clean.trim()) return '';
        return `<p>${clean}</p>`;
    }

    function renderQuoteBlock(text) {
        if (!text) return '';
        const clean = renderInlineText(text);
        return `<blockquote>${clean}</blockquote>`;
    }

    function renderListBlock(items) {
        if (!items || items.length === 0) return '';
        let html = '<ul class="fotw-content-list">';
        for (const item of items) {
            html += `<li>${renderInlineText(item)}</li>`;
        }
        html += '</ul>';
        return html;
    }

    function renderHeadingBlock(block) {
        const level = block.level || 2;
        const text = block.text;
        const anchor = block.anchor || '';
        const safeText = renderInlineText(text);
        const arrowSvg = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>';
        return `<h${level} id="${anchor}" class="fotw-section-heading">
            ${safeText}
            <a href="#top" class="fotw-back-to-top" title="回到顶部">${arrowSvg}</a>
        </h${level}>`;
    }

    function renderContentBlocks(blocks) {
        if (!blocks || blocks.length === 0) return '';
        let html = '';
        let firstImageSkipped = false;
        let clearFloatAdded = false;
        for (const block of blocks) {
            switch (block.type) {
                case 'heading':
                    if (!clearFloatAdded) {
                        html += '<div style="clear:both;"></div>';
                        clearFloatAdded = true;
                    }
                    html += renderHeadingBlock(block);
                    break;
                case 'paragraph':
                    html += renderParagraphBlock(block.text);
                    break;
                case 'image':
                    if (!firstImageSkipped) {
                        firstImageSkipped = true;
                        continue;
                    }
                    html += renderImageBlock(block);
                    break;
                case 'quote':
                    html += renderQuoteBlock(block.text);
                    break;
                case 'list':
                    html += renderListBlock(block.items);
                    break;
                case 'sub_pages':
                    html += '<div class="fotw-sub-pages"><h4>' + escapeHtml(block.title || '相关旗帜') + '</h4><div class="fotw-sub-pages-grid">';
                    for (const link of (block.links || [])) {
                        html += '<a href="flag.html?code=' + encodeURIComponent(link.code) + '" class="fotw-sub-page-link">' + escapeHtml(link.title || link.code) + '</a>';
                    }
                    html += '</div></div>';
                    break;
            }
        }
        return html;
    }

    function renderToc(toc) {
        if (!toc || toc.length === 0) return '';
        let html = '<div class="fotw-toc"><h3>本节目录</h3><ul>';
        for (const item of toc) {
            html += `<li><a href="#${item.anchor}">${escapeHtml(item.text)}</a></li>`;
        }
        html += '</ul></div>';
        return html;
    }

    function renderFlagsIndex(allFlags) {
        if (!allFlags || allFlags.length <= 1) return '';
        let html = '<div class="fotw-flags-index"><h3>本页旗帜</h3><div class="fotw-flags-thumbs">';
        for (let i = 0; i < allFlags.length; i++) {
            const img = allFlags[i];
            const src = img.src;
            const alt = img.alt || src.split('/').pop();
            const imgPng = getImageUrl(src);
            const imgGif = getGifUrl(src);
            html += `
                <a href="#${img.id}" class="fotw-flag-thumb" title="${escapeHtml(alt)}">
                    <img src="${imgPng}" alt="${escapeHtml(alt)}"
                         onerror="this.onerror=null;this.src='${imgGif}'">
                    <span>${i + 1}</span>
                </a>`;
        }
        html += '</div></div>';
        return html;
    }

    function renderLinksList(links, title, limit) {
        if (!links || links.length === 0) return '';
        let html = `<h2 class="fotw-section-heading">${escapeHtml(title)}</h2><ul class="fotw-related-links">`;
        const shown = new Set();
        let count = 0;
        for (const link of links) {
            const code = typeof link === 'string' ? link : link.code;
            const text = typeof link === 'string' ? link : link.title;
            if (!code || shown.has(code)) continue;
            if (code.startsWith('#') || code.startsWith('http') || code.startsWith('mailto:')) continue;
            if (code.endsWith('.pdf') || code.endsWith('.gif') || code.endsWith('.jpg') || code.endsWith('.png')) continue;
            if (code.startsWith('misc/') || code.startsWith('images/')) continue;
            shown.add(code);
            html += `<li><a href="flag.html?code=${encodeURIComponent(code)}">${renderInlineText(text || code)}</a></li>`;
            count++;
            if (limit && count >= limit) break;
        }
        html += '</ul>';
        return count > 0 ? html : '';
    }

    async function loadDetail() {
        const code = getParam('code');
        if (!code) {
            document.getElementById('detailContent').innerHTML = `
                <div class="fotw-empty">
                    <p>未指定旗帜代码</p>
                    <a href="index.html" style="color:var(--fotw-primary);">返回索引</a>
                </div>`;
            return;
        }

        try {
            const resp = await fetch('data/flag_details.json');
            if (!resp.ok) throw new Error('数据未就绪');
            const allDetails = await resp.json();
            const detail = allDetails[code];

            if (!detail) {
                const countriesResp = await fetch('data/countries.json');
                const countries = await countriesResp.json();
                const country = (countries.countries || []).find(c => c.code === code);
                if (country) {
                    renderBasicInfo(country, code);
                } else {
                    document.getElementById('detailContent').innerHTML = `
                        <div class="fotw-empty">
                            <p>未找到旗帜 "${escapeHtml(code)}"</p>
                            <a href="index.html" style="color:var(--fotw-primary);">返回索引</a>
                        </div>`;
                }
                return;
            }

            renderDetail(detail);
        } catch (e) {
            console.error(e);
            document.getElementById('detailContent').innerHTML = `
                <div class="fotw-empty">
                    <h3>📦 数据准备中</h3>
                    <p style="margin-top:0.5rem;">FOTW数据集正在下载和解析中，请稍后刷新页面。</p>
                    <a href="index.html" style="color:var(--fotw-primary);">返回索引</a>
                </div>`;
        }
    }

    function renderBasicInfo(country, code) {
        const letter = code.charAt(0).toLowerCase();
        const mainImg = country.main_image || `images/${letter}/${code}.gif`;
        const imgSrc = getImageUrl(mainImg);
        const gifSrc = getGifUrl(mainImg);
        const tags = country.tags || [];
        document.getElementById('crumbTitle').textContent = country.title || code;
        document.getElementById('detailContent').innerHTML = `
            <div id="top" class="fotw-detail-layout">
                <aside class="fotw-detail-sidebar">
                    <div class="fotw-detail-main-img">
                        <img src="${imgSrc}" alt="${escapeHtml(country.title || code)}"
                             onerror="detailImgError(this, '${gifSrc}', '${(country.tags||[]).join(',')}')">
                    </div>
                    <div class="fotw-detail-info">
                        <h2>${escapeHtml(country.title || code)}</h2>
                        <div class="fotw-detail-meta">代码: ${code.toUpperCase()}</div>
                        ${tags.length > 0 ? `
                        <div class="fotw-detail-tags-section">
                            <div class="fotw-detail-section-label">🏷️ 分类标签</div>
                            <div class="fotw-detail-tags">
                                ${tags.map(t => `<a href="index.html?tag=${encodeURIComponent(mapTagToSubject(t))}" class="fotw-keyword-tag fotw-tag-link">${escapeHtml(tagLabel(t))}</a>`).join('')}
                            </div>
                        </div>` : ''}
                    </div>
                    <a href="../flag.html" class="fotw-3d-btn" target="_blank">
                        🚩 3D飘扬展示
                    </a>
                </aside>
                <div class="fotw-detail-content">
                    <p style="color:var(--text-secondary);">该旗帜的详细页面数据正在解析中，目前仅显示基本信息。</p>
                    <p><a href="index.html">返回旗帜索引</a></p>
                </div>
            </div>`;
    }

    function tagLabel(tag) {
        const labels = {
            'national': '🇨🇮 国旗', 'civil': '民用旗', 'military': '⚔️ 军旗',
            'armed_forces': '武装部队', 'army': '陆军', 'war_flag': '战旗',
            'air_force': '空军', 'naval': '⚓ 海军', 'maritime': '海事',
            'ensign': '船籍旗', 'coast_guard': '海警', 'merchant': '商船',
            'political': '🗳️ 政治', 'political_party': '政党', 'sports': '⚽ 体育',
            'olympic': '奥运', 'corporate': '🏢 公司', 'government': '🏛️ 政府',
            'official': '官方', 'historical': '📜 历史', 'regional': '🗺️ 地方',
            'international': '🌐 国际组织', 'service': '🚓 公共服务',
            'cultural': '🎭 文化', 'ethnic': '民族', 'university': '🎓 大学',
            'yacht': '游艇', 'jack': '舰首旗', 'airline': '航空', 'shipping': '航运',
            'postal': '邮政', 'reported': '报道', 'unofficial': '非官方',
            'subdivision': '行政区', 'proposal': '提议', 'other': '🏳️ 其他'
        };
        return labels[tag] || tag;
    }

    function mapTagToSubject(tag) {
        const map = {
            'national': 'national', 'civil': 'national',
            'military': 'military', 'armed_forces': 'military', 'army': 'military',
            'war_flag': 'military', 'air_force': 'military',
            'naval': 'naval', 'maritime': 'naval', 'coast_guard': 'naval',
            'merchant': 'naval', 'jack': 'naval', 'yacht': 'naval', 'war_ensign': 'naval',
            'ensign': 'ensign',
            'political': 'political', 'political_party': 'political',
            'sports': 'sports', 'olympic': 'sports', 'football': 'sports',
            'corporate': 'corporate', 'airline': 'corporate', 'shipping': 'corporate',
            'government': 'government', 'official': 'government', 'service': 'government',
            'postal': 'government',
            'historical': 'historical', 'proposal': 'historical', 'reported': 'historical',
            'regional': 'regional', 'subdivision': 'regional',
            'organization': 'organization', 'international': 'organization',
            'cultural': 'cultural', 'ethnic': 'cultural', 'university': 'cultural'
        };
        return map[tag] || tag;
    }

    function renderDetail(detail) {
        const code = detail.code;
        const letter = code.charAt(0).toLowerCase();
        document.getElementById('crumbTitle').textContent = detail.title || code;

        const mainImg = detail.main_image || `images/${letter}/${code}.gif`;
        const mainImgSrc = getImageUrl(mainImg);
        const mainGifSrc = getGifUrl(mainImg);

        const tags = detail.tags || [];
        const keywords = detail.keywords || [];

        let sidebarHtml = `
            <div class="fotw-detail-main-img">
                <img src="${mainImgSrc}" alt="${escapeHtml(detail.title || code)}"
                     onerror="detailImgError(this, '${mainGifSrc}', '${(tags||[]).join(',')}')">
            </div>
            <div class="fotw-detail-info">
                <h2>${escapeHtml(detail.title || code)}</h2>
                ${detail.subtitle ? `<div class="fotw-detail-subtitle">${renderInlineText(detail.subtitle)}</div>` : ''}
                <div class="fotw-detail-meta">
                    代码: ${code.toUpperCase()}<br>
                    ${detail.flag_ratio ? `比例: ${detail.flag_ratio}<br>` : ''}
                    ${detail.last_modified ? `更新: ${detail.last_modified}` : ''}
                </div>
                ${detail.editor ? `<div class="fotw-detail-editor">编辑: ${escapeHtml(detail.editor)}</div>` : ''}
                ${tags.length > 0 ? `
                <div class="fotw-detail-tags-section">
                    <div class="fotw-detail-section-label">🏷️ 分类标签</div>
                    <div class="fotw-detail-tags">
                        ${tags.map(t => `<a href="index.html?tag=${encodeURIComponent(mapTagToSubject(t))}" class="fotw-keyword-tag fotw-tag-link">${escapeHtml(tagLabel(t))}</a>`).join('')}
                    </div>
                </div>` : ''}
                ${keywords.length > 0 ? `
                <div class="fotw-detail-tags-section">
                    <div class="fotw-detail-section-label">🔑 关键词</div>
                    <div class="fotw-detail-keywords">
                        ${keywords.map(k => `<a href="index.html?q=${encodeURIComponent(k)}" class="fotw-keyword-tag">${escapeHtml(k)}</a>`).join('')}
                    </div>
                </div>` : ''}
            </div>
            <a href="../flag.html" class="fotw-3d-btn" target="_blank">
                🚩 3D飘扬展示
            </a>`;

        let contentHtml = '';

        contentHtml += renderToc(detail.toc);
        contentHtml += renderFlagsIndex(detail.all_flags);

        if (detail.intro) {
            contentHtml += `<div class="fotw-intro">${renderInlineText(detail.intro)}</div>`;
        }

        contentHtml += renderContentBlocks(detail.content_blocks);

        contentHtml += renderLinksList(detail.see_also, '参见', 20);
        contentHtml += renderLinksList(detail.links, '相关旗帜', 40);

        contentHtml += `<p style="margin-top:2rem;"><a href="index.html">← 返回旗帜索引</a></p>`;

        document.getElementById('detailContent').innerHTML = `
            <div id="top" class="fotw-detail-layout">
                <aside class="fotw-detail-sidebar">${sidebarHtml}</aside>
                <div class="fotw-detail-content">${contentHtml}</div>
            </div>`;

        window.scrollTo(0, 0);
    }

    loadDetail();
})();
