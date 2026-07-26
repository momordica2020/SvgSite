import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

// ========== 全局状态 ==========
let scene, camera, renderer, controls;
let flagMesh = null;
let flagGroup = null;
let poleGroup = null;
let currentTexture = null;
let windSpeed = 3.0;
let currentPoleType = 'modern';
let spearColor = '#8B4513';
let images = []; // 图库数据
let animationId = null;
let time = 0;

// 布料模拟参数
const SEG_X = 30;
const SEG_Y = 20;
let flagWidth = 3;
let flagHeight = 2;

// 顶点原始位置缓存（用于布料模拟）
let originalPositions = null;

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    initScene();
    initTheme();
    loadImages().then(() => {
        setupEventListeners();
        // 尝试从 URL 参数加载 SVG
        const params = new URLSearchParams(window.location.search);
        const svgId = params.get('svg');
        if (svgId) {
            const img = images.find(i => i.id === svgId);
            if (img) loadFlagTexture(`svg/${encodeURIComponent(img.svgFile)}`, img.name);
            document.getElementById('flagImageSelect').value = svgId;
        }
    });
});

// ========== Three.js 场景 ==========
function initScene() {
    const container = document.getElementById('flagCanvasContainer');
    const w = container.clientWidth;
    const h = container.clientHeight;

    // 场景
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x87CEEB);
    scene.fog = new THREE.Fog(0x87CEEB, 20, 80);

    // 相机
    camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 200);
    camera.position.set(4, 2.5, 5);

    // 渲染器
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    renderer.setSize(w, h);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // 控制器
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 1;
    controls.maxDistance = 30;
    controls.target.set(0, 2, 0);
    controls.update();

    // 灯光
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfff5e6, 1.2);
    sunLight.position.set(10, 15, 8);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 0.5;
    sunLight.shadow.camera.far = 50;
    sunLight.shadow.camera.left = -10;
    sunLight.shadow.camera.right = 10;
    sunLight.shadow.camera.top = 10;
    sunLight.shadow.camera.bottom = -10;
    scene.add(sunLight);

    const backLight = new THREE.DirectionalLight(0xffffff, 0.3);
    backLight.position.set(-5, 10, -5);
    scene.add(backLight);

    // 地面
    const groundGeo = new THREE.PlaneGeometry(60, 60);
    const groundMat = new THREE.MeshStandardMaterial({
        color: 0x7cb87c,
        roughness: 0.9,
        metalness: 0.0
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    // 云
    createClouds();

    // 初始旗杆和旗帜
    createPole('modern');
    createFlag();

    // 窗口缩放
    window.addEventListener('resize', onWindowResize);

    // 开始渲染循环
    animate();
}

function createClouds() {
    const cloudGroup = new THREE.Group();
    const cloudMat = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        roughness: 1,
        metalness: 0,
        transparent: true,
        opacity: 0.85
    });

    // 生成若干随机云朵（用多个球体拼成）
    for (let i = 0; i < 8; i++) {
        const cloud = new THREE.Group();
        const numBlobs = 3 + Math.floor(Math.random() * 3);
        for (let j = 0; j < numBlobs; j++) {
            const r = 0.5 + Math.random() * 0.8;
            const blob = new THREE.Mesh(
                new THREE.SphereGeometry(r, 16, 16),
                cloudMat
            );
            blob.position.set(
                (Math.random() - 0.5) * 1.5,
                (Math.random() - 0.5) * 0.4,
                (Math.random() - 0.5) * 0.8
            );
            blob.scale.y = 0.6;
            cloud.add(blob);
        }
        cloud.position.set(
            (Math.random() - 0.5) * 40,
            12 + Math.random() * 8,
            (Math.random() - 0.5) * 40
        );
        cloud.userData.speed = 0.05 + Math.random() * 0.1;
        cloudGroup.add(cloud);
    }
    scene.add(cloudGroup);
    scene.userData.cloudGroup = cloudGroup;
}

function onWindowResize() {
    const container = document.getElementById('flagCanvasContainer');
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
}

// ========== 旗杆创建 ==========
function createPole(type) {
    // 移除旧旗杆
    if (poleGroup) {
        scene.remove(poleGroup);
        poleGroup.traverse(obj => {
            if (obj.geometry) obj.geometry.dispose();
            if (obj.material) obj.material.dispose();
        });
    }

    poleGroup = new THREE.Group();

    switch (type) {
        case 'modern':
            createModernPole();
            break;
        case 'spear':
            createSpearPole();
            break;
        case 'dadun':
            createDadunPole();
            break;
    }

    scene.add(poleGroup);
    currentPoleType = type;

    // 重建旗帜以匹配新旗杆
    if (currentTexture) {
        createFlag();
    }
}

function createModernPole() {
    // 金属杆
    const poleMat = new THREE.MeshStandardMaterial({
        color: 0xC0C0C0,
        roughness: 0.2,
        metalness: 0.9
    });
    const pole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.03, 0.04, 6, 16),
        poleMat
    );
    pole.position.y = 3;
    pole.castShadow = true;
    poleGroup.add(pole);

    // 顶部球
    const ball = new THREE.Mesh(
        new THREE.SphereGeometry(0.06, 16, 16),
        poleMat
    );
    ball.position.y = 6.06;
    poleGroup.add(ball);

    // 底座
    const baseMat = new THREE.MeshStandardMaterial({
        color: 0x696969,
        roughness: 0.5,
        metalness: 0.5
    });
    const base = new THREE.Mesh(
        new THREE.CylinderGeometry(0.15, 0.25, 0.3, 16),
        baseMat
    );
    base.position.y = 0.15;
    base.castShadow = true;
    poleGroup.add(base);
}

function createSpearPole() {
    // 木杆
    const woodMat = new THREE.MeshStandardMaterial({
        color: 0x5C4033,
        roughness: 0.7,
        metalness: 0.0
    });
    const pole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.025, 0.035, 5.5, 16),
        woodMat
    );
    pole.position.y = 2.75;
    pole.castShadow = true;
    poleGroup.add(pole);

    // 套筒
    const sleeveMat = new THREE.MeshStandardMaterial({
        color: spearColor,
        roughness: 0.4,
        metalness: 0.3
    });
    const sleeve = new THREE.Mesh(
        new THREE.CylinderGeometry(0.045, 0.05, 0.8, 16),
        sleeveMat
    );
    sleeve.position.y = 4.4;
    poleGroup.add(sleeve);
    poleGroup.userData.sleeve = sleeve;

    // 矛头
    const spearMat = new THREE.MeshStandardMaterial({
        color: 0xC0C0C0,
        roughness: 0.15,
        metalness: 0.95
    });
    const spearTip = new THREE.Mesh(
        new THREE.ConeGeometry(0.04, 0.35, 16),
        spearMat
    );
    spearTip.position.y = 5.85;
    spearTip.castShadow = true;
    poleGroup.add(spearTip);

    // 红穗（用红色锥体模拟）
    const tasselMat = new THREE.MeshStandardMaterial({
        color: 0xCC0000,
        roughness: 0.9,
        metalness: 0.0
    });
    const tassel = new THREE.Mesh(
        new THREE.ConeGeometry(0.08, 0.3, 8),
        tasselMat
    );
    tassel.position.y = 5.55;
    tassel.rotation.x = Math.PI;
    poleGroup.add(tassel);

    // 底座
    const baseMat = new THREE.MeshStandardMaterial({
        color: 0x4a3728,
        roughness: 0.6,
        metalness: 0.0
    });
    const base = new THREE.Mesh(
        new THREE.CylinderGeometry(0.12, 0.2, 0.25, 16),
        baseMat
    );
    base.position.y = 0.125;
    base.castShadow = true;
    poleGroup.add(base);
}

function createDadunPole() {
    // 竖直木杆（短一些）
    const woodMat = new THREE.MeshStandardMaterial({
        color: 0x8B6914,
        roughness: 0.7,
        metalness: 0.0
    });
    const verticalPole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.03, 0.04, 4, 16),
        woodMat
    );
    verticalPole.position.y = 2;
    verticalPole.castShadow = true;
    poleGroup.add(verticalPole);

    // 横杆
    const horizontalPole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.02, 0.02, 3.2, 16),
        woodMat
    );
    horizontalPole.rotation.z = Math.PI / 2;
    horizontalPole.position.set(0.8, 3.9, 0);
    horizontalPole.castShadow = true;
    poleGroup.add(horizontalPole);

    // 横杆两端装饰球
    const decoMat = new THREE.MeshStandardMaterial({
        color: 0xB8860B,
        roughness: 0.3,
        metalness: 0.6
    });
    const deco1 = new THREE.Mesh(new THREE.SphereGeometry(0.04, 16, 16), decoMat);
    deco1.position.set(2.4, 3.9, 0);
    poleGroup.add(deco1);
    const deco2 = new THREE.Mesh(new THREE.SphereGeometry(0.04, 16, 16), decoMat);
    deco2.position.set(-0.8, 3.9, 0);
    poleGroup.add(deco2);

    // 底座
    const baseMat = new THREE.MeshStandardMaterial({
        color: 0x5C4033,
        roughness: 0.6,
        metalness: 0.0
    });
    const base = new THREE.Mesh(
        new THREE.CylinderGeometry(0.12, 0.2, 0.25, 16),
        baseMat
    );
    base.position.y = 0.125;
    base.castShadow = true;
    poleGroup.add(base);
}

// ========== 旗帜创建 ==========
function createFlag() {
    // 移除旧旗帜
    if (flagMesh) {
        scene.remove(flagMesh);
        flagMesh.geometry.dispose();
        flagMesh.material.dispose();
        flagMesh = null;
    }

    // 根据旗杆类型确定旗帜尺寸和位置
    let flagY, flagX;
    switch (currentPoleType) {
        case 'modern':
            flagWidth = 3;
            flagHeight = 2;
            flagX = 0.03; // 杆半径
            flagY = 5.0; // 杆顶下方
            break;
        case 'spear':
            flagWidth = 2.5;
            flagHeight = 1.8;
            flagX = 0.025;
            flagY = 4.0; // 套筒位置下方
            break;
        case 'dadun':
            flagWidth = 2.4;
            flagHeight = 1.8;
            flagX = 0.8; // 从横杆中间开始
            flagY = 3.9; // 横杆高度
            break;
    }

    // 创建旗帜几何体
    const geometry = new THREE.PlaneGeometry(flagWidth, flagHeight, SEG_X, SEG_Y);

    // 缓存原始顶点位置
    originalPositions = geometry.attributes.position.array.slice();

    // 创建材质
    const material = new THREE.MeshStandardMaterial({
        map: currentTexture,
        side: THREE.DoubleSide,
        roughness: 0.7,
        metalness: 0.0,
        transparent: true,
        alphaTest: 0.01
    });

    flagMesh = new THREE.Mesh(geometry, material);
    flagMesh.castShadow = true;
    flagMesh.receiveShadow = true;

    // 根据旗杆类型设置旗帜位置和旋转
    switch (currentPoleType) {
        case 'modern':
        case 'spear':
            // 竖直挂：旗帜左侧固定在杆上，向右展开
            flagMesh.position.set(flagX + flagWidth / 2, flagY - flagHeight / 2, 0);
            break;
        case 'dadun':
            // 大纛：旗帜顶部固定在横杆上，向下垂
            flagMesh.position.set(flagX, flagY - flagHeight / 2, 0);
            break;
    }

    scene.add(flagMesh);
}

// ========== 布料模拟 ==========
function simulateFlag() {
    if (!flagMesh || !originalPositions) return;

    const positions = flagMesh.geometry.attributes.position.array;
    const timeStep = time * 0.5;

    // 风力系数
    const windFactor = windSpeed * 0.15;
    const gravity = 0.02;

    for (let i = 0; i < positions.length; i += 3) {
        const ix = i / 3;
        const col = ix % (SEG_X + 1);
        const row = Math.floor(ix / (SEG_X + 1));

        // 归一化坐标 (0-1)
        const u = col / SEG_X; // 0=固定边, 1=自由边
        const v = row / SEG_Y; // 0=顶部, 1=底部

        // 原始位置
        const ox = originalPositions[i];
        const oy = originalPositions[i + 1];
        const oz = originalPositions[i + 2];

        let newX = ox;
        let newY = oy;
        let newZ = oz;

        switch (currentPoleType) {
            case 'modern':
            case 'spear': {
                // 竖直挂：左侧(u=0)固定，右侧(u=1)自由
                // 风力随距离固定边的距离增大
                const wave = Math.sin(u * 5 - timeStep * 3) * 0.15 * windFactor * u;
                const wave2 = Math.sin(u * 8 - timeStep * 5 + v * 3) * 0.08 * windFactor * u;
                const wave3 = Math.cos(v * 4 - timeStep * 2) * 0.05 * windFactor * u;
                newZ = oz + wave + wave2;
                newY = oy + wave3 - gravity * u * u;
                // 固定边不移动
                if (u < 0.02) {
                    newX = ox;
                    newY = oy;
                    newZ = oz;
                }
                break;
            }
            case 'dadun': {
                // 大纛：顶部(v=0)固定，底部(v=1)自由
                const wave = Math.sin(v * 4 - timeStep * 2.5) * 0.12 * windFactor * v;
                const wave2 = Math.sin(u * 6 + timeStep * 3) * 0.06 * windFactor * v;
                const wave3 = Math.cos(u * 3 - timeStep * 2) * 0.04 * windFactor * v;
                newZ = oz + wave + wave2;
                newX = ox + wave3;
                newY = oy - gravity * v * 0.5;
                // 顶部固定
                if (v < 0.02) {
                    newX = ox;
                    newY = oy;
                    newZ = oz;
                }
                break;
            }
        }

        positions[i] = newX;
        positions[i + 1] = newY;
        positions[i + 2] = newZ;
    }

    flagMesh.geometry.attributes.position.needsUpdate = true;
    flagMesh.geometry.computeVertexNormals();
}

// ========== 动画循环 ==========
function animate() {
    animationId = requestAnimationFrame(animate);
    time += 0.016;

    // 布料模拟
    simulateFlag();

    // 云的移动
    if (scene.userData.cloudGroup) {
        scene.userData.cloudGroup.children.forEach(cloud => {
            cloud.position.x += cloud.userData.speed * 0.016;
            if (cloud.position.x > 25) cloud.position.x = -25;
        });
    }

    controls.update();
    renderer.render(scene, camera);
}

// ========== 旗面纹理加载 ==========
function loadFlagTexture(src, name) {
    const loader = new THREE.TextureLoader();
    loader.load(
        src,
        (texture) => {
            texture.colorSpace = THREE.SRGBColorSpace;
            texture.minFilter = THREE.LinearFilter;
            texture.magFilter = THREE.LinearFilter;
            currentTexture = texture;
            createFlag();
        },
        undefined,
        (err) => {
            console.error('加载旗面纹理失败:', err);
        }
    );
}

function loadFlagFromFile(file) {
    if (!file) return;

    if (file.type === 'image/svg+xml' || file.name.endsWith('.svg')) {
        // SVG 转 PNG
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const maxSize = 1024;
                const aspect = img.width / img.height;
                if (aspect >= 1) {
                    canvas.width = maxSize;
                    canvas.height = Math.round(maxSize / aspect);
                } else {
                    canvas.height = maxSize;
                    canvas.width = Math.round(maxSize * aspect);
                }
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                loadFlagTexture(canvas.toDataURL('image/png'), file.name);
            };
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
    } else {
        // 直接加载 PNG/JPG
        const reader = new FileReader();
        reader.onload = (e) => {
            loadFlagTexture(e.target.result, file.name);
        };
        reader.readAsDataURL(file);
    }
}

// ========== 图库数据加载 ==========
async function loadImages() {
    try {
        const response = await fetch('data/images.json');
        images = await response.json();
        const select = document.getElementById('flagImageSelect');
        images.forEach(img => {
            const option = document.createElement('option');
            option.value = img.id;
            option.textContent = img.name;
            select.appendChild(option);
        });
    } catch (e) {
        console.error('加载图库数据失败:', e);
    }
}

// ========== 事件监听 ==========
function setupEventListeners() {
    // 旗面选择
    document.getElementById('flagImageSelect').addEventListener('change', (e) => {
        const id = e.target.value;
        if (!id) return;
        const img = images.find(i => i.id === id);
        if (img) {
            loadFlagTexture(`svg/${encodeURIComponent(img.svgFile)}`, img.name);
        }
    });

    // 上传
    document.getElementById('flagUploadInput').addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            loadFlagFromFile(e.target.files[0]);
        }
        e.target.value = '';
    });

    // 旗杆类型
    document.querySelectorAll('#poleTypeGroup .panel-type-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#poleTypeGroup .panel-type-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const type = btn.dataset.pole;
            createPole(type);
            // 显示/隐藏套筒颜色选择
            document.getElementById('spearColorSection').style.display =
                type === 'spear' ? 'flex' : 'none';
        });
    });

    // 套筒颜色
    document.getElementById('spearColorPicker').addEventListener('input', (e) => {
        spearColor = e.target.value;
        document.getElementById('spearColorValue').textContent = spearColor;
        if (poleGroup && poleGroup.userData.sleeve) {
            poleGroup.userData.sleeve.material.color.set(spearColor);
        }
    });

    // 风速
    document.getElementById('windSpeedSlider').addEventListener('input', (e) => {
        windSpeed = parseFloat(e.target.value);
        document.getElementById('windValue').textContent = windSpeed.toFixed(1);
    });

    // 重置视角
    document.getElementById('resetCameraBtn').addEventListener('click', () => {
        camera.position.set(4, 2.5, 5);
        controls.target.set(0, 2, 0);
        controls.update();
    });

    // 面板折叠（移动端）
    document.getElementById('flagPanelToggle').addEventListener('click', () => {
        document.getElementById('flagPanel').classList.toggle('expanded');
    });
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
