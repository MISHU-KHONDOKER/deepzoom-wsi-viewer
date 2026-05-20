/* =====================================================
   Heidstar WSI Viewer — Index page logic
   Handles upload, listing, and deletion of slides.
   ===================================================== */

// DOM references
const fileInput        = document.getElementById("file-input");
const uploadDrop       = document.querySelector(".upload-drop");
const uploadStatus     = document.getElementById("upload-status");
const uploadFilename   = document.getElementById("upload-filename");
const uploadProgressBar = document.getElementById("upload-progress-bar");
const uploadMessage    = document.getElementById("upload-message");
const slideList        = document.getElementById("slide-list");
const refreshBtn       = document.getElementById("refresh-btn");


/* ─────────────────────────────────────────────────────
   List slides
   ───────────────────────────────────────────────────── */
async function loadSlides() {
    slideList.innerHTML = `<p class="empty-state">Loading slides…</p>`;

    try {
        const response = await fetch("/api/slides");
        if (!response.ok) throw new Error(`Server returned ${response.status}`);
        const data = await response.json();
        renderSlideList(data.slides);
    } catch (err) {
        slideList.innerHTML = `<p class="empty-state">⚠️  Could not load slides: ${err.message}</p>`;
    }
}

function renderSlideList(slides) {
    if (!slides || slides.length === 0) {
        slideList.innerHTML = `
            <p class="empty-state">
                No slides uploaded yet. Use the upload area above to add one.
            </p>`;
        return;
    }

    slideList.innerHTML = slides.map(slide => {
        const encodedName = encodeURIComponent(slide.name);
        return `
            <div class="slide-card" data-slide="${slide.name}">
                <div class="slide-card-thumb">
                    <img src="/api/slides/${encodedName}/thumbnail"
                         alt="${slide.name} thumbnail"
                         loading="lazy"
                         onerror="this.style.display='none'">
                </div>
                <div class="slide-card-body">
                    <div class="slide-card-name" title="${slide.name}">${slide.name}</div>
                    <div class="slide-card-meta">
                        ${slide.size_mb} MB · ${slide.extension}
                    </div>
                </div>
                <div class="slide-card-actions">
                    <a class="btn btn-primary"
                       href="/viewer/${encodedName}">Open Viewer</a>
                    <button class="btn btn-danger"
                            data-action="delete"
                            data-slide="${slide.name}">Delete</button>
                </div>
            </div>
        `;
    }).join("");
}


/* ─────────────────────────────────────────────────────
   Delete a slide
   ───────────────────────────────────────────────────── */
async function deleteSlide(slideName) {
    const confirmed = confirm(`Delete "${slideName}"? This cannot be undone.`);
    if (!confirmed) return;

    try {
        const response = await fetch(
            `/api/slides/${encodeURIComponent(slideName)}`,
            { method: "DELETE" }
        );
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || `Server returned ${response.status}`);
        }
        loadSlides();
    } catch (err) {
        alert(`Failed to delete slide: ${err.message}`);
    }
}

slideList.addEventListener("click", (e) => {
    const button = e.target.closest("[data-action='delete']");
    if (button) {
        const slideName = button.getAttribute("data-slide");
        deleteSlide(slideName);
    }
});


/* ─────────────────────────────────────────────────────
   Upload — with progress bar
   ───────────────────────────────────────────────────── */
function showUploadStatus(filename) {
    uploadStatus.classList.remove("hidden");
    uploadFilename.textContent = filename;
    uploadProgressBar.style.width = "0%";
    uploadMessage.textContent = "Uploading…";
    uploadMessage.className = "upload-message";
}

function setUploadProgress(percent) {
    uploadProgressBar.style.width = `${percent}%`;
}

function setUploadMessage(text, kind = "info") {
    uploadMessage.textContent = text;
    uploadMessage.className = `upload-message ${kind}`;
}

function uploadFile(file) {
    showUploadStatus(file.name);

    const formData = new FormData();
    formData.append("file", file);

    // XMLHttpRequest is used (not fetch) because it supports upload progress
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
        if (e.lengthComputable) {
            const percent = (e.loaded / e.total) * 100;
            setUploadProgress(percent);
        }
    });

    xhr.addEventListener("load", () => {
        if (xhr.status >= 200 && xhr.status < 300) {
            setUploadProgress(100);
            setUploadMessage("✅ Upload successful", "success");
            // Refresh the slide list
            loadSlides();
            // Hide status after a moment
            setTimeout(() => {
                uploadStatus.classList.add("hidden");
                fileInput.value = "";
            }, 2500);
        } else {
            let detail = "Upload failed";
            try {
                const json = JSON.parse(xhr.responseText);
                if (json.detail) detail = json.detail;
            } catch {}
            setUploadMessage(`❌ ${detail}`, "error");
        }
    });

    xhr.addEventListener("error", () => {
        setUploadMessage("❌ Network error during upload", "error");
    });

    xhr.open("POST", "/api/slides/upload");
    xhr.send(formData);
}

// File input change
fileInput.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (file) uploadFile(file);
});

// Drag-and-drop
["dragenter", "dragover"].forEach(eventName => {
    uploadDrop.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadDrop.classList.add("dragover");
    });
});

["dragleave", "drop"].forEach(eventName => {
    uploadDrop.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadDrop.classList.remove("dragover");
    });
});

uploadDrop.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
});


/* ─────────────────────────────────────────────────────
   Refresh + init
   ───────────────────────────────────────────────────── */
refreshBtn.addEventListener("click", loadSlides);

// Load slides immediately on page load
loadSlides();