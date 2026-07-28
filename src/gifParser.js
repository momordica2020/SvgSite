import * as THREE from 'three';

function parseGIF(arrayBuffer) {
    const data = new Uint8Array(arrayBuffer);
    const view = new DataView(arrayBuffer);
    const frames = [];

    let pos = 0;

    const readSubBlocks = () => {
        let result = new Uint8Array(0);
        while (pos < data.length) {
            const blockSize = data[pos++];
            if (blockSize === 0) break;
            const newResult = new Uint8Array(result.length + blockSize);
            newResult.set(result, 0);
            newResult.set(data.subarray(pos, pos + blockSize), result.length);
            result = newResult;
            pos += blockSize;
        }
        return result;
    };

    const readExtension = () => {
        const type = data[pos++];
        if (type === 0xF9) {
            const blockSize = data[pos++];
            const packed = data[pos++];
            const delay = view.getUint16(pos, true);
            pos += 2;
            const transparentIndex = data[pos++];
            pos++;
            if (frames.length > 0) {
                const frame = frames[frames.length - 1];
                frame.delay = delay * 10;
                frame.disposal = (packed >> 2) & 0x07;
                frame.transparentIndex = transparentIndex;
            }
        } else if (type === 0xFF) {
            const blockSize = data[pos++];
            const label = data.subarray(pos, pos + blockSize);
            pos += blockSize;
            readSubBlocks();
        } else {
            readSubBlocks();
        }
    };

    const readLZW = (minCodeSize, pixelCount) => {
        const clearCode = 1 << minCodeSize;
        const eoiCode = clearCode + 1;
        let codeSize = minCodeSize + 1;
        let nextCode = eoiCode + 1;
        let codeMask = (1 << codeSize) - 1;

        const dictionary = [];
        const resetDict = () => {
            dictionary.length = 0;
            for (let i = 0; i < clearCode; i++) {
                dictionary.push([i]);
            }
            dictionary.push(null);
            dictionary.push(null);
            nextCode = eoiCode + 1;
            codeSize = minCodeSize + 1;
            codeMask = (1 << codeSize) - 1;
        };
        resetDict();

        const output = new Uint8Array(pixelCount);
        let outputPos = 0;
        let prev = null;
        let bitBuffer = 0;
        let bitCount = 0;
        const raw = readSubBlocks();
        let rawPos = 0;

        const readCode = () => {
            while (bitCount < codeSize) {
                if (rawPos >= raw.length) return -1;
                bitBuffer |= raw[rawPos++] << bitCount;
                bitCount += 8;
            }
            const code = bitBuffer & codeMask;
            bitBuffer >>= codeSize;
            bitCount -= codeSize;
            return code;
        };

        while (outputPos < pixelCount) {
            const code = readCode();
            if (code === -1 || code === eoiCode) break;
            if (code === clearCode) {
                resetDict();
                prev = null;
                continue;
            }
            let entry;
            if (code < dictionary.length) {
                entry = dictionary[code];
            } else if (code === nextCode) {
                if (prev === null) return output;
                entry = [...prev, prev[0]];
            } else {
                return output;
            }
            if (entry === null) return output;

            for (let i = 0; i < entry.length && outputPos < pixelCount; i++) {
                output[outputPos++] = entry[i];
            }

            if (prev !== null) {
                dictionary[nextCode] = [...prev, entry[0]];
                nextCode++;
                if (nextCode > codeMask && codeSize < 12) {
                    codeSize++;
                    codeMask = (1 << codeSize) - 1;
                }
            }
            prev = entry;
        }
        return output;
    };

    const header = () => {
        const sig = String.fromCharCode.apply(null, data.subarray(0, 6));
        pos = 6;
        const width = view.getUint16(pos, true);
        const height = view.getUint16(pos + 2, true);
        pos += 4;
        const packed = data[pos++];
        const colorResolution = (packed >> 4) & 0x07;
        const hasGlobalColorTable = (packed >> 7) & 0x01;
        let gct = null;
        if (hasGlobalColorTable) {
            const gctSize = 3 * Math.pow(2, (packed & 0x07) + 1);
            gct = [];
            for (let i = 0; i < gctSize; i += 3) {
                gct.push([data[pos++], data[pos++], data[pos++]]);
            }
        }
        pos += 2;
        return { width, height, gct };
    };

    const { width, height, gct } = header();

    while (pos < data.length - 1) {
        const blockType = data[pos++];
        if (blockType === 0x21) {
            readExtension();
        } else if (blockType === 0x2C) {
            const frameLeft = view.getUint16(pos, true);
            const frameTop = view.getUint16(pos + 2, true);
            const frameWidth = view.getUint16(pos + 4, true);
            const frameHeight = view.getUint16(pos + 6, true);
            pos += 8;
            const flags = data[pos++];
            const localColorTableFlag = (flags >> 7) & 0x01;
            let lct = null;
            if (localColorTableFlag) {
                const lctSize = 3 * Math.pow(2, (flags & 0x07) + 1);
                lct = [];
                for (let i = 0; i < lctSize; i += 3) {
                    lct.push([data[pos++], data[pos++], data[pos++]]);
                }
            }
            const colorTable = lct || gct;
            const minCodeSize = data[pos++];
            const pixelCount = frameWidth * frameHeight;

            frames.push({
                left: frameLeft,
                top: frameTop,
                width: frameWidth,
                height: frameHeight,
                colorTable: colorTable,
                delay: 100,
                disposal: 0,
                transparentIndex: -1
            });

            const indices = readLZW(minCodeSize, pixelCount);
            const frame = frames[frames.length - 1];
            frame.indices = indices;
        } else if (blockType === 0x3B) {
            break;
        } else {
            break;
        }
    }

    return { width, height, frames };
}

function renderGIFFrame(frame, fullWidth, fullHeight, prevImageData) {
    const canvas = document.createElement('canvas');
    canvas.width = fullWidth;
    canvas.height = fullHeight;
    const ctx = canvas.getContext('2d');

    let imageData;
    if (prevImageData) {
        imageData = new ImageData(new Uint8ClampedArray(prevImageData.data), fullWidth, fullHeight);
    } else {
        imageData = ctx.createImageData(fullWidth, fullHeight);
    }

    const data = imageData.data;
    const palette = frame.colorTable;
    const transparentIndex = frame.transparentIndex;

    if (frame.disposal === 2) {
        for (let i = 0; i < data.length; i += 4) {
            data[i] = 0;
            data[i + 1] = 0;
            data[i + 2] = 0;
            data[i + 3] = 0;
        }
    }

    const indices = frame.indices;
    for (let y = 0; y < frame.height; y++) {
        for (let x = 0; x < frame.width; x++) {
            const idx = indices[y * frame.width + x];
            const px = frame.left + x;
            const py = frame.top + y;
            const di = (py * fullWidth + px) * 4;
            if (idx !== transparentIndex && palette && idx < palette.length) {
                data[di] = palette[idx][0];
                data[di + 1] = palette[idx][1];
                data[di + 2] = palette[idx][2];
                data[di + 3] = 255;
            }
        }
    }

    return imageData;
}

export function extractGIFFrames(arrayBuffer) {
    const parsed = parseGIF(arrayBuffer);
    if (!parsed.frames || parsed.frames.length === 0) return null;

    const textures = [];
    let prevImageData = null;

    for (const frame of parsed.frames) {
        const imageData = renderGIFFrame(frame, parsed.width, parsed.height, prevImageData);

        const canvas = document.createElement('canvas');
        canvas.width = parsed.width;
        canvas.height = parsed.height;
        const ctx = canvas.getContext('2d');
        ctx.putImageData(imageData, 0, 0);

        const texture = new THREE.CanvasTexture(canvas);
        texture.colorSpace = THREE.SRGBColorSpace;
        texture.minFilter = THREE.LinearFilter;
        texture.magFilter = THREE.LinearFilter;
        texture.generateMipmaps = false;

        textures.push({
            texture: texture,
            delay: frame.delay
        });

        if (frame.disposal === 2 || frame.disposal === 3) {
            prevImageData = null;
        } else {
            prevImageData = imageData;
        }
    }

    return {
        width: parsed.width,
        height: parsed.height,
        frames: textures
    };
}
