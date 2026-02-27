"""
Email servisi — Resend API entegrasyonu.

Fiyat alarmları, buybox kaybı ve kampanya bildirimleri için email gönderir.
"""

import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

_resend_client = None


def _get_resend():
    global _resend_client
    if _resend_client is None:
        import resend
        api_key = (settings.RESEND_API_KEY or "").strip()
        if not api_key:
            logger.warning("RESEND_API_KEY ayarlanmadı — email gönderilemeyecek")
            return None
        resend.api_key = api_key
        _resend_client = resend
    return _resend_client


FROM_EMAIL = "MarketPulse <alerts@marketpulse.app>"


async def send_email(to: str, subject: str, html_body: str) -> bool:
    """Generic email gönderme."""
    client = _get_resend()
    if not client:
        logger.warning(f"Email gönderilemedi (Resend yapılandırılmamış): {subject}")
        return False

    try:
        client.Emails.send({
            "from": FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html_body,
        })
        logger.info(f"Email gönderildi: {to} — {subject}")
        return True
    except Exception as e:
        logger.error(f"Email gönderim hatası: {e}")
        return False


async def send_price_alert_email(
    to_email: str,
    product_name: str,
    sku: str,
    platform: str,
    merchant_name: str,
    old_price: float,
    new_price: float,
    threshold: float,
) -> bool:
    """Fiyat değişimi uyarı emaili."""
    change_pct = abs(new_price - old_price) / old_price * 100 if old_price else 0
    direction = "düştü" if new_price < old_price else "arttı"

    subject = f"Fiyat Alarmı: {product_name or sku} fiyatı %{change_pct:.0f} {direction}"

    html = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #f0fdf4, #dcfce7); border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <h1 style="color: #166534; margin: 0 0 8px;">Fiyat Alarmı</h1>
            <p style="color: #15803d; margin: 0;">Takip ettiğiniz ürünün fiyatı değişti.</p>
        </div>

        <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px; margin-bottom: 16px;">
            <h2 style="color: #1f2937; margin: 0 0 12px; font-size: 16px;">{product_name or 'Ürün'}</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Platform</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{platform.capitalize()}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">SKU</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{sku}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Satıcı</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{merchant_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Eski Fiyat</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{old_price:.2f} ₺</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Yeni Fiyat</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right; color: {'#dc2626' if new_price > old_price else '#16a34a'};">{new_price:.2f} ₺</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Eşik Değer</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{threshold:.2f} ₺</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Değişim</td>
                    <td style="padding: 8px 0; font-weight: 700; text-align: right; color: {'#dc2626' if new_price > old_price else '#16a34a'};">%{change_pct:.1f} {direction}</td>
                </tr>
            </table>
        </div>

        <p style="color: #9ca3af; font-size: 12px; text-align: center; margin-top: 24px;">
            Bu email MarketPulse fiyat takip sistemi tarafından gönderilmiştir.
        </p>
    </div>
    """

    return await send_email(to_email, subject, html)


async def send_buybox_lost_email(
    to_email: str,
    product_name: str,
    sku: str,
    platform: str,
    old_winner: str,
    new_winner: str,
    new_winner_price: float,
) -> bool:
    """Buybox kaybı uyarı emaili."""
    subject = f"Buybox Kaybı: {product_name or sku}"

    html = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #fef2f2, #fecaca); border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <h1 style="color: #991b1b; margin: 0 0 8px;">Buybox Kaybı</h1>
            <p style="color: #b91c1c; margin: 0;">Bir ürünün buybox'ını kaybettiniz.</p>
        </div>

        <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px;">
            <h2 style="color: #1f2937; margin: 0 0 12px; font-size: 16px;">{product_name or 'Ürün'}</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Platform</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{platform.capitalize()}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">SKU</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{sku}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Eski Winner</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{old_winner}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Yeni Winner</td>
                    <td style="padding: 8px 0; font-weight: 700; text-align: right; color: #dc2626;">{new_winner}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Winner Fiyatı</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{new_winner_price:.2f} ₺</td>
                </tr>
            </table>
        </div>

        <p style="color: #9ca3af; font-size: 12px; text-align: center; margin-top: 24px;">
            Bu email MarketPulse fiyat takip sistemi tarafından gönderilmiştir.
        </p>
    </div>
    """

    return await send_email(to_email, subject, html)


async def send_campaign_alert_email(
    to_email: str,
    product_name: str,
    sku: str,
    platform: str,
    merchant_name: str,
    campaign_price: float,
    threshold: float,
) -> bool:
    """Kampanya fiyat uyarısı emaili."""
    subject = f"Kampanya Alarmı: {product_name or sku} — {campaign_price:.2f} ₺"

    html = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #fffbeb, #fef3c7); border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <h1 style="color: #92400e; margin: 0 0 8px;">Kampanya Alarmı</h1>
            <p style="color: #b45309; margin: 0;">Bir rakip kampanyaya girdi!</p>
        </div>

        <div style="background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px;">
            <h2 style="color: #1f2937; margin: 0 0 12px; font-size: 16px;">{product_name or 'Ürün'}</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Platform</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{platform.capitalize()}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">SKU</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{sku}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Satıcı</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{merchant_name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Kampanya Fiyatı</td>
                    <td style="padding: 8px 0; font-weight: 700; text-align: right; color: #dc2626;">{campaign_price:.2f} ₺</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">Eşik Değer</td>
                    <td style="padding: 8px 0; font-weight: 600; text-align: right;">{threshold:.2f} ₺</td>
                </tr>
            </table>
        </div>

        <p style="color: #9ca3af; font-size: 12px; text-align: center; margin-top: 24px;">
            Bu email MarketPulse fiyat takip sistemi tarafından gönderilmiştir.
        </p>
    </div>
    """

    return await send_email(to_email, subject, html)
