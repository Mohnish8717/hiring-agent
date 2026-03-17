"""Module 11: DeviceFingerprintAnalyzer — Detects suspicious device signals."""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("identity_trust.device_fingerprint")


class DeviceFingerprintAnalyzer:
    """Analyzes device and network signals for fraud indicators.

    Refactored to consume structured metadata produced by the production-grade
    fingerprinting pipeline (frontend/fingerprint.js + api/fingerprint_api.py).
    """

    def analyze(self, fingerprint_metadata: Dict[str, Any] | None = None) -> Optional[float]:
        """Returns a device trust score (0-10) or None if metadata is missing."""
        if not fingerprint_metadata:
            logger.info("DeviceFingerprint: no metadata available")
            return None

        score = 8.0  # Base trust for typical devices

        # --- Headless Browser Detection (-4.0) ---
        if fingerprint_metadata.get("headless_browser", False):
            score -= 4.0
            logger.warning(f"DeviceFingerprint: Headless browser detected (Device: {fingerprint_metadata.get('device_id', 'unknown')})")

        # --- VPN / Proxy Detection (-2.0) ---
        if fingerprint_metadata.get("vpn_detected", False):
            score -= 2.0
            logger.info("DeviceFingerprint: VPN or Proxy detected")

        # --- IP vs Resume Location Mismatch (-1.5) ---
        ip_country = fingerprint_metadata.get("ip_country")
        resume_country = fingerprint_metadata.get("resume_country")
        if ip_country and resume_country and ip_country.lower() != resume_country.lower():
            score -= 1.5
            logger.info(f"DeviceFingerprint: Location mismatch (IP: {ip_country}, Resume: {resume_country})")

        # --- Device Velocity ---
        # Highly repetitive submissions from the same ID are a fraud signal
        same_device_apps = fingerprint_metadata.get("same_device_applications", 1)
        if same_device_apps > 10:
            score -= 3.0
            logger.warning(f"DeviceFingerprint: High application velocity ({same_device_apps})")
        elif same_device_apps > 3:
            score -= 1.0

        score = max(0.0, min(10.0, score))
        logger.info(f"DeviceFingerprint: score={score:.1f}")
        
        return round(score, 1)  # type: ignore
