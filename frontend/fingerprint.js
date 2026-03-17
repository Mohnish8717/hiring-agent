/**
 * Production-Grade Device Fingerprinting Collector
 * Collects browser signals and submits them to the backend API.
 */

const FingerprintCollector = {
    /**
     * Collects all hardware and software browser signals.
     */
    async collect() {
        return {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            screenResolution: `${window.screen.width}x${window.screen.height}`,
            colorDepth: window.screen.colorDepth,
            hardwareConcurrency: navigator.hardwareConcurrency || 0,
            deviceMemory: navigator.deviceMemory || 0,
            cookiesEnabled: navigator.cookieEnabled,
            canvasFingerprint: this.getCanvasFingerprint(),
            webglVendor: this.getWebGlSignals().vendor,
            webglRenderer: this.getWebGlSignals().renderer,
            isHeadless: this.detectHeadless(),
            webdriver: navigator.webdriver || false
        };
    },

    /**
     * Generates a unique canvas drawing to capture GPU rendering nuances.
     */
    getCanvasFingerprint() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        if (!ctx) return 'not_supported';
        
        canvas.width = 200;
        canvas.height = 50;
        ctx.textBaseline = "top";
        ctx.font = "14px 'Arial'";
        ctx.fillStyle = "#f60";
        ctx.fillRect(125,1,62,20);
        ctx.fillStyle = "#069";
        ctx.fillText("IdentityTrust <fingerprint>", 2, 15);
        ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
        ctx.fillText("IdentityTrust <fingerprint>", 4, 17);
        
        return canvas.toDataURL();
    },

    /**
     * Extracts WebGL hardware info.
     */
    getWebGlSignals() {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) return { vendor: 'none', renderer: 'none' };
        
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (!debugInfo) return { vendor: 'unknown', renderer: 'unknown' };
        
        return {
            vendor: gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL),
            renderer: gl.getParameter(debugInfo.UNMASKED_RENDER_INFO_WEBGL)
        };
    },

    /**
     * Simple heuristics for headless browser detection.
     */
    detectHeadless() {
        if (navigator.webdriver) return true;
        if (window.chrome && !window.chrome.runtime) return true;
        if (!navigator.languages || navigator.languages.length === 0) return true;
        return false;
    },

    /**
     * Submits signals to the backend.
     */
    async submit(apiUrl = '/api/device-fingerprint') {
        try {
            const signals = await this.collect();
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(signals)
            });
            
            if (!response.ok) throw new Error('Submission failed');
            return await response.json();
        } catch (error) {
            console.error('Fingerprint submission error:', error);
            return null;
        }
    }
};

// Auto-run if embedded in page
// FingerprintCollector.submit();
