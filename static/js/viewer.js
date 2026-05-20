/* =====================================================
   Heidstar WSI Viewer — Viewer page logic
   Includes a built-in scale bar (no external plugin).
   ===================================================== */

const slideName = window.SLIDE_NAME;
const mpp = window.SLIDE_MPP;                     // microns per pixel
const magnification = window.SLIDE_MAGNIFICATION;
const encodedSlide = encodeURIComponent(slideName);


/* ─────────────────────────────────────────────────────
   Initialize OpenSeadragon
   ───────────────────────────────────────────────────── */
const viewer = OpenSeadragon({
    id: "openseadragon-viewer",
    tileSources: `/api/slides/${encodedSlide}/dzi`,
    prefixUrl: "https://cdn.jsdelivr.net/npm/openseadragon@4.1.0/build/openseadragon/images/",

    showNavigator: true,
    navigatorPosition: "TOP_RIGHT",
    navigatorAutoFade: false,
    navigatorBackground: "#0f172a",
    navigatorOpacity: 0.85,
    navigatorBorderColor: "#2563eb",
    navigatorDisplayRegionColor: "#2563eb",
    navigatorSizeRatio: 0.15,

    showRotationControl: true,
    showFullPageControl: true,
    showHomeControl: true,
    showZoomControl: true,

    animationTime: 0.5,
    blendTime: 0.1,
    constrainDuringPan: true,
    maxZoomPixelRatio: 4,
    minZoomLevel: 0.5,
    visibilityRatio: 1.0,
    zoomPerScroll: 1.3,

    immediateRender: false,
    preserveViewport: true,
    placeholderFillStyle: "#0a0e1a",
});


/* ─────────────────────────────────────────────────────
   Build the scale bar element (overlay on the viewer)
   ───────────────────────────────────────────────────── */
function createScaleBar() {
    const container = document.getElementById("openseadragon-viewer");

    const scaleBar = document.createElement("div");
    scaleBar.id = "scale-bar";
    scaleBar.style.cssText = `
        position: absolute;
        bottom: 24px;
        right: 24px;
        background: rgba(15, 23, 42, 0.85);
        color: #ffffff;
        padding: 8px 12px;
        border-radius: 6px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        font-size: 13px;
        font-weight: 600;
        z-index: 100;
        pointer-events: none;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(148, 163, 184, 0.2);
    `;

    const text = document.createElement("div");
    text.id = "scale-bar-text";
    text.textContent = "—";

    const bar = document.createElement("div");
    bar.id = "scale-bar-line";
    bar.style.cssText = `
        height: 3px;
        background: #ffffff;
        width: 100px;
        border-radius: 1px;
    `;

    scaleBar.appendChild(text);
    scaleBar.appendChild(bar);
    container.appendChild(scaleBar);

    return { scaleBar, text, bar };
}


/* ─────────────────────────────────────────────────────
   Compute and update the scale bar
   ───────────────────────────────────────────────────── */
function updateScaleBar(scaleBarElements) {
    if (!mpp || !scaleBarElements) return;

    // Get the viewport width in image pixels
    const containerWidth = viewer.viewport.containerSize.x;
    const zoom = viewer.viewport.getZoom(true);
    const imageZoom = viewer.viewport.viewportToImageZoom(zoom);

    // pixels per micrometer at current zoom
    const screenPixelsPerImagePixel = imageZoom;
    const screenPixelsPerMicron = screenPixelsPerImagePixel / mpp;

    // Choose a "nice" length for the bar (around 100-150 screen pixels)
    const targetScreenLength = 120;
    const targetMicrons = targetScreenLength / screenPixelsPerMicron;

    // Round to a nice human number: 1, 2, 5, 10, 20, 50, 100, 200, 500, ...
    const niceValues = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000];
    let niceMicrons = niceValues[0];
    for (const v of niceValues) {
        if (v <= targetMicrons) niceMicrons = v;
    }

    // Convert to display units
    let displayValue, displayUnit;
    if (niceMicrons >= 1000) {
        displayValue = niceMicrons / 1000;
        displayUnit = "mm";
    } else {
        displayValue = niceMicrons;
        displayUnit = "µm";
    }

    // Width on screen
    const barScreenWidth = niceMicrons * screenPixelsPerMicron;

    // Update DOM
    scaleBarElements.text.textContent = `${displayValue} ${displayUnit}`;
    scaleBarElements.bar.style.width = `${barScreenWidth}px`;
}


/* ─────────────────────────────────────────────────────
   Wire it all up
   ───────────────────────────────────────────────────── */
let scaleBarElements = null;

viewer.addHandler("open", () => {
    console.log(`✅ Slide opened: ${slideName}`);
    if (mpp) {
        scaleBarElements = createScaleBar();
        updateScaleBar(scaleBarElements);
        console.log(`✅ Scale bar enabled (mpp = ${mpp} µm/px)`);
    } else {
        console.log("ℹ️  Scale bar disabled — no MPP data");
    }
});

viewer.addHandler("zoom", () => {
    // Update scale bar
    if (scaleBarElements) updateScaleBar(scaleBarElements);

    // Update live magnification chip
    if (!magnification) return;
    const currentZoom = viewer.viewport.getZoom(true);
    const maxZoom = viewer.viewport.getMaxZoom();
    const realMag = (currentZoom / maxZoom) * magnification;
    const el = document.getElementById("live-magnification-value");
    if (el) el.textContent = `${realMag.toFixed(1)}×`;
});

viewer.addHandler("resize", () => {
    if (scaleBarElements) updateScaleBar(scaleBarElements);
});


/* ─────────────────────────────────────────────────────
   Error handling
   ───────────────────────────────────────────────────── */
viewer.addHandler("open-failed", (e) => {
    console.error("Failed to open slide:", e);
    const container = document.getElementById("openseadragon-viewer");
    container.innerHTML = `
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #f1f5f9;
            text-align: center;
            padding: 48px;">
            <div style="font-size: 48px; margin-bottom: 16px;">⚠️</div>
            <h2 style="font-size: 20px; font-weight: 600; margin-bottom: 8px;">
                Could not open slide
            </h2>
            <p style="opacity: 0.7; font-size: 14px;">${e.message || "unknown error"}</p>
        </div>
    `;
});