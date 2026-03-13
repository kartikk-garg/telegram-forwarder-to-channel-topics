"""
Message Formatting — V2.1 (Clean Layout)
Telegram message formatting with expanded data display.
Refined for a cleaner, premium look with 1h volume prominence.

Usage:
    python execution/format_message.py
"""


# ---------------------------------------------------------------------------
# Price / Number Formatters
# ---------------------------------------------------------------------------

def format_price(num):
    """Formats price — handles sub-cent crypto prices."""
    if not num: return "$0"
    num = float(num)
    if num > 1: return f"${num:.2f}"
    return f"${num:.8f}".rstrip('0')

def human_format(num):
    """Converts number to human-readable: $1.2M, $45K, etc."""
    if not num: return "$0"
    num = float(num)
    if num >= 1_000_000: return f"${num / 1_000_000:.1f}M"
    if num >= 1_000: return f"${num / 1_000:.1f}K"
    return f"${num:.1f}"

def pct_fmt(val):
    """Formats percentage — None-safe."""
    if val is None: return "—"
    return f"{val:+.1f}%"


# ---------------------------------------------------------------------------
# Social Links
# ---------------------------------------------------------------------------

def build_social_links(websites, socials):
    """Builds formatted social links string."""
    links = []
    # websites or socials might be None or list
    if websites:
        for site in websites:
            label = site.get('label', 'Web').capitalize()
            links.append(f"[{label}]({site['url']})")
    if socials:
        for social in socials:
            type_name = social.get('type', 'Social').capitalize()
            if 'twitter' in type_name.lower(): type_name = "Twitter"
            elif 'telegram' in type_name.lower(): type_name = "TG"
            links.append(f"[{type_name}]({social['url']})")
    return " | ".join(links) if links else "Links: N/A"


# ---------------------------------------------------------------------------
# Token Info Block (Header)
# ---------------------------------------------------------------------------

def build_token_info(d):
    """Main token info block: symbol, price, mcap, age."""
    symbol = d.get('symbol', '?')
    name = d.get('token_name', '')
    price = format_price(d.get('price', 0))
    mcap = human_format(d.get('mcap', 0))
    
    age_str = ""
    age_h = d.get('token_age_hours', 0)
    if age_h > 0:
        if age_h < 1: age_str = f"{age_h * 60:.0f}m old"
        elif age_h < 24: age_str = f"{age_h:.1f}h old"
        else: age_str = f"{age_h / 24:.1f}d old"
    
    market = d.get('primary_market', '')
    market_tag = "PumpFun" if 'pump' in market.lower() else ("Raydium" if 'ray' in market.lower() else "DEX")

    return (
        f"💎 **{symbol}** ({name})\n"
        f"Price: `{price}` | MC: **{mcap}**\n"
        f"Platform: {market_tag} | Age: {age_str}"
    )


# ---------------------------------------------------------------------------
# Market & Volume Line (Cleaned)
# ---------------------------------------------------------------------------

def build_market_line(d):
    """Unified volume and market stats."""
    vol1h = human_format(d.get('vol_h1', 0))
    vol24h = human_format(d.get('volume_24h', 0))
    ratio1h = d.get('vol_mcap_ratio', 0) # 1h ratio from DexScreener
    holders = d.get('holders', 0)
    
    return (
        f"📊 **Vol 1h:** {vol1h} (Ratio: {ratio1h:.1f}%) | **24h:** {vol24h}\n"
        f"Holders: {holders} | LPs: {human_format(d.get('liquidity', 0))}"
    )


# ---------------------------------------------------------------------------
# Price Change Line
# ---------------------------------------------------------------------------

def build_price_change_line(d):
    """Price changes across timeframes."""
    changes = []
    items = [("1m", "price_change_1m"), ("5m", "price_change_5m"), ("1h", "price_change_1h"), ("6h", "price_change_6h")]
    for label, key in items:
        val = d.get(key)
        if val is not None:
            emoji = "🟢" if val > 0 else "🔴"
            changes.append(f"{label}: {emoji}{val:+.1f}%")
    
    if not changes: return ""
    return "📈 " + " | ".join(changes)


# ---------------------------------------------------------------------------
# Risk Summary Line (Condensed)
# ---------------------------------------------------------------------------

def build_risk_line(d):
    """Risk summary: Score, Bundlers, Snipers, Top10."""
    score = d.get('risk_score', 0)
    top10 = d.get('top10_holder_pct', 0)
    bundler_count = d.get('bundler_count', 0)
    bundler_pct = d.get('bundler_pct', 0)
    sniper_count = d.get('sniper_count', 0)
    insider_count = d.get('insider_count', 0)

    # Emoji based on score
    risk_emoji = "✅" if score < 3 else ("⚠️" if score < 7 else "🚨")
    
    return (
        f"{risk_emoji} **Risk Score: {score}/10** | Top10: {top10}%\n"
        f"Bundlers: {bundler_count} ({bundler_pct}%) | Snipers: {sniper_count} | Insiders: {insider_count}"
    )


# ---------------------------------------------------------------------------
# Bot Fees Line
# ---------------------------------------------------------------------------

def build_fees_line(d):
    """Condensed bot fees."""
    total = d.get('fees_total_trading', 0)
    if total < 1: return ""
    
    fees = {
        'Padre': d.get('fees_padre', 0), 'Axiom': d.get('fees_axiom', 0),
        'Photon': d.get('fees_photon', 0), 'GMGN': d.get('fees_gmgn', 0),
        'Trojan': d.get('fees_trojan', 0)
    }
    # Only show bots > 0.5 SOL
    active = [f"{k}: {v:.1f}◎" for k, v in fees.items() if v > 0.5]
    if not active: return f"🤖 Bot Fees: {total:.1f}◎"
    
    return f"🤖 Bots: {' | '.join(active[:3])} (Total: {total:.1f}◎)"


# ---------------------------------------------------------------------------
# Full Call Message
# ---------------------------------------------------------------------------

def build_call_message(call_tag, ch_name, token_data, original_text="", reply_context=""):
    """
    Builds the complete Telegram message for a forwarded call.
    Refined for clarity and professionalism.
    """
    ca = token_data.get('real_ca', token_data.get('ca', ''))
    maestro_link = f"https://t.me/MaestroSniperBot?start={ca}"
    dex_link = f"https://dexscreener.com/solana/{ca}"

    # Header section
    header = f"{call_tag} from **{ch_name}**"
    
    # Original text (shortened)
    original_section = ""
    if original_text:
        clean_text = original_text.replace("\n", " ").strip()
        if len(clean_text) > 80: clean_text = clean_text[:77] + "..."
        original_section = f"💬 _{clean_text}_\n"

    # Social links
    social_text = build_social_links(token_data.get('websites'), token_data.get('socials'))

    # Message Construction
    parts = [
        header,
        original_section,
        "─" * 15,
        build_token_info(token_data),
        build_market_line(token_data),
        build_price_change_line(token_data),
        build_risk_line(token_data),
        build_fees_line(token_data),
        "─" * 15,
        f"`{ca}`",
        reply_context if reply_context else "",
        f"{social_text}",
        f"🚀 [Maestro]({maestro_link}) | 📊 [DexScreener]({dex_link})"
    ]

    return "\n".join(part for part in parts if part)


# ---------------------------------------------------------------------------
# Report Message
# ---------------------------------------------------------------------------

def build_report_message(leaderboard_rows, best_call=None):
    """Builds the enhanced weekly leaderboard report."""
    if not leaderboard_rows:
        return "⚠️ **Weekly Report:** Not enough data collected yet."
    
    lines = []
    for row in leaderboard_rows:
        total = row['total']
        wins = row['wins']
        win_pct = int(wins / total * 100) if total > 0 else 0
        best_x = round(row.get('best_x', 0) or 0, 1)
        calls_day = round(row.get('calls_per_day', 0) or 0, 1)
        speed = row.get('avg_speed_to_2x')
        speed_str = f"{speed:.1f}h" if speed else "—"
        
        lines.append(
            f"• **{row['channel_name']}**: {total} calls ({calls_day}/day) | "
            f"{win_pct}% win | {best_x}x peak | ⚡{speed_str}"
        )
    
    report = (
        f"📊 **Weekly Alpha Leaderboard**\n"
        f"Last 7 days of performance\n\n"
        + "\n".join(lines) +
        f"\n\n_Wins = Calls hitting > 2x | ⚡ = Avg time to 2x_"
    )

    # Best Call of the Week highlight
    if best_call:
        bc_sym = best_call.get('symbol', '?')
        bc_peak = round(best_call.get('peak_multiplier', 0) or 0, 1)
        bc_ch = best_call.get('channel_name', '?')
        bc_time = best_call.get('time_to_peak_hours')
        bc_time_str = f" in {bc_time:.1f}h" if bc_time else ""
        bc_risk = best_call.get('risk_score', '?')
        report += (
            f"\n\n🏆 **Best Call:** ${bc_sym} ({bc_peak}x{bc_time_str}) "
            f"from {bc_ch} | Risk: {bc_risk}/10"
        )

    return report

