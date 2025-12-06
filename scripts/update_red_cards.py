#!/usr/bin/env python3
"""
Script to automatically update red card statistics for Benfica, Sporting and Porto.
Uses API-Football (free tier: 100 requests/day) as primary source.
Falls back to manual configuration if API is unavailable.

Setup:
1. Create free account at https://www.api-football.com/
2. Get your API key from the dashboard
3. Set RAPIDAPI_KEY environment variable or GitHub secret
"""

import os
import re
import json
import requests
from datetime import datetime, date, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, List
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# API-Football configuration (RapidAPI)
API_FOOTBALL_HOST = "api-football-v1.p.rapidapi.com"
API_FOOTBALL_BASE_URL = f"https://{API_FOOTBALL_HOST}/v3"

# Portuguese Primeira Liga ID in API-Football
PRIMEIRA_LIGA_ID = 94

# Team IDs in API-Football
TEAM_IDS = {
    "benfica": 211,
    "sporting": 228,
    "porto": 212,
}

# Headers for API requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


@dataclass
class RedCardEvent:
    """Represents a red card event"""
    player: str
    date: date
    match: str  # e.g., "Alverca 1 - 2 Benfica"
    minute: str  # e.g., "70'"
    card_type: str  # "Red Card" or "Second Yellow"
    team: str
    
    def to_iso_date(self) -> str:
        return self.date.strftime("%Y-%m-%d")
    
    def to_display_date(self) -> str:
        months_pt = {
            1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
            5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
            9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
        }
        return f"{self.date.day} {months_pt[self.date.month]} {self.date.year}"


def get_api_key() -> Optional[str]:
    """Get API key from environment variable"""
    return os.environ.get("RAPIDAPI_KEY") or os.environ.get("API_FOOTBALL_KEY")


def fetch_api_football(endpoint: str, params: dict = None) -> Optional[dict]:
    """Fetch data from API-Football"""
    api_key = get_api_key()
    if not api_key:
        print("⚠️  No API key found. Set RAPIDAPI_KEY environment variable.")
        return None
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": API_FOOTBALL_HOST,
    }
    
    url = f"{API_FOOTBALL_BASE_URL}/{endpoint}"
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get("errors"):
            print(f"⚠️  API Error: {data['errors']}")
            return None
        
        return data
    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return None


def get_current_season() -> int:
    """Get current football season year (e.g., 2024 for 2024/25 season)"""
    today = date.today()
    # Season starts in August
    if today.month < 8:
        return today.year - 1
    return today.year


def get_team_fixtures(team_id: int, season: int) -> List[dict]:
    """Get all fixtures for a team in a season"""
    data = fetch_api_football("fixtures", {
        "team": team_id,
        "league": PRIMEIRA_LIGA_ID,
        "season": season,
    })
    
    if not data:
        return []
    
    return data.get("response", [])


def get_fixture_events(fixture_id: int) -> List[dict]:
    """Get all events (goals, cards, etc.) for a fixture"""
    data = fetch_api_football("fixtures/events", {
        "fixture": fixture_id,
    })
    
    if not data:
        return []
    
    return data.get("response", [])


def find_red_cards_for_team(team_key: str, season: int) -> List[RedCardEvent]:
    """Find all red cards (direct + second yellow) for a team in the season"""
    team_id = TEAM_IDS.get(team_key)
    if not team_id:
        print(f"❌ Unknown team: {team_key}")
        return []
    
    print(f"📊 Fetching fixtures for {team_key.title()} (season {season}/{season+1})...")
    fixtures = get_team_fixtures(team_id, season)
    
    if not fixtures:
        print(f"   No fixtures found")
        return []
    
    print(f"   Found {len(fixtures)} fixtures")
    
    red_cards = []
    
    # Only check completed matches (status = FT, AET, PEN)
    completed_fixtures = [f for f in fixtures if f["fixture"]["status"]["short"] in ["FT", "AET", "PEN"]]
    print(f"   {len(completed_fixtures)} completed matches")
    
    for fixture in completed_fixtures:
        fixture_id = fixture["fixture"]["id"]
        fixture_date = datetime.strptime(fixture["fixture"]["date"][:10], "%Y-%m-%d").date()
        
        home_team = fixture["teams"]["home"]["name"]
        away_team = fixture["teams"]["away"]["name"]
        home_goals = fixture["goals"]["home"] or 0
        away_goals = fixture["goals"]["away"] or 0
        match_str = f"{home_team} {home_goals} - {away_goals} {away_team}"
        
        # Get events for this fixture
        events = get_fixture_events(fixture_id)
        
        for event in events:
            # Check if it's a card event for our team
            if event.get("team", {}).get("id") != team_id:
                continue
            
            event_type = event.get("type", "")
            event_detail = event.get("detail", "")
            
            # Check for red cards (direct red or second yellow)
            if event_type == "Card" and event_detail in ["Red Card", "Second Yellow card"]:
                player_name = event.get("player", {}).get("name", "Unknown")
                minute = f"{event.get('time', {}).get('elapsed', '?')}'"
                
                card_type = "Red Card" if event_detail == "Red Card" else "Second Yellow"
                
                red_card = RedCardEvent(
                    player=player_name,
                    date=fixture_date,
                    match=match_str,
                    minute=minute,
                    card_type=card_type,
                    team=team_key,
                )
                red_cards.append(red_card)
                print(f"   🔴 Found: {player_name} ({minute}) - {match_str}")
    
    # Sort by date, most recent first
    red_cards.sort(key=lambda x: x.date, reverse=True)
    
    return red_cards


def count_reds_since_date(team_key: str, since_date: date, season: int) -> int:
    """Count red cards for a team since a specific date"""
    all_reds = find_red_cards_for_team(team_key, season)
    return len([r for r in all_reds if r.date >= since_date])


def read_current_html() -> str:
    """Read current index.html content"""
    html_path = Path("index.html")
    if not html_path.exists():
        # Try from scripts directory
        html_path = Path(__file__).parent.parent / "index.html"
    
    with open(html_path, 'r', encoding='utf-8') as f:
        return f.read()


def get_current_last_red_date() -> Optional[date]:
    """Extract current last red card date from index.html"""
    content = read_current_html()
    match = re.search(r'LAST_RED_CARD_ISO_DATE\s*=\s*"(\d{4}-\d{2}-\d{2})"', content)
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    return None


def update_html(
    new_date: str,
    new_player: str,
    new_match: str,
    new_minute: str,
    card_type: str,
    sporting_reds: int,
    porto_reds: int
):
    """Update index.html with new red card data"""
    
    html_path = Path("index.html")
    if not html_path.exists():
        html_path = Path(__file__).parent.parent / "index.html"
    
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update the JavaScript date constant
    content = re.sub(
        r'const LAST_RED_CARD_ISO_DATE = "[^"]+";',
        f'const LAST_RED_CARD_ISO_DATE = "{new_date}";',
        content
    )
    
    # Determine card icon based on type
    if card_type == "Second Yellow":
        card_icon = '<img src="https://static.files.bbci.co.uk/core/website/assets/static/sport/football/second-yellow-card.face6badd0.svg" alt="Segundo Amarelo" style="height: 1.2em; vertical-align: middle; margin-left: 0.3rem;">'
    else:
        card_icon = '<img src="https://static.files.bbci.co.uk/core/website/assets/static/sport/football/red-card.d7b89be4ae.svg" alt="Vermelho Directo" style="height: 1.2em; vertical-align: middle; margin-left: 0.3rem;">'
    
    # Parse date for display
    date_obj = datetime.strptime(new_date, "%Y-%m-%d")
    months_pt = {
        1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
        5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
        9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
    }
    display_date = f"{date_obj.day} {months_pt[date_obj.month]} {date_obj.year}"
    
    # Build new last-expulsion content
    new_expulsion_html = f'{display_date} - {new_player} - {new_minute} \n    {card_icon}\n    ({new_match})'
    
    # Update last-expulsion div
    content = re.sub(
        r'<div class="last-expulsion">\s*[^<]*\s*<img[^>]*>\s*\([^)]+\)\s*</div>',
        f'<div class="last-expulsion">\n    {new_expulsion_html}\n  </div>',
        content,
        flags=re.DOTALL
    )
    
    # Update Sporting red cards count
    content = re.sub(
        r'O Sporting viu \d+ vermelhos',
        f'O Sporting viu {sporting_reds} vermelhos',
        content
    )
    
    # Update Porto red cards count  
    content = re.sub(
        r'O Porto viu \d+ vermelhos',
        f'O Porto viu {porto_reds} vermelhos',
        content
    )
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ Updated index.html:")
    print(f"   📅 Date: {display_date}")
    print(f"   👤 Player: {new_player}")
    print(f"   ⚽ Match: {new_match}")
    print(f"   🟢 Sporting reds since: {sporting_reds}")
    print(f"   🔵 Porto reds since: {porto_reds}")


def run_api_update():
    """Run full update using API-Football"""
    season = get_current_season()
    
    print(f"🔄 Running API-Football update...")
    print(f"📅 Season: {season}/{season+1}")
    print()
    
    # Get Benfica red cards
    benfica_reds = find_red_cards_for_team("benfica", season)
    
    if not benfica_reds:
        # Also check previous season
        print(f"\n📊 No reds this season, checking previous season...")
        benfica_reds = find_red_cards_for_team("benfica", season - 1)
    
    if not benfica_reds:
        print("❌ No Benfica red cards found. Check API connection.")
        return False
    
    # Get the most recent red card
    last_red = benfica_reds[0]
    print(f"\n🔴 Last Benfica red card:")
    print(f"   {last_red.player} - {last_red.to_display_date()}")
    print(f"   {last_red.match} ({last_red.minute})")
    
    # Count Sporting and Porto reds since Benfica's last red
    print()
    sporting_count = count_reds_since_date("sporting", last_red.date, season)
    porto_count = count_reds_since_date("porto", last_red.date, season)
    
    # Update HTML
    update_html(
        new_date=last_red.to_iso_date(),
        new_player=last_red.player,
        new_match=last_red.match,
        new_minute=last_red.minute,
        card_type=last_red.card_type,
        sporting_reds=sporting_count,
        porto_reds=porto_count,
    )
    
    return True


def run_check_only():
    """Just check current status without updating"""
    print("🔍 Checking current status...")
    
    current_date = get_current_last_red_date()
    if current_date:
        days_since = (date.today() - current_date).days
        print(f"📅 Last Benfica red card: {current_date.isoformat()}")
        print(f"📆 Days since: {days_since}")
    else:
        print("⚠️  Could not read current date from index.html")
    
    api_key = get_api_key()
    if api_key:
        print("✅ API key found")
    else:
        print("⚠️  No API key - set RAPIDAPI_KEY to enable automatic updates")


# =============================================================================
# MANUAL UPDATE SECTION
# =============================================================================
# For manual updates when API is unavailable, modify these values and run:
#   python scripts/update_red_cards.py --manual

MANUAL_DATA = {
    "enabled": False,  # Set to True to apply manual update
    "date": "2025-08-31",  # ISO format YYYY-MM-DD
    "player": "Amar Dedić",
    "match": "Alverca 1 - 2 Benfica",
    "minute": "70'",
    "card_type": "Second Yellow",  # "Red Card" or "Second Yellow"
    "sporting_reds": 0,
    "porto_reds": 0,
}


def run_manual_update():
    """Apply manual update from MANUAL_DATA"""
    if not MANUAL_DATA["enabled"]:
        print("⚠️  Manual update is disabled.")
        print("   Edit MANUAL_DATA in this file and set 'enabled': True")
        return False
    
    print("📝 Applying manual update...")
    update_html(
        new_date=MANUAL_DATA["date"],
        new_player=MANUAL_DATA["player"],
        new_match=MANUAL_DATA["match"],
        new_minute=MANUAL_DATA["minute"],
        card_type=MANUAL_DATA["card_type"],
        sporting_reds=MANUAL_DATA["sporting_reds"],
        porto_reds=MANUAL_DATA["porto_reds"],
    )
    return True


# =============================================================================
# MAIN
# =============================================================================

def main():
    import sys
    
    print("=" * 60)
    print("🔴 Zero Vermelhos - Red Card Update Script")
    print("=" * 60)
    print()
    
    if "--manual" in sys.argv:
        run_manual_update()
    elif "--check" in sys.argv:
        run_check_only()
    elif "--api" in sys.argv or get_api_key():
        run_api_update()
    else:
        # Default: just check status
        run_check_only()
        print()
        print("💡 To update data:")
        print("   - With API: Set RAPIDAPI_KEY and run with --api")
        print("   - Manually: Edit MANUAL_DATA and run with --manual")


if __name__ == "__main__":
    main()
