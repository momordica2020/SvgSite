import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { extractGIFFrames } from './gifParser.js';

// ========== GIF 动画状态 ==========
let gifAnimation = null; // { frames: [{texture, delay}], currentIndex, lastTime, meshMaterial }
let gifBaseTexture = null;

// ========== 调试接口 ==========
window.__flagDebug = {
    getState: () => {
        if (!particles) return null;
        const total = particles.length / 7;
        let minY = Infinity, maxY = -Infinity;
        let minX = Infinity, maxX = -Infinity;
        let minZ = Infinity, maxZ = -Infinity;
        for (let i = 0; i < total; i++) {
            const idx = i * 7;
            minY = Math.min(minY, particles[idx + 1]);
            maxY = Math.max(maxY, particles[idx + 1]);
            minX = Math.min(minX, particles[idx]);
            maxX = Math.max(maxX, particles[idx]);
            minZ = Math.min(minZ, particles[idx + 2]);
            maxZ = Math.max(maxZ, particles[idx + 2]);
        }
        const w = SEG_X + 1;
        const topRight = (w - 1) * 7;
        const bottomLeft = (SEG_Y * w) * 7;
        const bottomRight = (SEG_Y * w + w - 1) * 7;
        return {
            particleCount: total,
            constraintCount: constraints ? constraints.length : 0,
            windSpeed: windSpeed,
            time: time,
            flagWidth,
            flagHeight,
            bounds: { minX, maxX, minY, maxY, minZ, maxZ },
            corners: {
                topLeft: { x: particles[0], y: particles[1], z: particles[2], pinned: particles[6] },
                topRight: { x: particles[topRight], y: particles[topRight + 1], z: particles[topRight + 2], pinned: particles[topRight + 6] },
                bottomLeft: { x: particles[bottomLeft], y: particles[bottomLeft + 1], z: particles[bottomLeft + 2], pinned: particles[bottomLeft + 6] },
                bottomRight: { x: particles[bottomRight], y: particles[bottomRight + 1], z: particles[bottomRight + 2], pinned: particles[bottomRight + 6] }
            }
        };
    }
};

// ========== 全局状态 ==========
let scene, camera, renderer, controls;
let flagMesh = null;
let flagGroup = null;
let poleGroup = null;
let currentTexture = null;
let windSpeed = 5.0;
let currentPoleType = 'modern';
let sleeveColor = '#ffffff'; // 旗裤/套筒颜色（古代矛杆）
let images = []; // 图库数据
let animationId = null;
let time = 0;

// ========== 设备性能档位（自动检测手机端降级） ==========
const IS_MOBILE = /Android|iPhone|iPad|iPod|Mobile|Touch/i.test(navigator.userAgent)
    || (window.matchMedia && window.matchMedia('(max-width: 768px)').matches)
    || (navigator.maxTouchPoints > 1 && window.innerWidth < 1024);
const QUALITY = IS_MOBILE ? 'low' : 'high';

// 布料模拟参数（低端机降级）
let SEG_X = QUALITY === 'low' ? 60 : 60;
let SEG_Y = QUALITY === 'low' ? 40 : 40;
let flagWidth = 3;
let flagHeight = 2;
let isVerticalHang = false; // true=顶挂向下（大纛，旗面竖着垂下），false=沿旗杆横向展开（金属/矛杆）

// 顶点原始位置缓存（用于布料模拟）
let originalPositions = null;

// 缓存旗杆包围盒
let cachedPoleBox = null;
let poleBoxNeedsUpdate = true;

// ========== 物理布料模拟系统 ==========
// 质点数组：每个质点包含 { x, y, z, px, py, pz, pinned }
let particles = null;
// 约束（弹簧）数组：每个约束 { p1, p2, restLength, type, stiffness }
// type: 'structural'(结构), 'shear'(剪切), 'bend'(弯曲)
let constraints = null;
// 物理模拟参数（低端机：更少迭代）
const PHYSICS_DT = QUALITY === 'low' ? 1 / 40 : 1 / 60;
// 重力
const GRAVITY = 0.15;
// 竖挂时的重力倍数（竖挂时旗面沿旗杆方向，需要更大重力防止被风吹得太高）
const GRAVITY_VERTICAL_MULTIPLIER = 1.0;
// 竖挂时的风力衰减倍数（防止被风吹得太高）
const WIND_VERTICAL_MULTIPLIER = 0.1;
// 粘滞
const DAMPING = 0.999;
// 空气阻力（Blender-style）：对速度施加二次阻尼，遏制惯性钟摆
const AIR_DRAG = 0.15;
const CONSTRAINT_ITERATIONS = QUALITY === 'low' ? 6 : 6;
const PINNED = true;
const UNPINNED = false;

// ========== 材质参数（统一在这里调整） ==========
// 基础粗糙度：值越大越哑光
const FLAG_ROUGHNESS = 0.98;
// 凹凸强度：值越大织物纹理越明显
const FLAG_BUMP_SCALE = 0.0003;
// 透光率：值越大越透光（薄织物效果）
const FLAG_TRANSMISSION = 0.12;
// 折射率：织物大约 1.2-1.4
const FLAG_IOR = 1.45;
// 高光强度：值越小反光越弱
const FLAG_SPECULAR = 0.01;

// ========== 风力参数（统一在这里调整） ==========
// 阵风波动幅度：值越大风速变化越剧烈
const WIND_GUST_AMOUNT = 0.2;
// 湍流强度：值越大乱流越明显，卷动越剧烈
const WIND_TURBULENCE = 1.3;
// 纵向（Z轴）扰动强度：控制前后翻卷
const WIND_Z_TURB = 1.3;
// 垂直（Y轴）扰动强度：控制上下波动
const WIND_Y_TURB = 0.2;
// 风的倾斜角度：负值=从斜上方吹下，正值=从斜下方吹上
const WIND_UPWARD_ANGLE = 0.75;

// ========== 布料刚度参数（统一在这里调整） ==========
// 结构约束：旗面织物不可拉伸，固定为 1.0（硬约束），与 FREEEND_SOFTEN/ROOT_STIFFEN 相乘后仍取 1
const STIFFNESS_STRUCTURAL = 1;
// 剪切约束：控制斜切/弯折变形，值越大越硬挺不可弯折
const STIFFNESS_SHEAR = 0.001;
// 弯曲约束：控制弯折卷曲，值越小越柔软越容易卷
const STIFFNESS_BEND = 0.0005;
// 自由端变软系数：仅作用于剪切/弯曲约束（结构约束保持不可拉伸）
const FREEND_SOFTEN = 1.0;
// 根部变硬系数：仅作用于剪切约束
const ROOT_STIFFEN = 1.8;
// 最大修正量（每次迭代），仅作用于剪切/弯曲约束
const MAX_CORRECTION = 0.33;

// ========== 初始化物理布料系统 ==========
function initClothPhysics() {
    if (!originalPositions) return;

    const totalVertices = (SEG_X + 1) * (SEG_Y + 1);
    
    particles = new Float32Array(totalVertices * 7);
    constraints = [];

    for (let row = 0; row <= SEG_Y; row++) {
        for (let col = 0; col <= SEG_X; col++) {
            const i = row * (SEG_X + 1) + col;
            const particleIdx = i * 7;
            const origIdx = i * 3;

            const ox = originalPositions[origIdx];
            const oy = originalPositions[origIdx + 1];
            const oz = originalPositions[origIdx + 2];

            particles[particleIdx] = ox;
            particles[particleIdx + 1] = oy;
            particles[particleIdx + 2] = oz;
            particles[particleIdx + 3] = ox;
            particles[particleIdx + 4] = oy;
            particles[particleIdx + 5] = oz;
            particles[particleIdx + 6] = 0;
        }
    }

    const w = SEG_X + 1;
    const h = SEG_Y + 1;

    // 结构约束
    for (let row = 0; row < h; row++) {
        for (let col = 0; col < w; col++) {
            const i = row * w + col;
            if (col < w - 1) {
                addConstraint(i, i + 1, 'structural');
            }
            if (row < h - 1) {
                addConstraint(i, i + w, 'structural');
            }
        }
    }
    // 1. 剪切约束（保持不变，它负责对角线抗扭）
    for (let row = 0; row < h - 1; row++) {
        for (let col = 0; col < w - 1; col++) {
            const i = row * w + col;
            addConstraint(i, i + w + 1, 'shear');
            addConstraint(i + 1, i + w, 'shear');
        }
    }

    // 2. 弯曲约束（重构：降低水平锁定，引入对角线弯曲以形成海波层叠）
    for (let row = 0; row < h; row++) {
        for (let col = 0; col < w; col++) {
            const i = row * w + col;
            
            // 水平弯曲：只保留跨度2，去掉跨度4！(让水平方向能够荡起大波浪)
            if (col < w - 2) addConstraint(i, i + 2, 'bend');
            
            // 垂直弯曲：保持跨度2 (允许上下波动)
            if (row < h - 2) addConstraint(i, i + 2 * w, 'bend');
            
            // 对角线弯曲约束（跨度2），这是形成交错卷动和海波层叠感的关键！
            if (row < h - 2 && col < w - 2) {
                addConstraint(i, i + 2 * w + 2, 'bend');
                addConstraint(i + 2, i + 2 * w, 'bend');
            }
        }
    }
    // // 剪切约束（全网格，均匀分布避免边缘抽搐）
    // for (let row = 0; row < h - 1; row++) {
    //     for (let col = 0; col < w - 1; col++) {
    //         const i = row * w + col;
    //         addConstraint(i, i + w + 1, 'shear');
    //         addConstraint(i + 1, i + w, 'shear');
    //     }
    // }

    // // 弯曲约束（多种跨度，水平方向更强，保持旗面展开）
    // for (let row = 0; row < h; row++) {
    //     for (let col = 0; col < w; col++) {
    //         const i = row * w + col;
    //         // 水平方向弯曲约束（更密，保持旗面展开）
    //         if (col < w - 2) addConstraint(i, i + 2, 'bend');
    //         if (col < w - 4) addConstraint(i, i + 4, 'bend');
    //         // 垂直方向弯曲约束（均匀分布）
    //         if (row < h - 2) addConstraint(i, i + 2 * w, 'bend');
    //     }
    // }

    pinVerticesByType();
    
    console.log('Cloth physics initialized:', {
        particles: particles.length / 7,
        constraints: constraints.length
    });
}

function addConstraint(i, j, type) {
    const idx1 = i * 7;
    const idx2 = j * 7;
    const dx = particles[idx1] - particles[idx2];
    const dy = particles[idx1 + 1] - particles[idx2 + 1];
    const dz = particles[idx1 + 2] - particles[idx2 + 2];
    
    const restLength = Math.sqrt(dx * dx + dy * dy + dz * dz);
    if (restLength < 0.005) return;

    const w = SEG_X + 1;
    const col1 = i % w;
    const col2 = j % w;
    const row1 = Math.floor(i / w);
    const row2 = Math.floor(j / w);

    // 根据挂法选择使用列方向（横挂）还是行方向（竖挂）来计算刚度衰减
    const avgCol = (col1 + col2) / 2 / SEG_X;
    const minCol = Math.min(col1, col2) / SEG_X;
    const avgRow = (row1 + row2) / 2 / SEG_Y;
    const minRow = Math.min(row1, row2) / SEG_Y;

    // 竖挂时以行方向（顶部固定、底部自由）作为刚度衰减主方向
    const useAvg = isVerticalHang ? avgRow : avgCol;
    const useMin = isVerticalHang ? minRow : minCol;

    let baseStiffness;
    if (type === 'structural') baseStiffness = STIFFNESS_STRUCTURAL;
    else if (type === 'shear') baseStiffness = STIFFNESS_SHEAR;
    else baseStiffness = STIFFNESS_BEND;

    let stiffness;
    if (type === 'structural') {
        // 结构约束：硬约束（不可拉伸），不应用自由端/根部系数
        stiffness = 1.0;
    } else {
        // 金属杆模式下：靠近旗杆的第一列约束保持高刚度（模拟绷紧的绳索）
        const isNearPole = (currentPoleType === 'modern' && (col1 === 0 || col2 === 0));
        if (isNearPole) {
            stiffness = baseStiffness * 2.5; // 第一列加硬
        } else {
            // 剪切/弯曲约束：可按位置变化
            // 旗尾快速衰减：前15%保持刚度，之后急剧衰减
            const t = useAvg;
            const smooth = t < 0.15 ? 1.0 : (t > 0.5 ? 0.0 : 1.0 - Math.pow((t - 0.15) / 0.35, 1.5));
            const softFactor = 1.0 - FREEND_SOFTEN * (1.0 - smooth);
            // 根部加强：仅剪切约束
            const rootFactor = 1.0 + (ROOT_STIFFEN - 1.0) * Math.max(0, 1.0 - useMin * 2.0);
            stiffness = baseStiffness * softFactor * (type === 'shear' ? rootFactor : 1.0);
        }
    }

    // 是否硬约束（结构约束）：求解时不做 MAX_CORRECTION 截断，完全消除拉伸
    //const isRigid = (type === 'structural') ? 1 : 0;
    const isRigid = 0;
    constraints.push({ i, j, restLength, type, stiffness, isRigid });
}

// 检查并修复 NaN 和 Infinity 值
function fixNaNValues() {
    if (!particles) return false;
    let fixed = false;
    const totalParticles = particles.length / 7;
    let fixCount = 0;
    
    console.log('fixNaNValues called, totalParticles:', totalParticles);
    
    for (let i = 0; i < totalParticles; i++) {
        const idx = i * 7;
        for (let j = 0; j < 6; j++) {
            const val = particles[idx + j];
            if (!isFinite(val)) {
                fixed = true;
                fixCount++;
                console.error('Found invalid value at particle', i, 'offset', j, ':', val);
                // 重置到原始位置
                if (originalPositions) {
                    const origIdx = i * 3;
                    particles[idx] = originalPositions[origIdx];
                    particles[idx + 1] = originalPositions[origIdx + 1];
                    particles[idx + 2] = originalPositions[origIdx + 2];
                    particles[idx + 3] = originalPositions[origIdx];
                    particles[idx + 4] = originalPositions[origIdx + 1];
                    particles[idx + 5] = originalPositions[origIdx + 2];
                } else {
                    particles[idx] = 0;
                    particles[idx + 1] = 0;
                    particles[idx + 2] = 0;
                    particles[idx + 3] = 0;
                    particles[idx + 4] = 0;
                    particles[idx + 5] = 0;
                }
            }
        }
    }
    console.log('fixNaNValues result: fixed=' + fixed + ', fixCount=' + fixCount);
    if (fixCount > 0) {
        console.error('Fixed', fixCount, 'invalid values in particles');
    }
    return fixed;
}

function pinVerticesByType() {
    const w = SEG_X + 1;
    const h = SEG_Y + 1;

    if (currentPoleType === 'modern') {
        // 金属旗杆：仅使用两个角进行硬连接约束（绳索悬挂）
        pinParticle(0);               // 左上角
        pinParticle((h - 1) * w);     // 左下角
    } else if (currentPoleType === 'spear') {
        // 矛杆：整条左边固定（第一列）
        for (let row = 0; row < h; row++) {
            pinParticle(row * w);
        }
    } else if (currentPoleType === 'dadun') {
        // 大纛：顶部左右两个角固定（顶挂）
        pinParticle(0);                         // 左上角
        pinParticle(w - 1);                     // 右上角
        // 顶部整条也固定，保持横杆形状
        for (let col = 1; col < w - 1; col++) {
            pinParticle(col);
        }
    }
}

function pinParticle(i) {
    particles[i * 7 + 6] = 1; // 标记为固定
}

function unpinAllParticles() {
    for (let i = 0; i < particles.length; i += 7) {
        particles[i + 6] = 0;
    }
}

// 预热布料：让它在重力作用下稳定到自然下垂状态
function settleCloth() {
    if (!particles) return;
    
    const dt = PHYSICS_DT;
    const dtSq = dt * dt;
    const totalParticles = particles.length / 7;
    const settleIterations = 15; // 预热迭代次数（减少以加快加载）
    const settleConstraintIterations = 2; // 预热时使用更少的约束迭代
    
    for (let step = 0; step < settleIterations; step++) {
        // Verlet 积分（仅重力，无风）
        for (let i = 0; i < totalParticles; i++) {
            const idx = i * 7;
            if (particles[idx + 6]) continue;
            
            const x = particles[idx];
            const y = particles[idx + 1];
            const z = particles[idx + 2];
            const px = particles[idx + 3];
            const py = particles[idx + 4];
            const pz = particles[idx + 5];
            
            // 仅重力，逐渐增加（竖挂时使用更大重力）
            const gravityFactor = step < 5 ? 0.3 : (step < 10 ? 0.6 : 1.0);
            const settleGravity = isVerticalHang ? GRAVITY * GRAVITY_VERTICAL_MULTIPLIER : GRAVITY;
            const ay = -settleGravity * gravityFactor;
            
            const newX = x + (x - px) * DAMPING;
            const newY = y + (y - py) * DAMPING + ay * dtSq;
            const newZ = z + (z - pz) * DAMPING;
            
            particles[idx + 3] = x;
            particles[idx + 4] = y;
            particles[idx + 5] = z;
            particles[idx] = newX;
            particles[idx + 1] = newY;
            particles[idx + 2] = newZ;
        }
        
        // 约束求解（使用更少的迭代）
        for (let iter = 0; iter < settleConstraintIterations; iter++) {
            for (let c = 0; c < constraints.length; c++) {
                const constraint = constraints[c];
                const idx1 = constraint.i * 7;
                const idx2 = constraint.j * 7;
                
                const pinned1 = particles[idx1 + 6];
                const pinned2 = particles[idx2 + 6];
                
                if (pinned1 && pinned2) continue;
                
                const x1 = particles[idx1];
                const y1 = particles[idx1 + 1];
                const z1 = particles[idx1 + 2];
                const x2 = particles[idx2];
                const y2 = particles[idx2 + 1];
                const z2 = particles[idx2 + 2];
                
                const dx = x2 - x1;
                const dy = y2 - y1;
                const dz = z2 - z1;
                const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
                
                if (dist < 0.0001) continue;
                
                let stiffness = 1.0;
                if (constraint.type === 'shear') stiffness = 0.3;
                if (constraint.type === 'bend') stiffness = 0.05;
                
                let diff = (dist - constraint.restLength) / dist;
                // 预热阶段：结构约束也走硬约束，避免初始下垂时拉伸
                if (constraint.type !== 'structural') {
                    const maxDiff = 0.05 / Math.max(constraint.restLength, 0.01);
                    if (Math.abs(diff) > maxDiff) {
                        diff = Math.sign(diff) * maxDiff;
                    }
                }
                const offsetX = dx * 0.5 * diff * stiffness;
                const offsetY = dy * 0.5 * diff * stiffness;
                const offsetZ = dz * 0.5 * diff * stiffness;
                
                if (!pinned1) {
                    particles[idx1] += offsetX;
                    particles[idx1 + 1] += offsetY;
                    particles[idx1 + 2] += offsetZ;
                }
                if (!pinned2) {
                    particles[idx2] -= offsetX;
                    particles[idx2 + 1] -= offsetY;
                    particles[idx2 + 2] -= offsetZ;
                }
            }
        }
    }
    
    // 同步到 Three.js 网格
    if (flagMesh) {
        const positions = flagMesh.geometry.attributes.position.array;
        for (let i = 0; i < totalParticles; i++) {
            const idx = i * 7;
            const posIdx = i * 3;
            positions[posIdx] = particles[idx];
            positions[posIdx + 1] = particles[idx + 1];
            positions[posIdx + 2] = particles[idx + 2];
        }
        flagMesh.geometry.attributes.position.needsUpdate = true;
        flagMesh.geometry.computeVertexNormals();
    }
}

// 重置布料到初始状态
function resetClothToInitialState() {
    if (!particles || !originalPositions) return;
    
    const totalVertices = (SEG_X + 1) * (SEG_Y + 1);
    for (let i = 0; i < totalVertices; i++) {
        const idx = i * 7;
        const origIdx = i * 3; // originalPositions 是每个顶点 3 个值 (x,y,z)
        const ox = originalPositions[origIdx];
        const oy = originalPositions[origIdx + 1];
        const oz = originalPositions[origIdx + 2];
        
        particles[idx] = ox;
        particles[idx + 1] = oy;
        particles[idx + 2] = oz;
        particles[idx + 3] = ox;
        particles[idx + 4] = oy;
        particles[idx + 5] = oz;
    }
    
    // 重新标记固定点
    unpinAllParticles();
    pinVerticesByType();
}

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
            if (img) {
                document.getElementById('flagSearchInput').value = img.name;
                loadFlagTexture(`svg/${encodeURIComponent(img.svgFile)}`, img.name);
            }
        }
        // 从 URL 参数加载旗面方向
        const orient = params.get('orient');
        if (orient) {
            const validOrients = ['normal', 'rotateCW', 'rotateCCW', 'rotate180', 'flipH', 'flipV', 'flipHV', 'rotateCW_flipH', 'rotateCCW_flipH', 'rotate180_flipH'];
            if (validOrients.includes(orient)) {
                document.getElementById('flagOrientationSelect').value = orient;
                flagOrientation = orient;
            }
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
    scene.background = new THREE.Color(0x1a1a2e);

    // 相机
    camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 200);
    camera.position.set(3, 5, 6);
    camera.lookAt(1.56, 3, 0);

    // 渲染器
    // 低端机：关闭抗锯齿、阴影、降低像素比，大幅减少 GPU 负担
    renderer = new THREE.WebGLRenderer({
        antialias: true,
        //antialias: QUALITY !== 'low',
        alpha: false,
        powerPreference: QUALITY === 'low' ? 'low-power' : 'high-performance'
    });
    renderer.setSize(w, h);
    // 低端机最高 1x 像素比，高端机最高 2x
    renderer.setPixelRatio(QUALITY === 'low' ? 1 : Math.min(window.devicePixelRatio, 2));
    //renderer.shadowMap.enabled = QUALITY !== 'low';
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = QUALITY === 'low' ? THREE.BasicShadowMap : THREE.PCFSoftShadowMap;
    container.appendChild(renderer.domElement);

    // 控制器
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 1;
    controls.maxDistance = 30;
    controls.target.set(1.56, 4, 0);
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

    // 天空球（KTX2 HDR 真实天空）
    createSkyDome();

    // 云
    //createClouds();

    // 初始旗杆和旗帜
    createPole('modern');
    createFlag();

    // 窗口缩放
    window.addEventListener('resize', onWindowResize);

    // 开始渲染循环
    animate();
}

// function createClouds() {
//     const cloudGroup = new THREE.Group();
//     const cloudMat = new THREE.MeshStandardMaterial({
//         color: 0xffffff,
//         roughness: 1,
//         metalness: 0,
//         transparent: true,
//         opacity: 0.85
//     });

//     // 生成若干随机云朵（用多个球体拼成）
//     for (let i = 0; i < 8; i++) {
//         const cloud = new THREE.Group();
//         const numBlobs = 3 + Math.floor(Math.random() * 3);
//         for (let j = 0; j < numBlobs; j++) {
//             const r = 0.5 + Math.random() * 0.8;
//             const blob = new THREE.Mesh(
//                 new THREE.SphereGeometry(r, 16, 16),
//                 cloudMat
//             );
//             blob.position.set(
//                 (Math.random() - 0.5) * 1.5,
//                 (Math.random() - 0.5) * 0.4,
//                 (Math.random() - 0.5) * 0.8
//             );
//             blob.scale.y = 0.6;
//             cloud.add(blob);
//         }
//         cloud.position.set(
//             (Math.random() - 0.5) * 40,
//             12 + Math.random() * 8,
//             (Math.random() - 0.5) * 40
//         );
//         cloud.userData.speed = 0.05 + Math.random() * 0.1;
//         cloudGroup.add(cloud);
//     }
//     scene.add(cloudGroup);
//     scene.userData.cloudGroup = cloudGroup;
// }

// ========== 天空球（KTX2 HDR 真实天空） ==========
function createSkyDome() {
    createFallbackSky();
}

function createFallbackSky() {
    const w = 2048, h = 1024;
    const canvas = document.createElement('canvas');
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0.00, '#0d3b6e');
    grad.addColorStop(0.35, '#2f6fb2');
    grad.addColorStop(0.52, '#6aa8dd');
    grad.addColorStop(0.62, '#a8cbe8');
    grad.addColorStop(0.70, '#d9ecf7');
    grad.addColorStop(0.78, '#eef6fb');
    grad.addColorStop(1.00, '#f4f8fa');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, w, h);
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    // 低端机：减少天球分段（24x16 顶点数 1/4）
    const skyGeo = new THREE.SphereGeometry(95, QUALITY === 'low' ? 24 : 48, QUALITY === 'low' ? 16 : 32);
    const skyMat = new THREE.MeshBasicMaterial({
        map: texture,
        side: THREE.BackSide,
        fog: false,
        depthWrite: false
    });
    const sky = new THREE.Mesh(skyGeo, skyMat);
    sky.renderOrder = -10;
    scene.add(sky);
}

// ========== 织物纹理（自然、低对比度，避免鱼鳞锯齿） ==========
let fabricGrainTexture = null;

function makeNoise2D(seed) {
    const perm = new Uint8Array(512);
    const p = new Uint8Array(256);
    for (let i = 0; i < 256; i++) p[i] = i;
    let s = seed;
    for (let i = 255; i > 0; i--) {
        s = (s * 16807 + 0) % 2147483647;
        const j = s % (i + 1);
        [p[i], p[j]] = [p[j], p[i]];
    }
    for (let i = 0; i < 512; i++) perm[i] = p[i & 255];
    const fade = t => t * t * t * (t * (t * 6 - 15) + 10);
    const lerp = (a, b, t) => a + t * (b - a);
    const grad = (h, x, y) => {
        const u = (h & 1) === 0 ? x : y;
        const v = (h & 1) === 0 ? y : x;
        return ((h & 2) === 0 ? u : -u) + ((h & 2) === 0 ? v : -v);
    };
    // 3D 噪声：在 2D 基础上增加 z（=time）维
    return (x, y, z) => {
        const X = Math.floor(x) & 255;
        const Y = Math.floor(y) & 255;
        const Z = Math.floor(z) & 255;
        x -= Math.floor(x);
        y -= Math.floor(y);
        z -= Math.floor(z);
        const u = fade(x);
        const v = fade(y);
        const w = fade(z);
        const A = perm[X] + Y;
        const AA = perm[A] + Z;
        const AB = perm[A + 1] + Z;
        const B = perm[X + 1] + Y;
        const BA = perm[B] + Z;
        const BB = perm[B + 1] + Z;
        return lerp(
            lerp(
                lerp(grad(perm[AA], x, y, z), grad(perm[BA], x - 1, y, z), u),
                lerp(grad(perm[AB], x, y - 1, z), grad(perm[BB], x - 1, y - 1, z), u),
                v
            ),
            lerp(
                lerp(grad(perm[AA + 1], x, y, z - 1), grad(perm[BA + 1], x - 1, y, z - 1), u),
                lerp(grad(perm[AB + 1], x, y - 1, z - 1), grad(perm[BB + 1], x - 1, y - 1, z - 1), u),
                v
            ),
            w
        );
    };
}

// 风力专用噪声（X/Y/Z 三向，3D 时空噪声）
const windNoiseX = makeNoise2D(7919);
const windNoiseY = makeNoise2D(4093);
const windNoiseZ = makeNoise2D(1601);

function fbm(noise, x, y, octaves) {
    let val = 0, amp = 0.5, freq = 1;
    for (let i = 0; i < octaves; i++) {
        val += noise(x * freq, y * freq) * amp;
        amp *= 0.5;
        freq *= 2.0;
    }
    return val;
}

function getFabricGrainTexture() {
    if (fabricGrainTexture) return fabricGrainTexture;

    // 低端机：256x256 替代 512x512（生成耗时 1/4，纹理采样开销 1/4）
    const size = QUALITY === 'low' ? 512 : 512;
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d');
    const img = ctx.createImageData(size, size);
    const d = img.data;

    const noise1 = makeNoise2D(42);
    const noise2 = makeNoise2D(137);
    const noise3 = makeNoise2D(73);

    for (let y = 0; y < size; y++) {
        for (let x = 0; x < size; x++) {
            const idx = (y * size + x) * 4;
            const nx = x / size;
            const ny = y / size;

            const f1 = fbm(noise1, nx * 3, ny * 3, 3);
            const f2 = fbm(noise2, nx * 8 + 5.3, ny * 8 + 2.1, 2);

            const fabricVar = f1 * 0.6 + f2 * 0.4;

            const warpX = fbm(noise3, nx * 1.2, ny * 1.2, 2) * 0.15;

            const threadFreq = 24;
            const threadX = Math.sin((nx + warpX) * threadFreq * Math.PI) * 0.5 + 0.5;
            const threadY = Math.cos((ny + warpX * 0.6) * threadFreq * Math.PI) * 0.5 + 0.5;
            const weave = Math.min(threadX, threadY) * 2 - 1;

            const micro = (Math.random() - 0.5) * 0.01;

            let v = 128 + fabricVar * 12 + weave * 4 + micro * 4;
            v = Math.max(112, Math.min(144, v));
            d[idx] = d[idx + 1] = d[idx + 2] = v;
            d[idx + 3] = 255;
        }
    }
    ctx.putImageData(img, 0, 0);

    const texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(10, 6);
    // 低端机用 1x 各向异性（避免额外的 mipmap 采样）
    texture.anisotropy = QUALITY === 'low' ? 4 : 8;
    texture.colorSpace = THREE.SRGBColorSpace;
    fabricGrainTexture = texture;
    return texture;
}

// 创建默认纹理（蓝色旗面）
function getDefaultFlagTexture() {
    const size = 512;
    const canvas = document.createElement('canvas');
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext('2d');
    
    // 蓝色渐变背景
    const gradient = ctx.createLinearGradient(0, 0, size, size);
    gradient.addColorStop(0, '#1e3a5f');
    gradient.addColorStop(0.5, '#2d5a87');
    gradient.addColorStop(1, '#1e3a5f');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
    
    // 添加一些装饰性图案
    ctx.strokeStyle = 'rgba(255, 215, 0, 0.6)';
    ctx.lineWidth = 8;
    ctx.beginPath();
    ctx.moveTo(100, 100);
    ctx.lineTo(412, 412);
    ctx.stroke();
    
    ctx.beginPath();
    ctx.moveTo(412, 100);
    ctx.lineTo(100, 412);
    ctx.stroke();
    
    // 添加边框
    ctx.strokeStyle = '#ffd700';
    ctx.lineWidth = 16;
    ctx.strokeRect(30, 30, size - 60, size - 60);
    
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
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

    // 标记旗杆包围盒需要更新
    poleBoxNeedsUpdate = true;

    // 重建旗帜以匹配新旗杆（无论是否有自定义纹理，都需要重新固定粒子）
    if (flagMesh) {
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

    // ---- 滑轮与旗绳（软性绳索悬挂系统，无旗裤） ----
    const hardwareMat = new THREE.MeshStandardMaterial({
        color: 0x8a8a8a,
        roughness: 0.35,
        metalness: 0.85
    });
    // 顶部滑轮（横放的小滚轮 + 护壳）
    const pulley = new THREE.Mesh(
        new THREE.CylinderGeometry(0.035, 0.035, 0.025, 16),
        hardwareMat
    );
    pulley.rotation.z = Math.PI / 2;
    pulley.position.set(0.05, 5.98, 0);
    poleGroup.add(pulley);
    const pulleyShell = new THREE.Mesh(
        new THREE.BoxGeometry(0.035, 0.09, 0.06),
        hardwareMat
    );
    pulleyShell.position.set(0.038, 5.97, 0);
    poleGroup.add(pulleyShell);

    // 旗绳：从底部绳夹贯穿至顶部滑轮
    const ropeMat = new THREE.MeshStandardMaterial({
        color: 0xd8cfc0,
        roughness: 0.9,
        metalness: 0.0
    });
    const ropeTop = 5.98;
    const ropeBottom = 0.55;
    const rope = new THREE.Mesh(
        new THREE.CylinderGeometry(0.007, 0.007, ropeTop - ropeBottom, 8),
        ropeMat
    );
    rope.position.set(0.058, (ropeTop + ropeBottom) / 2, 0);
    poleGroup.add(rope);

    // 底部绳夹
    const cleat = new THREE.Mesh(
        new THREE.BoxGeometry(0.05, 0.07, 0.05),
        hardwareMat
    );
    cleat.position.set(0.045, 0.52, 0);
    poleGroup.add(cleat);

    // 旗帜上下角的金属扣环（位置与旗面挂点一致）
    const ringGeo = new THREE.TorusGeometry(0.018, 0.005, 8, 16);
    const ringTop = new THREE.Mesh(ringGeo, hardwareMat);
    ringTop.position.set(0.058, 5.92, 0);
    ringTop.rotation.y = Math.PI / 2;
    poleGroup.add(ringTop);
    // const ringBottom = new THREE.Mesh(ringGeo, hardwareMat);
    // ringBottom.position.set(0.058, 3.92, 0);
    // ringBottom.rotation.y = Math.PI / 2;
    // poleGroup.add(ringBottom);

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
    // 木杆（高度匹配金属旗杆，旗面顶端在 y=5.92）
    const woodMat = new THREE.MeshStandardMaterial({
        color: 0x5C4033,
        roughness: 0.7,
        metalness: 0.0
    });
    const poleHeight = 6.0;
    const pole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.045, 0.045, poleHeight, 16),
        woodMat
    );
    pole.position.y = poleHeight / 2 + 0.15;
    pole.castShadow = true;
    pole.userData.poleCore = true; // 标记为参与碰撞检测的旗杆主体
    poleGroup.add(pole);

    // 矛头（金属三棱刃，紧贴红缨上方）
    const spearMat = new THREE.MeshStandardMaterial({
        color: 0xC0C0C0,
        roughness: 0.15,
        metalness: 0.95
    });
    const spearTip = new THREE.Mesh(
        new THREE.ConeGeometry(0.05, 0.62, 16),
        spearMat
    );
    
    spearTip.position.y = poleHeight+0.4;
    spearTip.castShadow = true;
    poleGroup.add(spearTip);

    // 矛头基座（连接处套环）
    const spearBase = new THREE.Mesh(
        new THREE.CylinderGeometry(0.032, 0.1, 0.04, 16),
        spearMat
    );
    spearBase.position.y = poleHeight+0.2;
    poleGroup.add(spearBase);

    // 红缨（紧贴矛头下方、旗面顶端之上）
    const tasselMat = new THREE.MeshStandardMaterial({
        color: 0xB30000,
        roughness: 0.95,
        metalness: 0.0
    });
    // 红缨核心（细小红球体）
    const tasselCore = new THREE.Mesh(
        new THREE.SphereGeometry(0.1, 12, 12),
        tasselMat
    );
    tasselCore.scale.set(1, 0.5, 1);
    tasselCore.position.y = poleHeight + 0.15;
    poleGroup.add(tasselCore);
    // 红缨流苏（向四周发散的多束细锥体）
    for (let i = 0; i < 32; i++) {
        const angle = (i / 32) * Math.PI * 2;
        const strand = new THREE.Mesh(
            new THREE.ConeGeometry(0.05, 0.26, 6),
            tasselMat
        );
        strand.position.set(
            Math.cos(angle) * 0.08,
            poleHeight+0.05,
            Math.sin(angle) * 0.08
        );
        strand.rotation.y = -angle - Math.PI / 2;
        strand.rotation.z = 0.3;
        poleGroup.add(strand);
    }

    // 旗裤（套筒）：套在旗帜左侧，高度 = 旗面高度
    // 旗面 anchorY=5.92，height=2，垂直范围 3.92~5.92
    const sleeveMat = new THREE.MeshStandardMaterial({
        color: sleeveColor,
        roughness: 0.6,
        metalness: 0.0
    });
    const sleeve = new THREE.Mesh(
        new THREE.CylinderGeometry(0.055, 0.055, 2, 16),
        sleeveMat
    );
    sleeve.position.set(0.006, 4.92, 0); // 旗裤垂直居中于旗面
    poleGroup.add(sleeve);
    poleGroup.userData.sleeve = sleeve;

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
    // 竖直木杆（高度匹配金属旗杆）
    const dx = -0.7;
    const woodMat = new THREE.MeshStandardMaterial({
        color: 0x8B6914,
        roughness: 0.7,
        metalness: 0.0
    });
    const verticalPoleHeight = 6.3;
    const verticalPole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.03, 0.04, verticalPoleHeight, 16),
        woodMat
    );
    verticalPole.position.x = dx;
    verticalPole.position.y = verticalPoleHeight / 2 + 0.15;
    verticalPole.castShadow = true;
    verticalPole.userData.poleCore = true; // 标记为参与碰撞检测的旗杆主体
    poleGroup.add(verticalPole);

    // ---- 横杆：位于旗面顶端 y=5.92，长度覆盖旗面宽度 ----
    // 旗面 anchorX=0.058，slotWidth=3 → 旗面从 x≈0 到 x≈3
    // 横杆居中放置 x 范围 = [-0.5, 3.5]，长度 4.0
    const horizontalLength = 4.0;
    const horizontalCenterX = 1.5;
    const horizontalY = 5.92;
    const horizontalPole = new THREE.Mesh(
        new THREE.CylinderGeometry(0.022, 0.022, horizontalLength, 16),
        woodMat
    );
    horizontalPole.rotation.z = Math.PI / 2;
    horizontalPole.position.set(horizontalCenterX+dx, horizontalY, 0);
    horizontalPole.castShadow = true;
    horizontalPole.userData.poleCore = true; // 标记为参与碰撞检测的旗杆主体
    poleGroup.add(horizontalPole);


    // ---- 斜拉绳：竖杆顶部到横杆两端的两个三角支撑 ----
    const ropeMat = new THREE.MeshStandardMaterial({
        color: 0xc9a877,
        roughness: 0.95,
        metalness: 0.0
    });
    const poleTopY = verticalPoleHeight + 0.15;
    // 竖杆顶（x=0, y=6.45）到横杆左端（x=-0.5, y=5.92）
    addDiagonalRope(dx, poleTopY, 0, horizontalCenterX - horizontalLength / 2+dx, horizontalY, 0, ropeMat);
    // 竖杆顶（x=0, y=6.45）到横杆右端（x=3.5, y=5.92）
    addDiagonalRope(dx, poleTopY, 0, horizontalCenterX + horizontalLength / 2+dx, horizontalY, 0, ropeMat);

    // 端装饰球
    const decoMat = new THREE.MeshStandardMaterial({
        color: 0xB8860B,
        roughness: 0.3,
        metalness: 0.6
    });
    const deco1 = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 16), decoMat);
    deco1.position.set(horizontalCenterX + horizontalLength / 2+dx, horizontalY, 0);
    poleGroup.add(deco1);
    const deco2 = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 16), decoMat);
    deco2.position.set(horizontalCenterX - horizontalLength / 2+dx, horizontalY, 0);
    poleGroup.add(deco2);
    const deco3 = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 16), decoMat);
    deco3.position.set(dx, poleTopY, 0);
    poleGroup.add(deco3);

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
    base.position.x = dx;
    base.position.y = 0.125;
    base.castShadow = true;
    poleGroup.add(base);
}

// 在两点之间生成一根斜拉绳（CylinderGeometry 自动按方向定位）
function addDiagonalRope(x1, y1, z1, x2, y2, z2, material) {
    const dx = x2 - x1, dy = y2 - y1, dz = z2 - z1;
    const length = Math.sqrt(dx * dx + dy * dy + dz * dz);
    const rope = new THREE.Mesh(
        new THREE.CylinderGeometry(0.008, 0.008, length, 6),
        material
    );
    rope.position.set((x1 + x2) / 2, (y1 + y2) / 2, (z1 + z2) / 2);
    // 默认圆柱沿 Y 轴，需要旋转到指向目标方向
    const axis = new THREE.Vector3(0, 1, 0);
    const dir = new THREE.Vector3(dx, dy, dz).normalize();
    const quat = new THREE.Quaternion().setFromUnitVectors(axis, dir);
    rope.quaternion.copy(quat);
    rope.castShadow = true;
    poleGroup.add(rope);
}

// ========== 旗帜创建 ==========
function createFlag() {
    // 移除旧旗帜
    if (flagMesh) {
        scene.remove(flagMesh);
        if (flagMesh.material.map && !gifBaseTexture) {
            flagMesh.material.map.dispose();
        }
        flagMesh.geometry.dispose();
        flagMesh.material.dispose();
        flagMesh = null;
    }

    // 根据旗杆类型确定旗帜槽位（最大可容纳尺寸）与挂点参考位置
    let slotWidth, slotHeight, anchorX, anchorY;
    switch (currentPoleType) {
        case 'modern':
            slotWidth = 3;
            slotHeight = 2;
            anchorX = 0.058; // 旗绳位置（软性绳索悬挂，无旗裤）
            anchorY = 5.92;  // 旗面顶端挂点（杆顶滑轮处）
            isVerticalHang = false;
            break;
        case 'spear':
            // 古代矛杆：旗帜尺寸与挂高与金属旗杆一致
            slotWidth = 3;
            slotHeight = 2;
            anchorX = 0.058;
            anchorY = 5.92;
            isVerticalHang = false;
            break;
        case 'dadun':
            // 大纛：旗帜尺寸与金属旗杆一致，顶挂向下
            slotWidth = 3;
            slotHeight = 2;
            anchorX = 0.058;
            anchorY = 5.92;
            isVerticalHang = true;
            break;
    }

    // ---- 根据纹理原图宽高比决定旗面实际尺寸与对齐方式（不拉伸） ----
    // 比率 = 原图宽 / 原图高；阈值 3/2
    //  比率 < 3/2（窄高图）：以高度 = 槽位高度，宽度按比例缩小 → 水平居中放置
    //  比率 > 3/2（宽扁图）：以宽度 = 槽位宽度，高度按比例缩小 → 沿旗杆方向靠上
    let originalAspect = 1;
    if (originalSourceImage) {
        const w = originalSourceImage.naturalWidth || originalSourceImage.width || originalSourceImage.videoWidth;
        const h = originalSourceImage.naturalHeight || originalSourceImage.height || originalSourceImage.videoHeight;
        if (w && h) originalAspect = w / h;
    } else if (currentTexture && currentTexture.image) {
        const img = currentTexture.image;
        const w = img.naturalWidth || img.width || img.videoWidth;
        const h = img.naturalHeight || img.height || img.videoHeight;
        if (w && h) originalAspect = w / h;
    }

    const has90rotation = ORIENTATION_HAS_90[flagOrientation] || false;
    // 90度旋转后，展示宽高比 = 原始宽高比的倒数
    const aspect = has90rotation ? (1 / originalAspect) : originalAspect;

    const THRESHOLD = 3 / 2;
    let meshCenterX, meshCenterY;
    if (isVerticalHang) {
         // 大纛顶挂：旗面顶部 y 固定在 anchorY（横杆高度）
        if (aspect < THRESHOLD) {
            flagHeight = slotHeight;
            flagWidth = slotHeight * aspect;
        } else {
            flagWidth = slotWidth;
            flagHeight = slotWidth / aspect;
        }
        // 旗帜左边缘对齐横杆左端装饰球位置（x = horizontalCenterX - horizontalLength/2）
        const leftEdgeX = 1.5 - 4.0 / 2; // = -0.5
        meshCenterX = leftEdgeX + flagWidth / 2;
        const topEdgeY = anchorY;
        meshCenterY = topEdgeY - flagHeight / 2;
    } else {
        if (aspect < THRESHOLD) {
            // 窄高：以槽位高度为基准，水平居中（左右留白）
            flagHeight = slotHeight;
            flagWidth = slotHeight * aspect;
        } else {
            // 宽扁：以槽位宽度为基准，沿旗杆方向靠上
            flagWidth = slotWidth;
            flagHeight = slotWidth / aspect;
        }
        // 竖挂：贴杆的左边缘 x 固定在 anchorX
        const leftEdgeX = anchorX;
        meshCenterX = leftEdgeX + flagWidth / 2;
        // 顶端 y 固定在 anchorY
        const topEdgeY = anchorY;
        meshCenterY = topEdgeY - flagHeight / 2;
    }

    // 动态网格分辨率：根据物理尺寸自适应，保持单位长度粒子密度一致
    const particlesPerMeter = QUALITY === 'low' ? 20 : 20;
    SEG_X = Math.max(8, Math.round(flagWidth * particlesPerMeter));
    SEG_Y = Math.max(8, Math.round(flagHeight * particlesPerMeter));

    // 创建旗帜几何体
    const geometry = new THREE.PlaneGeometry(flagWidth, flagHeight, SEG_X, SEG_Y);

    // 缓存原始顶点位置
    originalPositions = geometry.attributes.position.array.slice();

    // 使用纹理或默认纹理
    let textureToUse = currentTexture;
    if (!textureToUse) {
        textureToUse = getDefaultFlagTexture();
        if (textureToUse.image) {
            originalSourceImage = textureToUse.image;
        }
    }
    
    // 创建材质：低端机用 MeshStandardMaterial 避免 transmission 的高开销
    const grain = getFabricGrainTexture();
    const material = QUALITY === 'low'
        ? new THREE.MeshStandardMaterial({
            map: textureToUse,
            side: THREE.DoubleSide,
            roughness: FLAG_ROUGHNESS,
            roughnessMap: grain,
            metalness: 0.0,
            bumpMap: grain,
            bumpScale: FLAG_BUMP_SCALE,
            transparent: true,
            alphaTest: 0.01,
            flatShading: false
        })
        : new THREE.MeshPhysicalMaterial({
            map: textureToUse,
            side: THREE.DoubleSide,
            roughness: FLAG_ROUGHNESS,
            roughnessMap: grain,
            metalness: 0.0,
            bumpMap: grain,
            bumpScale: FLAG_BUMP_SCALE,
            transparent: true,
            alphaTest: 0.01,
            flatShading: false,
            transmission: FLAG_TRANSMISSION,
            ior: FLAG_IOR,
            thickness: 0.015,
            attenuationColor: new THREE.Color(0xffffff),
            attenuationDistance: 0.8,
            specularIntensity: FLAG_SPECULAR,
            specularColor: new THREE.Color(0x888888)
        });

    flagMesh = new THREE.Mesh(geometry, material);
    // 低端机无阴影投射/接收
    flagMesh.castShadow = QUALITY !== 'low';
    flagMesh.receiveShadow = QUALITY !== 'low';

    // 旗面位置（已根据纹理原图比例与对齐规则计算）
    flagMesh.position.set(meshCenterX, meshCenterY, 0);

    scene.add(flagMesh);

    // 应用旗面方向变换
    applyFlagOrientation();

    // 初始化物理布料系统
    initClothPhysics();
    
    // 立即同步物理位置到几何体
    if (particles) {
        const positions = flagMesh.geometry.attributes.position.array;
        const totalParticles = particles.length / 7;
        for (let i = 0; i < totalParticles; i++) {
            const idx = i * 7;
            const posIdx = i * 3;
            positions[posIdx] = particles[idx];
            positions[posIdx + 1] = particles[idx + 1];
            positions[posIdx + 2] = particles[idx + 2];
        }
        flagMesh.geometry.attributes.position.needsUpdate = true;
        flagMesh.geometry.computeVertexNormals();
    }
}

// ========== 布料模拟（基于 Verlet 积分的真实物理模拟） ==========
function simulateFlag() {
    if (!flagMesh || !particles) return;

    const positions = flagMesh.geometry.attributes.position.array;
    const dt = PHYSICS_DT;
    const dtSq = dt * dt;
    const timeStep = time * 1.2;
    const totalParticles = particles.length / 7;

    // ---- 阵风模型 ----
    const gust =
        1.0 +
        (Math.sin(timeStep * 0.35) * 0.18 +
        Math.sin(timeStep * 0.97 + 1.7) * 0.12 +
        Math.sin(timeStep * 2.3 + 4.2) * 0.08 +
        Math.sin(timeStep * 4.7 + 2.8) * 0.05 +
        Math.sin(timeStep * 8.3 + 6.1) * 0.03) * WIND_GUST_AMOUNT;
    const gustClamped = Math.max(0.15, Math.min(1.8, gust));
    const windStrength = windSpeed * 0.9 * gustClamped;

    // ---- Verlet 积分：更新质点位置 ----
    const wIdx = SEG_X + 1;
    for (let i = 0; i < totalParticles; i++) {
        const idx = i * 7;
        if (particles[idx + 6]) continue;

        const x = particles[idx];
        const y = particles[idx + 1];
        const z = particles[idx + 2];
        const px = particles[idx + 3];
        const py = particles[idx + 4];
        const pz = particles[idx + 5];

        const col = i % wIdx;
        const row = Math.floor(i / wIdx);
        const u = col / SEG_X;
        const v = row / SEG_Y;

        // 根据挂法选择使用 u(横挂/左端固定) 还是 v(竖挂/顶端固定) 来分布风力
        const freeFactor = isVerticalHang ? v : u;

        let ax = 0;
        const gravityForce = isVerticalHang ? GRAVITY * GRAVITY_VERTICAL_MULTIPLIER : GRAVITY;
        let ay = -gravityForce;
        let az = 0;

        // 竖挂时按风力衰减倍数缩放 windStrength（不增加重力，避免惯性过大）
        const effectiveWindStrength = isVerticalHang
            ? windStrength * WIND_VERTICAL_MULTIPLIER
            : windStrength;

        if (effectiveWindStrength > 0.01) {
            // 用 3D 时空噪声（位置 + 时间）作为风力基础，让每个粒子有真正独立的扰动
            // 产生局部孤立褶皱，而不是整面齐步走
            // 将粒子实际世界 Y/Z 坐标混入噪声输入，使旗面卷曲移动时采样到不同噪声区域
            // 从而打破基于网格坐标的规律条纹，产生时空交错的湍流
            const physU = u * flagWidth;
            const physV = v * flagHeight;
            const t = timeStep * 0.6;
            // 三层噪声叠加：低频大褶皱 + 中频卷动 + 高频细节，旗尾频率更高
            const tailBoost = 1.0 + freeFactor * 1.5;
            const nX = windNoiseX(physU * 1.5 + z * 0.8, physV * 1.5 + y * 0.6, t) * 0.5
                     + windNoiseX(physU * 3.5 + z * 1.2, physV * 2.5 + y * 1.0, t * 1.4) * 0.3
                     + windNoiseX(physU * 7.0 * tailBoost + z * 2.0, physV * 5.0 + y * 1.5, t * 2.2) * 0.2;
            const nY = windNoiseY(physU * 1.8 + z * 0.7, physV * 1.2 + y * 0.5, t * 0.9) * 0.5
                     + windNoiseY(physU * 4.0 + z * 1.1, physV * 2.0 + y * 0.9, t * 1.6) * 0.3
                     + windNoiseY(physU * 8.0 * tailBoost + z * 1.8, physV * 4.5 + y * 1.3, t * 2.5) * 0.2;
            const nZ = windNoiseZ(physU * 1.6 + z * 0.9, physV * 1.4 + y * 0.7, t * 1.1) * 0.5
                     + windNoiseZ(physU * 3.8 + z * 1.3, physV * 2.3 + y * 1.1, t * 1.5) * 0.3
                     + windNoiseZ(physU * 7.5 * tailBoost + z * 2.2, physV * 4.8 + y * 1.6, t * 2.3) * 0.2;

            // ---- 风的自遮蔽（基于局部法线 vs 主风向） ----
            // 用相邻 4 个粒子的位置估算局部法线。风向以 X 正向为主。
            // 法线与风向夹角 > 90°（背风面）→ 大幅衰减；前缘/迎风面 → 满风
            let occlusion = 1.0;
            if (col > 0 && col < SEG_X && row > 0 && row < SEG_Y) {
                const iL = (row * wIdx + (col - 1)) * 7;
                const iR = (row * wIdx + (col + 1)) * 7;
                const iU = ((row - 1) * wIdx + col) * 7;
                const iD = ((row + 1) * wIdx + col) * 7;
                const dxU = particles[iR] - particles[iL];
                const dyU = particles[iR + 1] - particles[iL + 1];
                const dzU = particles[iR + 2] - particles[iL + 2];
                const dxV = particles[iD] - particles[iU];
                const dyV = particles[iD + 1] - particles[iU + 1];
                const dzV = particles[iD + 2] - particles[iU + 2];
                // 叉积得局部法线
                let nx = dyU * dzV - dzU * dyV;
                let ny = dzU * dxV - dxU * dzV;
                let nz = dxU * dyV - dyU * dxV;
                const nLen = Math.sqrt(nx * nx + ny * ny + nz * nz);
                if (nLen > 1e-6) {
                    nx /= nLen; ny /= nLen; nz /= nLen;
                    // 风向 = (1, 0, 0) + 一点 Y 向上风
                    const windDirX = 1.0;
                    const windDirY = 0.25;
                    const windDirZ = 0.0;
                    const wLen = Math.sqrt(windDirX * windDirX + windDirY * windDirY + windDirZ * windDirZ);
                    const dot = (nx * windDirX + ny * windDirY + nz * windDirZ) / wLen;
                    // dot > 0: 迎风面（法线与风向同向），满风
                    // dot < 0: 背风面（法线与风向反向），风被完全吸收
                    occlusion = Math.max(0, dot);
                }
            }

            // 主风力集中在自由端（freeFactor 让根部稳，自由端展开）
            const windForce = effectiveWindStrength * (0.25 + 0.75 * freeFactor) * occlusion;
            // X 方向：恒定主风向 + 噪声扰动（噪声让相邻粒子真正独立）
            const windX = (1.0 + nX) * windForce;

            // 扰动因子（近杆端 1.0 → 自由端 0.1）
            // 让空气扰动集中在近旗杆侧，自由端自身扰动微弱，主要由近侧通过约束"拽着"运动
            const disturbFactor = 1.0 - 1 * freeFactor;

            // Z 方向：近杆端有强湍流（拽着旗面动），旗尾保留适度湍流使其自然翻卷
            const windZ = nZ * windForce * WIND_Z_TURB * (0.6 + 0.4 * freeFactor);
            // Y 方向扰动集中在近杆端，自由端保持几乎被动的自然漂浮
            const windY = (
                WIND_UPWARD_ANGLE * (0.2 + 0.8 * Math.sqrt(freeFactor)) +
                nY * 0.5 * disturbFactor
            ) * effectiveWindStrength * (0.3 + 0.7 * disturbFactor) * WIND_Y_TURB * disturbFactor;
            
            az += windZ;
            ax += windX;
            ay += windY;
        }

        // Verlet 积分
        let velX = (x - px) * DAMPING;
        let velY = (y - py) * DAMPING;
        let velZ = (z - pz) * DAMPING;

        // 空气阻力（Blender-style）：对速度施加二次阻尼，遏制惯性钟摆
        const velMag = Math.sqrt(velX * velX + velY * velY + velZ * velZ);
        if (velMag > 0.001) {
            const dragFactor = Math.max(0, 1 - AIR_DRAG * velMag);
            velX *= dragFactor;
            velY *= dragFactor;
            velZ *= dragFactor;
        }

        // 速度限制
        const velMagSq = velX * velX + velY * velY + velZ * velZ;
        const MAX_VEL = 3.0;
        const maxDisp = MAX_VEL * dt;
        if (velMagSq > maxDisp * maxDisp) {
            const velMag = Math.sqrt(velMagSq);
            const scale = maxDisp / velMag;
            velX *= scale;
            velY *= scale;
            velZ *= scale;
        }

        // 计算新位置
        let newX = x + velX + ax * dtSq;
        let newY = y + velY + ay * dtSq;
        let newZ = z + velZ + az * dtSq;

        // 位置限制（防止极端值）
        const MAX_POS = 6;
        if (newX > MAX_POS) newX = MAX_POS;
        if (newX < -MAX_POS) newX = -MAX_POS;
        if (newY > MAX_POS) newY = MAX_POS;
        if (newY < -MAX_POS) newY = -MAX_POS;
        if (newZ > MAX_POS) newZ = MAX_POS;
        if (newZ < -MAX_POS) newZ = -MAX_POS;

        particles[idx + 3] = x;
        particles[idx + 4] = y;
        particles[idx + 5] = z;
        particles[idx] = newX;
        particles[idx + 1] = newY;
        particles[idx + 2] = newZ;
    }

    // ---- 约束求解 ----
    for (let iter = 0; iter < CONSTRAINT_ITERATIONS; iter++) {
        for (let c = 0; c < constraints.length; c++) {
            const constraint = constraints[c];
            const idx1 = constraint.i * 7;
            const idx2 = constraint.j * 7;

            if (particles[idx1 + 6] && particles[idx2 + 6]) continue;

            const x1 = particles[idx1];
            const y1 = particles[idx1 + 1];
            const z1 = particles[idx1 + 2];
            const x2 = particles[idx2];
            const y2 = particles[idx2 + 1];
            const z2 = particles[idx2 + 2];

            const dx = x2 - x1;
            const dy = y2 - y1;
            const dz = z2 - z1;
            const distSq = dx * dx + dy * dy + dz * dz;

            if (distSq < 1e-8) continue;

            const dist = Math.sqrt(distSq);
            const stiffness = constraint.stiffness;

            let diff = (dist - constraint.restLength) / dist;
            // 结构约束是硬约束：完全不截断，一次性消除拉伸
            if (!constraint.isRigid) {
                const maxDiff = MAX_CORRECTION / Math.max(constraint.restLength, 0.01);
                if (Math.abs(diff) > maxDiff) {
                    diff = Math.sign(diff) * maxDiff;
                }
            }

            const offsetX = dx * 0.5 * diff * stiffness;
            const offsetY = dy * 0.5 * diff * stiffness;
            const offsetZ = dz * 0.5 * diff * stiffness;

            if (!particles[idx1 + 6]) {
                particles[idx1] += offsetX;
                particles[idx1 + 1] += offsetY;
                particles[idx1 + 2] += offsetZ;
            }
            if (!particles[idx2 + 6]) {
                particles[idx2] -= offsetX;
                particles[idx2 + 1] -= offsetY;
                particles[idx2 + 2] -= offsetZ;
            }
        }
    }

    // ---- 布料自碰撞 ----（低端机禁用以节省每帧开销；高端机保留体积感）
    resolveSelfCollisions();
    if (QUALITY !== 'low') {
        
    }

    // ---- 旗杆碰撞检测 ----
    // modern/spear 横挂模式启用，阻止旗面穿透旗杆
    if (currentPoleType !== 'dadun') {
        resolvePoleCollisions();
    }

    // ---- 更新 Three.js 网格 ----
    for (let i = 0; i < totalParticles; i++) {
        const idx = i * 7;
        const posIdx = i * 3;

        let px = particles[idx];
        let py = particles[idx + 1];
        let pz = particles[idx + 2];

        // 最终数值检查
        if (!isFinite(px) || !isFinite(py) || !isFinite(pz)) {
            const origIdx = posIdx;
            px = originalPositions[origIdx];
            py = originalPositions[origIdx + 1];
            pz = originalPositions[origIdx + 2];
            particles[idx] = px;
            particles[idx + 1] = py;
            particles[idx + 2] = pz;
            particles[idx + 3] = px;
            particles[idx + 4] = py;
            particles[idx + 5] = pz;
        }

        positions[posIdx] = px;
        positions[posIdx + 1] = py;
        positions[posIdx + 2] = pz;
    }

    flagMesh.geometry.attributes.position.needsUpdate = true;
    flagMesh.geometry.computeVertexNormals();
    flagMesh.geometry.computeBoundingSphere();
}

// ========== 旗杆碰撞检测 ==========
function resolvePoleCollisions() {
    if (!poleGroup || !particles || !flagMesh) return;

    if (poleBoxNeedsUpdate || !cachedPoleBox) {
        // 只把标记为 poleCore 的元素（旗杆主体）合并到包围盒，忽略旗裤/装饰等
        cachedPoleBox = new THREE.Box3();
        poleGroup.traverse(obj => {
            if (obj.isMesh && obj.userData.poleCore) {
                const box = new THREE.Box3().setFromObject(obj);
                cachedPoleBox.union(box);
            }
        });
        poleBoxNeedsUpdate = false;
    }
    
    const poleBox = cachedPoleBox;
    const totalParticles = particles.length / 7;
    const margin = 0.02; // 旗杆碰撞检测的安全边距，避免旗面紧贴杆体
    
    // 粒子坐标是几何体局部坐标，flagMesh有位置偏移（meshCenterX/Y）
    // 必须把粒子坐标转换到世界坐标才能与poleBox比较
    const offsetX = flagMesh.position.x;
    const offsetY = flagMesh.position.y;
    const offsetZ = flagMesh.position.z;
    
    for (let i = 0; i < totalParticles; i++) {
        const idx = i * 7;
        if (particles[idx + 6]) continue;

        // 粒子世界坐标
        const wx = particles[idx] + offsetX;
        const wy = particles[idx + 1] + offsetY;
        const wz = particles[idx + 2] + offsetZ;

        if (wx > poleBox.min.x - margin && wx < poleBox.max.x + margin &&
            wy > poleBox.min.y - margin && wy < poleBox.max.y + margin &&
            wz > poleBox.min.z - margin && wz < poleBox.max.z + margin) {

            const distLeft = Math.abs(wx - poleBox.min.x);
            const distRight = Math.abs(poleBox.max.x - wx);
            const distBottom = Math.abs(wy - poleBox.min.y);
            const distTop = Math.abs(poleBox.max.y - wy);
            const distFront = Math.abs(wz - poleBox.min.z);
            const distBack = Math.abs(poleBox.max.z - wz);

            const minDist = Math.min(distLeft, distRight, distBottom, distTop, distFront, distBack);

            // 修正量写回粒子局部坐标（减去偏移）
            if (minDist === distLeft) {
                particles[idx] = poleBox.min.x - margin - offsetX;
                particles[idx + 3] = particles[idx];
            } else if (minDist === distRight) {
                particles[idx] = poleBox.max.x + margin - offsetX;
                particles[idx + 3] = particles[idx];
            } else if (minDist === distBottom) {
                particles[idx + 1] = poleBox.min.y - margin - offsetY;
                particles[idx + 4] = particles[idx + 1];
            } else if (minDist === distTop) {
                particles[idx + 1] = poleBox.max.y + margin - offsetY;
                particles[idx + 4] = particles[idx + 1];
            } else if (minDist === distFront) {
                particles[idx + 2] = poleBox.min.z - margin - offsetZ;
                particles[idx + 5] = particles[idx + 2];
            } else {
                particles[idx + 2] = poleBox.max.z + margin - offsetZ;
                particles[idx + 5] = particles[idx + 2];
            }
        }
    }
}

// ========== 布料自碰撞检测（3D 空间哈希） ==========
// 用空间哈希在 3D 空间检查近邻粒子对，避免旗面正反两面完全重叠
function resolveSelfCollisions() {
    if (!particles) return;

    const totalParticles = particles.length / 7;
    // 旗面"厚度"：小于这个距离的两点视为穿透，强行分开
    const thickness = 0.04;
    const thicknessSq = thickness * thickness;
    // 空间哈希 cell 边长 = thickness * 2，让邻近粒子落到同一格或相邻格
    const cellSize = thickness * 2.0;
    const invCell = 1.0 / cellSize;

    // 构建空间哈希
    const grid = new Map();
    for (let i = 0; i < totalParticles; i++) {
        const idx = i * 7;
        const cx = Math.floor(particles[idx] * invCell);
        const cy = Math.floor(particles[idx + 1] * invCell);
        const cz = Math.floor(particles[idx + 2] * invCell);
        const key = cx * 73856093 ^ cy * 19349663 ^ cz * 83492791;
        if (!grid.has(key)) grid.set(key, []);
        grid.get(key).push(i);
    }

    // 检查每个粒子与 27 个相邻 cell 内粒子的距离
    // 跳过结构约束的近邻（左右上下前后 6 个直接邻居）以免破坏旗面本身
    const w = SEG_X + 1;
    const isStructuralNeighbor = (a, b) => {
        const ca = a % w, ra = Math.floor(a / w);
        const cb = b % w, rb = Math.floor(b / w);
        const dc = Math.abs(ca - cb), dr = Math.abs(ra - rb);
        // 水平/垂直紧邻
        if (dc + dr === 1) return true;
        return false;
    };

    for (let i = 0; i < totalParticles; i++) {
        const idx = i * 7;
        if (particles[idx + 6]) continue;
        const cx = Math.floor(particles[idx] * invCell);
        const cy = Math.floor(particles[idx + 1] * invCell);
        const cz = Math.floor(particles[idx + 2] * invCell);

        const ix = particles[idx], iy = particles[idx + 1], iz = particles[idx + 2];

        for (let dx = -1; dx <= 1; dx++) {
            for (let dy = -1; dy <= 1; dy++) {
                for (let dz = -1; dz <= 1; dz++) {
                    const key = (cx + dx) * 73856093 ^ (cy + dy) * 19349663 ^ (cz + dz) * 83492791;
                    const cell = grid.get(key);
                    if (!cell) continue;
                    for (let k = 0; k < cell.length; k++) {
                        const j = cell[k];
                        if (j <= i) continue; // 每对只处理一次
                        if (isStructuralNeighbor(i, j)) continue;

                        const jdx = j * 7;
                        if (particles[jdx + 6]) continue;

                        const ddx = particles[jdx] - ix;
                        const ddy = particles[jdx + 1] - iy;
                        const ddz = particles[jdx + 2] - iz;
                        const distSq = ddx * ddx + ddy * ddy + ddz * ddz;
                        if (distSq < thicknessSq && distSq > 1e-10) {
                            const dist = Math.sqrt(distSq);
                            const overlap = (thickness - dist) * 0.5;
                            const nx = ddx / dist;
                            const ny = ddy / dist;
                            const nz = ddz / dist;
                            particles[idx] -= nx * overlap;
                            particles[idx + 1] -= ny * overlap;
                            particles[idx + 2] -= nz * overlap;
                            particles[jdx] += nx * overlap;
                            particles[jdx + 1] += ny * overlap;
                            particles[jdx + 2] += nz * overlap;
                        }
                    }
                }
            }
        }
    }
}
// ========== 动画循环 ==========
function animate() {
    animationId = requestAnimationFrame(animate);
    time += 0.016;

    simulateFlag();

    if (gifAnimation) {
        updateGIFAnimation();
    }

    controls.update();
    renderer.render(scene, camera);
}

function updateGIFAnimation() {
    if (!gifAnimation || !gifAnimation.frames || gifAnimation.frames.length === 0) return;
    if (!flagMesh || !flagMesh.material || !flagMesh.material.map) return;

    const now = performance.now();
    if (gifAnimation.lastTime === 0) gifAnimation.lastTime = now;

    const frame = gifAnimation.frames[gifAnimation.currentIndex];
    if (now - gifAnimation.lastTime >= frame.delay) {
        gifAnimation.currentIndex = (gifAnimation.currentIndex + 1) % gifAnimation.frames.length;
        gifAnimation.lastTime = now;
        const newFrame = gifAnimation.frames[gifAnimation.currentIndex];
        flagMesh.material.map = newFrame.texture;
        applyFlagOrientation();
    }
}

// ========== 旗面纹理加载 ==========
// function loadFlagTexture(src, name) {
//     const loader = new THREE.TextureLoader();
//     loader.load(
//         src,
//         (texture) => {
//             texture.colorSpace = THREE.SRGBColorSpace;
//             texture.minFilter = THREE.LinearFilter;
//             texture.magFilter = THREE.LinearFilter;
//             currentTexture = texture;
//             createFlag();
//         },
//         undefined,
//         (err) => {
//             console.error('加载旗面纹理失败:', err);
//         }
//     );
// }
function loadFlagTexture(src, name) {
    stopGIFAnimation();

    const isSvgFile = typeof src === 'string' && src.toLowerCase().endsWith('.svg');
    const isSvgText = typeof src === 'string' && src.trim().startsWith('<') && src.includes('<svg');

    if (isSvgFile) {
        // ✨【核心拦截】：如果是文件路径，先用 fetch 拿到纯文本源码
        fetch(src)
            .then(response => {
                if (!response.ok) throw new Error(`无法读取文件路径: ${src}`);
                return response.text();
            })
            .then(rawText => {
                // 送去清洗，把带有 <?xml ?> 的脏数据洗干净
                const safeSvgText = prepareSvgString(rawText);

                // 高清光栅化 SVG → PNG（按真实展示尺寸渲染，避免纹理模糊）
                rasterizeSvgToTexture(safeSvgText);
            })
            .catch(error => {
                console.error("SVG 预处理清洗失败，正在回退至原始路径加载:", error);
                // 发生意外时，以原始路径进行保底尝试
                executeTextureLoad(src, false);
            });

    } else if (isSvgText) {
        // 如果是从其他本地上传组件直接传过来的原始 SVG 代码文本
        const safeSvgText = prepareSvgString(src);
        rasterizeSvgToTexture(safeSvgText);

    } else {
        // 如果是标准的 PNG / JPG 图片，不需要任何清洗，直接走正常加载
        executeTextureLoad(src, false);
    }
}

// ========== SVG 高清光栅化 ==========
// 将 SVG 文本光栅化为高分辨率 PNG 数据 URL，确保旗面纹理清晰
function rasterizeSvgToTexture(safeSvgText) {
    const blob = new Blob([safeSvgText], { type: 'image/svg+xml;charset=utf-8' });
    const blobUrl = URL.createObjectURL(blob);

    const img = new Image();
    img.onload = () => {
        // 解析 SVG 宽高比：优先 viewBox，其次 width/height 属性
        let aspect = 1;
        const vbMatch = safeSvgText.match(/viewBox=["']([^"']+)["']/i);
        if (vbMatch) {
            const parts = vbMatch[1].split(/[\s,]+/).map(parseFloat);
            if (parts.length === 4 && parts[2] > 0 && parts[3] > 0) {
                aspect = parts[2] / parts[3];
            }
        }
        if (Math.abs(aspect - 1) < 1e-6) {
            const wMatch = safeSvgText.match(/\swidth=["'](\d+(?:\.\d+)?)["']/i);
            const hMatch = safeSvgText.match(/\sheight=["'](\d+(?:\.\d+)?)["']/i);
            if (wMatch && hMatch) {
                aspect = parseFloat(wMatch[1]) / parseFloat(hMatch[1]);
            }
        }

        // 目标长边 2048px，按比例计算另一边
        const maxSize = 2048;
        let w, h;
        if (aspect >= 1) {
            w = maxSize;
            h = Math.max(1, Math.round(maxSize / aspect));
        } else {
            h = maxSize;
            w = Math.max(1, Math.round(maxSize * aspect));
        }

        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, w, h);
        ctx.drawImage(img, 0, 0, w, h);

        URL.revokeObjectURL(blobUrl);

        // 转为 PNG data URL 作为纹理源
        executeTextureLoad(canvas.toDataURL('image/png'), false);
    };
    img.onerror = (err) => {
        console.error('SVG 光栅化失败:', err);
        URL.revokeObjectURL(blobUrl);
        // 回退：直接用 blob URL 让 TextureLoader 尝试
        executeTextureLoad(blobUrl, true);
    };
    img.src = blobUrl;
}

function executeTextureLoad(url, isGeneratedBlob) {
    const loader = new THREE.TextureLoader();
    loader.load(
        url,
        (texture) => {
            texture.colorSpace = THREE.SRGBColorSpace;
            texture.minFilter = THREE.LinearMipmapLinearFilter;
            texture.magFilter = THREE.LinearFilter;
            texture.generateMipmaps = true;
            texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
            //texture.anisotropy = QUALITY === 'low' ? 1 : renderer.capabilities.getMaxAnisotropy();

            if (texture.image) {
                originalSourceImage = texture.image;
            }

            currentTexture = texture;
            createFlag();

            if (isGeneratedBlob) {
                URL.revokeObjectURL(url);
            }
        },
        undefined,
        (err) => {
            console.error('加载旗面纹理失败:', err);
            if (isGeneratedBlob) {
                URL.revokeObjectURL(url);
            }
        }
    );
}
function prepareSvgString(rawSvgString) {
    if (!rawSvgString) return '';

    // 1. 去除可能存在的首尾空白字符
    let cleanSvg = rawSvgString.trim();

    // 2. 利用正则强行删掉开头的 <?xml ... ?> 声明
    cleanSvg = cleanSvg.replace(/^<\?xml[^>]*\?>/i, '').trim();

    // 3. 检查 SVG 标签是否闭合。如果末尾因为截断残缺，强制补全它
    if (!cleanSvg.endsWith('</svg>')) {
        // 如果漏掉了 g 标签闭合，先补 g
        if (cleanSvg.includes('<g') && !cleanSvg.endsWith('</g>')) {
            cleanSvg += '</g>';
        }
        cleanSvg += '</svg>';
    }

    return cleanSvg;
}
function stopGIFAnimation() {
    if (gifAnimation) {
        gifAnimation.frames.forEach(f => f.texture.dispose());
        gifAnimation = null;
    }
    gifBaseTexture = null;
}

function setupGIFAnimation(gifData, name) {
    stopGIFAnimation();

    const result = extractGIFFrames(gifData);
    if (!result || result.frames.length === 0) {
        console.warn('GIF 帧提取失败，尝试静态加载');
        loadFlagTexture(URL.createObjectURL(new Blob([gifData], { type: 'image/gif' })), name);
        return;
    }

    gifBaseTexture = result.frames[0].texture;
    currentTexture = gifBaseTexture;
    if (gifBaseTexture.image) {
        originalSourceImage = gifBaseTexture.image;
    }

    gifAnimation = {
        frames: result.frames,
        currentIndex: 0,
        lastTime: 0
    };

    createFlag();
}

function loadFlagFromFile(file) {
    if (!file) return;

    stopGIFAnimation();

    if (file.type === 'image/gif' || file.name.toLowerCase().endsWith('.gif')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            setupGIFAnimation(e.target.result, file.name);
        };
        reader.readAsArrayBuffer(file);
        return;
    }

    if (file.type === 'image/svg+xml' || file.name.endsWith('.svg')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const maxSize = 2048;
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
    } catch (e) {
        console.error('加载图库数据失败:', e);
    }
}

// ========== 搜索栏功能 ==========
let searchIndex = -1;
let searchResults = [];

function initSearchBar() {
    const searchInput = document.getElementById('flagSearchInput');
    const resultsContainer = document.getElementById('flagSearchResults');

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.trim().toLowerCase();
        if (!query) {
            resultsContainer.classList.remove('active');
            resultsContainer.innerHTML = '';
            searchResults = [];
            searchIndex = -1;
            return;
        }
        // 搜索匹配
        searchResults = images.filter(img =>
            img.name.toLowerCase().includes(query) ||
            (img.tags && img.tags.some(tag => tag.toLowerCase().includes(query)))
        ).slice(0, 50);
        searchIndex = -1;
        renderSearchResults();
    });

    searchInput.addEventListener('focus', () => {
        if (searchInput.value.trim()) {
            searchInput.dispatchEvent(new Event('input'));
        }
    });

    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowDown' && searchResults.length > 0) {
            e.preventDefault();
            searchIndex = (searchIndex + 1) % searchResults.length;
            renderSearchResults();
        } else if (e.key === 'ArrowUp' && searchResults.length > 0) {
            e.preventDefault();
            searchIndex = (searchIndex - 1 + searchResults.length) % searchResults.length;
            renderSearchResults();
        } else if (e.key === 'Enter' && searchIndex >= 0) {
            e.preventDefault();
            selectSearchResult(searchResults[searchIndex]);
        } else if (e.key === 'Escape') {
            resultsContainer.classList.remove('active');
            searchInput.blur();
        }
    });

    // 点击外部关闭
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            resultsContainer.classList.remove('active');
        }
    });
}

function renderSearchResults() {
    const resultsContainer = document.getElementById('flagSearchResults');
    if (searchResults.length === 0) {
        resultsContainer.innerHTML = '<div class="search-result-item" style="cursor:default;">无匹配结果</div>';
            resultsContainer.classList.add('active');
        return;
    }
    resultsContainer.innerHTML = '';
    searchResults.forEach((img, index) => {
        const item = document.createElement('div');
        item.className = 'search-result-item' + (index === searchIndex ? ' active' : '');
        item.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>${img.name}`;
        item.addEventListener('click', () => selectSearchResult(img));
        resultsContainer.appendChild(item);
    });
    resultsContainer.classList.add('active');
}

function selectSearchResult(img) {
    if (!img) return;
    document.getElementById('flagSearchInput').value = img.name;
    document.getElementById('flagSearchResults').classList.remove('active');
    loadFlagTexture(`svg/${encodeURIComponent(img.svgFile)}`, img.name);
}

// ========== 旗面方向变换 ==========
let flagOrientation = 'normal';
let originalSourceImage = null;

const ORIENTATION_HAS_90 = {
    normal: false, rotateCW: true, rotateCCW: true, rotate180: false,
    flipH: false, flipV: false, flipHV: false,
    rotateCW_flipH: true, rotateCW_flipV: true,
    rotateCCW_flipH: true, rotateCCW_flipV: true,
};

function createOrientedCanvas(sourceImage, orientation) {
    const w = sourceImage.naturalWidth || sourceImage.width || sourceImage.videoWidth;
    const h = sourceImage.naturalHeight || sourceImage.height || sourceImage.videoHeight;

    const has90 = ORIENTATION_HAS_90[orientation] || false;
    const outW = has90 ? h : w;
    const outH = has90 ? w : h;

    const canvas = document.createElement('canvas');
    canvas.width = outW;
    canvas.height = outH;
    const ctx = canvas.getContext('2d');

    ctx.save();
    ctx.translate(outW / 2, outH / 2);

    switch (orientation) {
        case 'normal':
            break;
        case 'rotateCW':
            ctx.rotate(Math.PI / 2);
            break;
        case 'rotateCCW':
            ctx.rotate(-Math.PI / 2);
            break;
        case 'rotate180':
            ctx.rotate(Math.PI);
            break;
        case 'flipH':
            ctx.scale(-1, 1);
            break;
        case 'flipV':
            ctx.scale(1, -1);
            break;
        case 'flipHV':
            ctx.scale(-1, -1);
            break;
        case 'rotateCW_flipH':
            ctx.scale(-1, 1);
            ctx.rotate(Math.PI / 2);
            break;
        case 'rotateCW_flipV':
            ctx.scale(1, -1);
            ctx.rotate(Math.PI / 2);
            break;
        case 'rotateCCW_flipH':
            ctx.scale(-1, 1);
            ctx.rotate(-Math.PI / 2);
            break;
        case 'rotateCCW_flipV':
            ctx.scale(1, -1);
            ctx.rotate(-Math.PI / 2);
            break;
        default:
            break;
    }

    ctx.drawImage(sourceImage, -w / 2, -h / 2, w, h);
    ctx.restore();

    return canvas;
}

function applyFlagOrientation() {
    if (!flagMesh || !flagMesh.material.map || !originalSourceImage) return;

    const orientedCanvas = createOrientedCanvas(originalSourceImage, flagOrientation);
    const newTexture = new THREE.CanvasTexture(orientedCanvas);
    newTexture.colorSpace = THREE.SRGBColorSpace;
    newTexture.minFilter = THREE.LinearMipmapLinearFilter;
    newTexture.magFilter = THREE.LinearFilter;
    newTexture.generateMipmaps = true;
    //newTexture.anisotropy = QUALITY === 'low' ? 1 : renderer.capabilities.getMaxAnisotropy();
    newTexture.anisotropy = renderer.capabilities.getMaxAnisotropy();
    const oldMap = flagMesh.material.map;
    flagMesh.material.map = newTexture;
    flagMesh.material.needsUpdate = true;

    if (oldMap && oldMap !== currentTexture) {
        oldMap.dispose();
    }

    currentTexture = newTexture;
}

function applyFlagOrientationWithRebuild() {
    if (!originalSourceImage) {
        applyFlagOrientation();
        return;
    }

    const has90 = ORIENTATION_HAS_90[flagOrientation] || false;
    const imgW = originalSourceImage.naturalWidth || originalSourceImage.width;
    const imgH = originalSourceImage.naturalHeight || originalSourceImage.height;

    // 计算新方向需要的展示宽高比
    const newDisplayAspect = has90 ? (imgH / imgW) : (imgW / imgH);
    // 当前旗面的宽高比
    const currentFlagAspect = flagWidth / flagHeight;

    // 如果宽高比差异超过阈值，需要重建旗面几何体
    const aspectThreshold = 0.05;
    const needsRebuild = Math.abs(newDisplayAspect - currentFlagAspect) > aspectThreshold;

    if (needsRebuild) {
        const orientedCanvas = createOrientedCanvas(originalSourceImage, flagOrientation);
        const newTexture = new THREE.CanvasTexture(orientedCanvas);
        newTexture.colorSpace = THREE.SRGBColorSpace;
        newTexture.minFilter = THREE.LinearMipmapLinearFilter;
        newTexture.magFilter = THREE.LinearFilter;
        newTexture.generateMipmaps = true;
        //newTexture.anisotropy = QUALITY === 'low' ? 1 : renderer.capabilities.getMaxAnisotropy();
        newTexture.anisotropy =  renderer.capabilities.getMaxAnisotropy();
        if (currentTexture && currentTexture !== newTexture) {
            currentTexture.dispose();
        }
        currentTexture = newTexture;
        createFlag();
    } else {
        applyFlagOrientation();
    }
}

// ========== 事件监听 ==========
function setupEventListeners() {
    // 初始化搜索栏
    initSearchBar();

    // 旗面方向
    document.getElementById('flagOrientationSelect').addEventListener('change', (e) => {
        flagOrientation = e.target.value;
        applyFlagOrientationWithRebuild();
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
        sleeveColor = e.target.value;
        document.getElementById('spearColorValue').textContent = sleeveColor;
        if (poleGroup && poleGroup.userData.sleeve) {
            poleGroup.userData.sleeve.material.color.set(sleeveColor);
        }
    });

    // 风速
    document.getElementById('windSpeedSlider').addEventListener('input', (e) => {
        windSpeed = parseFloat(e.target.value);
        document.getElementById('windValue').textContent = windSpeed.toFixed(1);
    });

    // 重置视角
    document.getElementById('resetCameraBtn').addEventListener('click', () => {
        camera.position.set(3, 5, 6);
        controls.target.set(1.56, 4, 0);
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
