// FOTW Flags Encyclopedia - 主索引页JS
(function() {
    'use strict';

    let countriesData = null;
    let categoriesData = null;
    let currentLetter = 'a';
    let currentPage = 1;
    const PAGE_SIZE = 48;
    let currentSearchTerm = '';
    let currentTagFilter = '';  // tag filter: e.g. 'military', 'political', 'sports'
    // Map tab state
    let currentRegion = null;
    let regionPage = 1;
    // Build code->country map
    let countryMap = {};

    // Tag中文显示名映射
    const TAG_LABELS = {
        'national': '🇨🇮 国旗',
        'civil': '民用旗',
        'military': '⚔️ 军旗/武装力量',
        'armed_forces': '武装部队',
        'army': '陆军旗',
        'war_flag': '战旗',
        'air_force': '空军旗',
        'naval': '⚓ 海军旗',
        'maritime': '海事旗',
        'ensign': '船籍旗',
        'war_ensign': '战用船籍旗',
        'coast_guard': '海岸警卫队',
        'merchant': '商船旗',
        'jack': '舰首旗',
        'yacht': '游艇旗',
        'political': '🗳️ 政党/政治',
        'political_party': '政党旗帜',
        'sports': '⚽ 体育旗帜',
        'olympic': '奥林匹克',
        'football': '足球俱乐部',
        'corporate': '🏢 公司/商业',
        'airline': '航空公司',
        'shipping': '航运公司',
        'financial': '金融机构',
        'government': '🏛️ 政府/官方',
        'official': '官方旗帜',
        'historical': '📜 历史旗帜',
        'proposal': '提议旗帜',
        'regional': '🗺️ 地方/行政区',
        'subdivision': '行政区',
        'international': '🌐 国际组织',
        'organization': '国际组织',
        'service': '🚓 公共服务',
        'postal': '邮政旗',
        'cultural': '🎭 文化/民族',
        'ethnic': '民族旗帜',
        'university': '🎓 大学',
        'reported': '报道旗',
        'unofficial': '非官方旗',
        'other': '🏳️ 其他'
    };

    // 主题分类按钮 -> tag 映射
    const SUBJECT_TAG_MAP = {
        'national': 'national',
        'military': 'military',
        'ensign': 'ensign',
        'naval': 'naval',
        'maritime': 'maritime',
        'government': 'government',
        'historical': 'historical',
        'regional': 'regional',
        'organization': 'international',
        'political': 'political',
        'sports': 'sports',
        'corporate': 'corporate',
        'cultural': 'cultural'
    };

    // 将主题标签扩展为相关子标签（如military同时匹配army/war_flag等）
    const TAG_EXPANSIONS = {
        'national': ['national', 'civil'],
        'military': ['military', 'armed_forces', 'army', 'war_flag', 'air_force'],
        'naval': ['naval', 'maritime', 'coast_guard', 'merchant', 'jack', 'yacht', 'war_ensign', 'ensign'],
        'ensign': ['ensign', 'naval', 'maritime', 'war_ensign', 'military', 'coast_guard', 'war_flag'],
        'maritime': ['maritime', 'ensign', 'naval'],
        'government': ['government', 'official', 'service', 'postal'],
        'historical': ['historical', 'proposal', 'reported'],
        'regional': ['regional', 'subdivision'],
        'international': ['international', 'organization'],
        'organization': ['international', 'organization'],
        'political': ['political', 'political_party'],
        'sports': ['sports', 'olympic', 'football'],
        'corporate': ['corporate', 'airline', 'shipping', 'financial'],
        'cultural': ['cultural', 'ethnic', 'university']
    };

    // 图片路径解析：优先PNG，次选GIF
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

    function getCardImage(c) {
        const code = c.code || '';
        const letter = code.charAt(0).toLowerCase();
        // 优先使用main_image
        if (c.main_image) {
            return { png: getImageUrl(c.main_image), gif: getGifUrl(c.main_image) };
        }
        const defaultPath = `images/${letter}/${code}.gif`;
        return { png: getImageUrl(defaultPath), gif: getGifUrl(defaultPath) };
    }

    function getTagEmoji(tags) {
        if (!tags || !tags.length) return '\U0001f3f3\ufe0f';
        const emojiMap = {
            'national': '\U0001f1e8\U0001f1ee', 'military': '\u2694\ufe0f', 'naval': '\u2693', 'ensign': '\U0001f6a2',
            'political': '\U0001f5f3\ufe0f', 'sports': '\u26bd', 'corporate': '\U0001f3e2', 'government': '\U0001f3db\ufe0f',
            'historical': '\U0001f4dc', 'regional': '\U0001f5fa\ufe0f', 'international': '\U0001f310',
            'service': '\U0001f693', 'cultural': '\U0001f3ad', 'organization': '\U0001f310'
        };
        for (const t of tags) {
            if (emojiMap[t]) return emojiMap[t];
        }
        return '\U0001f3f3\ufe0f';
    }

    window.cardImgError = function(img, gifSrc, tagsStr) {
        img.onerror = function() {
            img.style.display = 'none';
            var parent = img.parentElement;
            if (parent && !parent.querySelector('.fotw-card-placeholder')) {
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
                ph.className = 'fotw-card-placeholder';
                ph.innerHTML = '<span style="font-size:2.5rem;">' + emoji + '</span>';
                parent.appendChild(ph);
            }
        };
        img.src = gifSrc;
    };


    // 加载数据
    async function loadData() {
        try {
            const [countriesResp, categoriesResp] = await Promise.all([
                fetch('data/countries.json'),
                fetch('data/categories.json').catch(() => null)
            ]);
            
            if (!countriesResp.ok) throw new Error('数据未就绪');
            countriesData = await countriesResp.json();
            
            // Build country map
            (countriesData.countries || []).forEach(c => {
                countryMap[c.code.toLowerCase()] = c;
            });
            
            if (categoriesResp && categoriesResp.ok) {
                categoriesData = await categoriesResp.json();
            }
            
            initUI();
        } catch (e) {
            document.getElementById('flagGrid').innerHTML = `
                <div class="fotw-empty" style="grid-column:1/-1;">
                    <h3>📦 数据准备中</h3>
                    <p style="margin-top:0.5rem;">FOTW数据集正在下载和解析中（约2.5GB），请稍后刷新页面。</p>
                </div>`;
            document.getElementById('statsText').textContent = '数据未就绪';
            document.getElementById('letterIndex').style.display = 'none';
        }
    }

    function initUI() {
        // 读取URL参数
        const urlParams = new URLSearchParams(window.location.search);
        const tagParam = urlParams.get('tag');
        const qParam = urlParams.get('q');

        const total = countriesData.total;
        document.getElementById('statsText').textContent = `共 ${total.toLocaleString()} 个旗帜条目`;

        renderLetterIndex();
        renderSubjectStats();
        renderFlags();
        renderRegions();

        // Tab切换
        document.querySelectorAll('.fotw-nav-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.fotw-nav-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.fotw-tab-content').forEach(c => c.style.display = 'none');
                tab.classList.add('active');
                const tabId = 'tab-' + tab.dataset.tab;
                document.getElementById(tabId).style.display = 'block';
            });
        });

        // 搜索
        const searchInput = document.getElementById('searchInput');
        let searchTimer;
        searchInput.addEventListener('input', () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => {
                currentSearchTerm = searchInput.value.trim().toLowerCase();
                currentTagFilter = '';  // 搜索时清除tag过滤
                currentPage = 1;
                if (currentSearchTerm) {
                    document.getElementById('letterIndex').style.opacity = '0.3';
                    document.querySelectorAll('.fotw-nav-tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('.fotw-tab-content').forEach(c => c.style.display = 'none');
                    document.querySelector('[data-tab="country"]').classList.add('active');
                    document.getElementById('tab-country').style.display = 'block';
                } else {
                    document.getElementById('letterIndex').style.opacity = '1';
                }
                renderFlags();
            }, 200);
        });

        // 卡片标签点击（事件委托）
        document.getElementById('flagGrid').addEventListener('click', (e) => {
            const tagEl = e.target.closest('.fotw-card-tag');
            if (tagEl) {
                e.preventDefault();
                e.stopPropagation();
                const tag = tagEl.dataset.tag;
                if (tag) showSubject(tag);
            }
        });

        // 如果有URL参数，自动触发搜索/过滤
        if (tagParam && SUBJECT_TAG_MAP[tagParam]) {
            showSubject(tagParam);
        } else if (qParam) {
            searchInput.value = qParam;
            currentSearchTerm = qParam.toLowerCase();
            currentPage = 1;
            document.getElementById('letterIndex').style.opacity = '0.3';
            document.querySelectorAll('.fotw-nav-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.fotw-tab-content').forEach(c => c.style.display = 'none');
            document.querySelector('[data-tab="country"]').classList.add('active');
            document.getElementById('tab-country').style.display = 'block';
            renderFlags();
        }
    }

    function renderSubjectStats() {
        // 更新主题分类按钮的计数（使用扩展后的标签集合统计）
        const allCountries = countriesData.countries || [];
        document.querySelectorAll('[data-subject]').forEach(btn => {
            const subj = btn.dataset.subject;
            const tag = SUBJECT_TAG_MAP[subj];
            if (!tag) return;
            const expanded = TAG_EXPANSIONS[tag] || [tag];
            const expandedSet = new Set(expanded.map(t => t.toLowerCase()));
            const count = allCountries.filter(c =>
                (c.tags || []).some(t => expandedSet.has(t.toLowerCase()))
            ).length;
            let countEl = btn.querySelector('.fotw-subject-count');
            if (!countEl) {
                countEl = document.createElement('span');
                countEl.className = 'fotw-subject-count';
                btn.appendChild(countEl);
            }
            countEl.textContent = count > 0 ? count : '';
        });
    }

    function renderLetterIndex() {
        const container = document.getElementById('letterIndex');
        const letters = 'abcdefghijklmnopqrstuvwxyz'.split('');
        const byLetter = countriesData.by_letter || {};

        container.innerHTML = letters.map(letter => {
            const count = (byLetter[letter] || []).length;
            const isEmpty = count === 0;
            const isActive = letter === currentLetter && !currentSearchTerm && !currentTagFilter;
            return `<button class="fotw-letter-btn ${isEmpty ? 'empty' : ''} ${isActive ? 'active' : ''}"
                data-letter="${letter}" ${isEmpty ? 'disabled' : ''}>
                ${letter.toUpperCase()}
                ${count > 0 ? `<span style="font-size:0.6rem;opacity:0.6;margin-left:1px">${count}</span>` : ''}
            </button>`;
        }).join('');

        container.querySelectorAll('.fotw-letter-btn:not(.empty)').forEach(btn => {
            btn.addEventListener('click', () => {
                currentLetter = btn.dataset.letter;
                currentPage = 1;
                currentSearchTerm = '';
                currentTagFilter = '';
                document.getElementById('searchInput').value = '';
                container.querySelectorAll('.fotw-letter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderFlags();
            });
        });
    }

    function getFilteredCountries() {
        let list = countriesData.countries || [];

        if (currentTagFilter) {
            // Tag过滤（支持子标签扩展）
            const tag = currentTagFilter.toLowerCase();
            const expanded = TAG_EXPANSIONS[tag] || [tag];
            const expandedSet = new Set(expanded.map(t => t.toLowerCase()));
            list = list.filter(c => {
                const tags = (c.tags || []).map(t => t.toLowerCase());
                return tags.some(t => expandedSet.has(t));
            });
        } else if (currentSearchTerm) {
            // 关键词搜索（支持 | 分隔OR）
            const terms = currentSearchTerm.split('|').map(t => t.trim().toLowerCase()).filter(t => t);
            list = list.filter(c => {
                const title = (c.title || '').toLowerCase();
                const code = (c.code || '').toLowerCase();
                const intro = (c.intro || '').toLowerCase();
                const kws = (c.keywords || []).map(k => (k || '').toLowerCase());
                const tags = (c.tags || []).map(t => (t || '').toLowerCase());
                const haystack = title + ' ' + code + ' ' + intro + ' ' + kws.join(' ') + ' ' + tags.join(' ');
                if (terms.length === 0) return true;
                return terms.some(term => haystack.includes(term));
            });
        } else {
            const byLetter = countriesData.by_letter || {};
            list = byLetter[currentLetter] || [];
        }

        return list;
    }

    function renderFlags() {
        const grid = document.getElementById('flagGrid');
        const list = getFilteredCountries();
        const totalPages = Math.ceil(list.length / PAGE_SIZE);
        const start = (currentPage - 1) * PAGE_SIZE;
        const pageItems = list.slice(start, start + PAGE_SIZE);

        // 更新过滤信息提示
        let filterInfo = '';
        if (currentTagFilter) {
            const label = TAG_LABELS[currentTagFilter] || currentTagFilter;
            filterInfo = `<div style="grid-column:1/-1;padding:0.5rem 0;font-size:0.9rem;color:var(--text-secondary);">
                📂 分类: <strong>${label}</strong> - 共 ${list.length} 个条目
                <button onclick="clearFilter()" style="margin-left:1rem;padding:2px 8px;font-size:0.8rem;cursor:pointer;background:transparent;border:1px solid var(--border);border-radius:4px;color:var(--text-secondary);">清除筛选</button>
            </div>`;
        }

        if (pageItems.length === 0) {
            grid.innerHTML = filterInfo + `<div class="fotw-empty" style="grid-column:1/-1;">没有找到匹配的旗帜</div>`;
            document.getElementById('pagination').innerHTML = '';
            return;
        }

        grid.innerHTML = filterInfo + pageItems.map(c => {
            const code = c.code || '';
            const imgs = getCardImage(c);
            const tagBadges = (c.tags || []).slice(0, 3).map(t => {
                const l = TAG_LABELS[t] || t;
                const short = l.replace(/^[^\s]+\s*/, '').trim() || l;
                const subjectTag = ({
                    'civil': 'national', 'armed_forces': 'military', 'army': 'military',
                    'war_flag': 'military', 'air_force': 'military',
                    'maritime': 'naval', 'coast_guard': 'naval', 'merchant': 'naval',
                    'jack': 'naval', 'yacht': 'naval', 'war_ensign': 'ensign',
                    'political_party': 'political', 'olympic': 'sports', 'football': 'sports',
                    'airline': 'corporate', 'shipping': 'corporate', 'financial': 'corporate',
                    'official': 'government', 'service': 'government', 'postal': 'government',
                    'proposal': 'historical', 'reported': 'historical',
                    'subdivision': 'regional', 'organization': 'organization',
                    'ethnic': 'cultural', 'university': 'cultural'
                })[t] || t;
                return `<span class="fotw-card-tag" data-tag="${subjectTag}" style="cursor:pointer;">${short}</span>`;
            }).join('');
            return `<div class="fotw-card" data-code="${code}" style="cursor:pointer;">
                <a href="flag.html?code=${encodeURIComponent(code)}" style="text-decoration:none;color:inherit;display:block;">
                <div class="fotw-card-img">
                    <img src="${imgs.png}" alt="${c.title || code}"
                         onerror="cardImgError(this, '${imgs.gif}', '${(c.tags||[]).join(',')}')">
                </div>
                <div class="fotw-card-name">${c.title || code}</div>
                <div class="fotw-card-code">${code.toUpperCase()}</div>
                </a>
                ${tagBadges ? `<div class="fotw-card-tags">${tagBadges}</div>` : ''}
            </div>`;
        }).join('');

        renderPagination(totalPages, currentPage, 'pagination', (page) => {
            currentPage = page;
            renderFlags();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    function renderPagination(totalPages, page, containerId, onPageChange) {
        const container = document.getElementById(containerId);
        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        let html = '';
        html += `<button class="fotw-page-btn" ${page <= 1 ? 'disabled' : ''} data-page="${page - 1}">‹</button>`;

        const maxVisible = 7;
        let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);
        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            html += `<button class="fotw-page-btn ${i === page ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }

        html += `<button class="fotw-page-btn" ${page >= totalPages ? 'disabled' : ''} data-page="${page + 1}">›</button>`;

        container.innerHTML = html;
        container.querySelectorAll('.fotw-page-btn:not([disabled])').forEach(btn => {
            btn.addEventListener('click', () => {
                const p = parseInt(btn.dataset.page);
                onPageChange(p);
            });
        });
    }

    function renderRegions() {
        const grid = document.getElementById('regionGrid');
        if (!categoriesData || !categoriesData.regions) {
            grid.innerHTML = '<div class="fotw-empty">地区数据加载中...</div>';
            return;
        }

        const regionIcons = {
            'africa': '🌍',
            'americas': '🌎',
            'asia': '🌏',
            'europe': '🏰',
            'oceania': '🏝️',
            'international': '🌐',
            'historical': '📜',
            'other': '🏳️'
        };

        grid.innerHTML = categoriesData.regions.map(r => `
            <div class="fotw-region-card" data-region="${r.code}">
                <div class="fotw-region-icon">${regionIcons[r.code] || '🏳️'}</div>
                <h3>${r.name}</h3>
                <p>${r.count} 个旗帜条目</p>
            </div>
        `).join('');

        grid.querySelectorAll('.fotw-region-card').forEach(card => {
            card.addEventListener('click', () => {
                const regionCode = card.dataset.region;
                showRegion(regionCode);
            });
        });

        document.getElementById('regionBackBtn').addEventListener('click', () => {
            document.getElementById('regionFlagList').style.display = 'none';
            document.getElementById('regionGrid').style.display = 'grid';
            currentRegion = null;
        });
    }

    function showRegion(regionCode) {
        const region = (categoriesData.regions || []).find(r => r.code === regionCode);
        if (!region) return;

        currentRegion = regionCode;
        regionPage = 1;
        document.getElementById('regionGrid').style.display = 'none';
        document.getElementById('regionFlagList').style.display = 'block';
        document.getElementById('regionTitle').textContent = `${region.name}（${region.count} 个）`;

        renderRegionFlags();
    }

    function renderRegionFlags() {
        const region = (categoriesData.regions || []).find(r => r.code === currentRegion);
        if (!region) return;

        const codes = region.codes || [];
        const flags = codes.map(code => countryMap[code.toLowerCase()]).filter(Boolean);
        
        const totalPages = Math.ceil(flags.length / PAGE_SIZE);
        const start = (regionPage - 1) * PAGE_SIZE;
        const pageItems = flags.slice(start, start + PAGE_SIZE);

        const grid = document.getElementById('regionFlags');
        
        if (pageItems.length === 0) {
            grid.innerHTML = `<div class="fotw-empty" style="grid-column:1/-1;">该地区暂无旗帜数据</div>`;
            document.getElementById('regionPagination').innerHTML = '';
            return;
        }

        grid.innerHTML = pageItems.map(c => {
            const code = c.code || '';
            const imgs = getCardImage(c);
            return `<a href="flag.html?code=${encodeURIComponent(code)}" class="fotw-card" data-code="${code}">
                <div class="fotw-card-img">
                    <img src="${imgs.png}" alt="${c.title || code}"
                         onerror="cardImgError(this, '${imgs.gif}', '${(c.tags||[]).join(',')}')">
                </div>
                <div class="fotw-card-name">${c.title || code}</div>
                <div class="fotw-card-code">${code.toUpperCase()}</div>
            </a>`;
        }).join('');

        renderPagination(totalPages, regionPage, 'regionPagination', (page) => {
            regionPage = page;
            renderRegionFlags();
            window.scrollTo({ top: document.getElementById('regionFlagList').offsetTop - 20, behavior: 'smooth' });
        });
    }

    window.showSubject = function(subject) {
        // 主题分类点击：使用tag过滤
        const tag = SUBJECT_TAG_MAP[subject] || subject;
        currentTagFilter = tag;
        currentSearchTerm = '';
        currentPage = 1;
        document.getElementById('searchInput').value = '';
        document.getElementById('letterIndex').style.opacity = '0.3';

        document.querySelectorAll('.fotw-nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.fotw-tab-content').forEach(c => c.style.display = 'none');
        document.querySelector('[data-tab="country"]').classList.add('active');
        document.getElementById('tab-country').style.display = 'block';

        renderFlags();
    };

    window.clearFilter = function() {
        currentTagFilter = '';
        currentSearchTerm = '';
        currentPage = 1;
        document.getElementById('searchInput').value = '';
        document.getElementById('letterIndex').style.opacity = '1';
        renderLetterIndex();
        renderFlags();
    };

    // 初始化
    loadData();
})();
