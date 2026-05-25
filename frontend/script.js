/* ============================================================
   LeadFlow AI — JavaScript Application Logic
   Handles: routing, form validation, API calls, processing states
============================================================ */

// ============================================================
// CONFIGURATION
// ============================================================
// Since the frontend is served by Flask on the same origin,
// we can use window.location.origin to target the API automatically.
const API_BASE = window.location.origin;

// Rotating quotes shown during processing
const PROCESSING_QUOTES = [
    '"Our AI is currently scanning 2,400+ industry data points to ensure your report is both accurate and tailored to market trends."',
    '"Analyzing competitive landscapes and cross-referencing 180+ business intelligence signals for your company."',
    '"Generating personalized strategic recommendations calibrated to your industry sector and growth stage."',
    '"Compiling your PDF report with executive-level insights and actionable growth opportunities."',
];

// ============================================================
// THEME MANAGEMENT
// ============================================================
const themeToggle = document.getElementById("themeToggle");
const iconMoon = themeToggle.querySelector(".icon-moon");
const iconSun  = themeToggle.querySelector(".icon-sun");

// Load saved theme or default to light
const savedTheme = localStorage.getItem("leadflow-theme") || "light";
applyTheme(savedTheme);

themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);
    localStorage.setItem("leadflow-theme", next);
});

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    if (theme === "dark") {
        iconMoon.style.display = "none";
        iconSun.style.display  = "block";
    } else {
        iconMoon.style.display = "block";
        iconSun.style.display  = "none";
    }
}

// ============================================================
// PAGE ROUTING
// ============================================================
let currentPage = "page-landing";

function showPage(pageId) {
    // Hide current
    const old = document.getElementById(currentPage);
    if (old) { old.classList.remove("active"); }

    // Show new
    const next = document.getElementById(pageId);
    if (next) {
        next.classList.add("active", "fade-in");
        next.scrollTop = 0;
        window.scrollTo(0, 0);
        // Remove animation class after it plays so it can replay
        setTimeout(() => next.classList.remove("fade-in"), 400);
    }

    currentPage = pageId;
}

// ============================================================
// FORM VALIDATION
// ============================================================
const form = document.getElementById("leadForm");

/**
 * Validate a single field and show/hide the error message.
 * Returns true if the field is valid.
 */
function validateField(id, errorId, rule, message) {
    const input = document.getElementById(id);
    const errEl = document.getElementById(errorId);
    const value = input.value.trim();
    const valid = rule(value);

    if (!valid) {
        input.classList.add("invalid");
        errEl.textContent = message;
    } else {
        input.classList.remove("invalid");
        errEl.textContent = "";
    }
    return valid;
}

function validateAll() {
    const emailRegex = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;
    const urlRegex   = /^https?:\/\/[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}(\/.*)?$/;

    const v1 = validateField("inputName",    "errName",    v => v.length >= 2,           "Full name must be at least 2 characters.");
    const v2 = validateField("inputEmail",   "errEmail",   v => emailRegex.test(v),       "Please enter a valid email address.");
    const v3 = validateField("inputCompany", "errCompany", v => v.length >= 2,            "Company name must be at least 2 characters.");
    const v4 = validateField("inputWebsite", "errWebsite", v => urlRegex.test(v),         "Enter a valid URL starting with https://");

    return v1 && v2 && v3 && v4;
}

// Real-time validation on blur
["inputName", "inputEmail", "inputCompany", "inputWebsite"].forEach(id => {
    const el = document.getElementById(id);
    el.addEventListener("blur", () => {
        // Trigger validation for this specific field
        form.dispatchEvent(new Event("validateField_" + id));
    });
    el.addEventListener("input", () => {
        // Remove invalid state while typing
        el.classList.remove("invalid");
        const errId = "err" + id.replace("input", "");
        const errEl = document.getElementById(errId);
        if (errEl) errEl.textContent = "";
    });
});

// ============================================================
// FORM SUBMISSION
// ============================================================
let lastFormData = null; // For retry functionality

form.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!validateAll()) {
        showToast("Please fix the errors before submitting.", "error");
        return;
    }

    const data = {
        name:    document.getElementById("inputName").value.trim(),
        email:   document.getElementById("inputEmail").value.trim(),
        company: document.getElementById("inputCompany").value.trim(),
        website: document.getElementById("inputWebsite").value.trim(),
    };

    lastFormData = data;
    await submitLead(data);
});

async function submitLead(data) {
    // Switch to processing page
    showPage("page-processing");
    startProcessingAnimation();

    try {
        // Health check using AbortController for broad browser compatibility
        let healthOk = false;
        try {
            const hc = new AbortController();
            const hcTimeout = setTimeout(() => hc.abort(), 5000);
            const healthRes = await fetch(`${API_BASE}/health`, { signal: hc.signal });
            clearTimeout(hcTimeout);
            healthOk = healthRes.ok;
        } catch (_) {
            healthOk = false;
        }

        if (!healthOk) {
            throw new Error("Cannot reach the backend server. Make sure it is running: python app.py");
        }

        // Main API call with 2-minute timeout via AbortController
        const ac = new AbortController();
        const acTimeout = setTimeout(() => ac.abort(), 120000);

        const response = await fetch(`${API_BASE}/generate-report`, {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify(data),
            signal:  ac.signal,
        });
        clearTimeout(acTimeout);

        const result = await response.json();
        stopProcessingAnimation();

        if (response.ok && result.status === "success") {
            renderSuccessPage(result, data);  // populate the success page with report data
            showPage("page-success");
        } else {
            const errMsg = result.errors
                ? result.errors.join(" \u2022 ")
                : (result.message || "An unexpected error occurred.");
            showErrorPage(errMsg);
        }

    } catch (err) {
        stopProcessingAnimation();
        let message = "An unexpected error occurred. Please try again.";
        if (err.name === "AbortError") {
            message = "Request timed out. The AI pipeline is taking longer than expected. Please retry.";
        } else if (err.message && (err.message.includes("fetch") || err.message.includes("network") || err.message.includes("connect"))) {
            message = "Could not connect to the backend. Make sure the Flask server is running: python app.py";
        } else if (err.message) {
            message = err.message;
        }
        showErrorPage(message);
    }
}

// ============================================================
// RETRY
// ============================================================
function retrySubmission() {
    if (lastFormData) {
        submitLead(lastFormData);
    } else {
        showPage("page-form");
    }
}

// ============================================================
// ERROR PAGE
// ============================================================
function showErrorPage(message) {
    document.getElementById("errorMessage").textContent = message;
    showPage("page-error");
}

// ============================================================
// SUCCESS PAGE — Render Report Data
// ============================================================
function renderSuccessPage(result, lead) {
    const data = result.data || {};
    const emailSent = data.email_sent;

    // Update the success message
    const msgEl = document.querySelector("#page-success .result-wrapper p");
    if (msgEl) {
        msgEl.textContent = emailSent
            ? `The AI-generated report for ${lead.company} has been delivered to ${lead.email}. Check your inbox!`
            : `The report for ${lead.company} was generated successfully. Email delivery failed — please check your SMTP settings.`;
    }

    // Show report preview if AI report data exists
    const reportData = result.report_data;
    const previewContainer = document.getElementById("reportPreview");
    if (!previewContainer) return;

    if (reportData) {
        let html = `<div class="report-preview">`;
        html += `<h3 class="report-preview-title">📊 Report Preview: ${reportData.company_name || lead.company}</h3>`;

        if (reportData.company_overview) {
            html += `<div class="report-section"><h4>Company Overview</h4><p>${reportData.company_overview}</p></div>`;
        }
        if (reportData.key_strengths?.length) {
            html += `<div class="report-section"><h4>Key Strengths</h4><ul>${reportData.key_strengths.map(s => `<li>${s}</li>`).join("")}</ul></div>`;
        }
        if (reportData.growth_opportunities?.length) {
            html += `<div class="report-section"><h4>Growth Opportunities</h4><ul>${reportData.growth_opportunities.map(o => `<li>${o}</li>`).join("")}</ul></div>`;
        }
        if (reportData.strategic_recommendations?.length) {
            html += `<div class="report-section"><h4>Strategic Recommendations</h4><ul>${reportData.strategic_recommendations.map(r => `<li>${r}</li>`).join("")}</ul></div>`;
        }
        html += `</div>`;
        previewContainer.innerHTML = html;
        previewContainer.style.display = "block";
    } else {
        // Show minimal info
        previewContainer.innerHTML = `<div class="report-section"><p>✅ PDF report saved at:<br><code>${data.pdf_path || "reports/ folder"}</code></p><p style="margin-top:8px;color:var(--text-secondary)">Request ID: <strong>${result.request_id || ""}</strong></p></div>`;
        previewContainer.style.display = "block";
    }
}

// ============================================================
// PROCESSING ANIMATION
// ============================================================
let processingTimers = [];
let countdownInterval = null;
let quoteInterval    = null;

const STEP_DELAYS = [0, 3000, 8000, 20000]; // ms to mark each step done
const STEP_DURATIONS = [3000, 5000, 12000, 8000]; // active duration per step

function startProcessingAnimation() {
    // Reset all steps
    for (let i = 1; i <= 4; i++) {
        const step = document.getElementById(`proc-step-${i}`);
        step.classList.remove("done", "active");
        step.querySelector(".proc-dot").textContent = "";
    }

    // Animate steps sequentially
    let totalTime = 0;
    for (let i = 1; i <= 4; i++) {
        const delay = STEP_DELAYS[i - 1];
        totalTime = delay + STEP_DURATIONS[i - 1];

        // Mark as active after delay
        const t1 = setTimeout(() => {
            document.getElementById(`proc-step-${i}`).classList.add("active");
        }, delay);

        // Mark previous as done
        if (i > 1) {
            const t2 = setTimeout(() => {
                document.getElementById(`proc-step-${i - 1}`).classList.remove("active");
                document.getElementById(`proc-step-${i - 1}`).classList.add("done");
            }, delay);
            processingTimers.push(t2);
        }
        processingTimers.push(t1);
    }

    // Countdown timer
    let seconds = 40;
    const timerEl = document.getElementById("timerCountdown");
    timerEl.textContent = `${seconds} SECONDS`;
    countdownInterval = setInterval(() => {
        seconds = Math.max(0, seconds - 1);
        timerEl.textContent = seconds > 0 ? `${seconds} SECONDS` : "FINALIZING...";
    }, 1000);

    // Rotating quotes
    const quoteEl = document.getElementById("rotatingQuote");
    let qIdx = 0;
    quoteEl.textContent = PROCESSING_QUOTES[0];
    quoteInterval = setInterval(() => {
        qIdx = (qIdx + 1) % PROCESSING_QUOTES.length;
        quoteEl.style.opacity = "0";
        setTimeout(() => {
            quoteEl.textContent = PROCESSING_QUOTES[qIdx];
            quoteEl.style.opacity = "1";
        }, 300);
    }, 8000);

    // Smooth opacity on quote
    quoteEl.style.transition = "opacity 0.3s ease";
}

function stopProcessingAnimation() {
    // Clear all timers
    processingTimers.forEach(t => clearTimeout(t));
    processingTimers = [];
    if (countdownInterval) clearInterval(countdownInterval);
    if (quoteInterval)    clearInterval(quoteInterval);

    // Mark all steps done
    for (let i = 1; i <= 4; i++) {
        const step = document.getElementById(`proc-step-${i}`);
        step.classList.remove("active");
        step.classList.add("done");
    }
    document.getElementById("timerCountdown").textContent = "DONE";
}

// ============================================================
// TOAST NOTIFICATION
// ============================================================
let toastTimer = null;

function showToast(message, type = "default") {
    let toast = document.getElementById("globalToast");
    if (!toast) {
        toast = document.createElement("div");
        toast.className = "toast";
        toast.id = "globalToast";
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.className = `toast ${type}`;

    // Show
    clearTimeout(toastTimer);
    requestAnimationFrame(() => {
        requestAnimationFrame(() => toast.classList.add("show"));
    });

    // Auto-hide after 3.5s
    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 3500);
}
