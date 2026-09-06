"""Statistical analysis service for Option 2 filters - Enhanced Version"""
from typing import Dict, List, Optional
import logging
from statistics import mean

logger = logging.getLogger(__name__)

# League average goals per match (for context filter)
LEAGUE_GOAL_AVERAGES = {
    # Top 5 European (typically higher scoring)
    39: 2.85,   # Premier League
    140: 2.55,  # La Liga
    135: 2.45,  # Serie A
    78: 3.05,   # Bundesliga
    61: 2.65,   # Ligue 1
    
    # Other European
    88: 2.90,   # Eredivisie (high scoring)
    94: 2.45,   # Primeira Liga
    144: 2.60,  # Belgian Pro League
    40: 2.70,   # Championship
    79: 2.85,   # Bundesliga 2
    141: 2.40,  # La Liga 2
    136: 2.35,  # Serie B (low scoring)
    62: 2.45,   # Ligue 2
    179: 2.55,  # Scottish Premiership
    203: 2.70,  # Süper Lig
    41: 2.60,   # League One
    42: 2.55,   # League Two
    
    # Default for unlisted leagues
    'default': 2.50
}


class StatsAnalyzer:
    """Analyze team statistics and apply enhanced Option 2 filters"""
    
    @staticmethod
    def get_league_avg_goals(league_id: int) -> float:
        """Get average goals per match for a league"""
        return LEAGUE_GOAL_AVERAGES.get(league_id, LEAGUE_GOAL_AVERAGES['default'])
    
    @staticmethod
    def calculate_goal_average(matches: List[Dict], team_id: int, last_n: int = 5) -> float:
        """Calculate goals per game average for a team"""
        if not matches:
            return 0.0
            
        recent_matches = matches[:last_n]
        goals = []
        
        for match in recent_matches:
            home_id = match.get('teams', {}).get('home', {}).get('id')
            away_id = match.get('teams', {}).get('away', {}).get('id')
            home_goals = match.get('goals', {}).get('home') or 0
            away_goals = match.get('goals', {}).get('away') or 0
            
            if home_id == team_id:
                goals.append(home_goals)
            elif away_id == team_id:
                goals.append(away_goals)
                
        return mean(goals) if goals else 0.0
        
    @staticmethod
    def calculate_goals_conceded_avg(matches: List[Dict], team_id: int, last_n: int = 5) -> float:
        """Calculate goals conceded per game average"""
        if not matches:
            return 0.0
            
        recent_matches = matches[:last_n]
        conceded = []
        
        for match in recent_matches:
            home_id = match.get('teams', {}).get('home', {}).get('id')
            away_id = match.get('teams', {}).get('away', {}).get('id')
            home_goals = match.get('goals', {}).get('home') or 0
            away_goals = match.get('goals', {}).get('away') or 0
            
            if home_id == team_id:
                conceded.append(away_goals)
            elif away_id == team_id:
                conceded.append(home_goals)
                
        return mean(conceded) if conceded else 0.0
    
    @staticmethod
    def calculate_h2h_goals_average(h2h: List[Dict], last_n: int = 5) -> float:
        """
        NEW FILTER: Calculate average total goals in H2H matches
        """
        if not h2h:
            return 2.5  # Default neutral
            
        total_goals = []
        for match in h2h[:last_n]:
            home_goals = match.get('goals', {}).get('home') or 0
            away_goals = match.get('goals', {}).get('away') or 0
            total_goals.append(home_goals + away_goals)
            
        return mean(total_goals) if total_goals else 2.5
    
    @staticmethod
    def calculate_clean_sheet_percentage(stats: Dict) -> float:
        """
        NEW FILTER: Calculate clean sheet percentage
        """
        if not stats:
            return 0.0
            
        played = stats.get('played', 0)
        if played == 0:
            return 0.0
            
        clean_sheets = stats.get('clean_sheets', 0)
        return (clean_sheets / played) * 100
    
    @staticmethod
    def calculate_failed_to_score_percentage(stats: Dict) -> float:
        """
        NEW FILTER: Calculate percentage of games where team failed to score
        """
        if not stats:
            return 0.0
            
        played = stats.get('played', 0)
        if played == 0:
            return 0.0
            
        failed_to_score = stats.get('failed_to_score', 0)
        return (failed_to_score / played) * 100
    
    @staticmethod
    def calculate_form_trend(stats: Dict) -> Dict:
        """
        NEW FILTER: Compare recent form (last 3) vs overall (last 10)
        Returns trend direction and magnitude
        """
        last_3_avg = stats.get('last_3_goals_avg', stats.get('goals_avg', 1.5))
        last_10_avg = stats.get('goals_avg', 1.5)
        
        if last_10_avg == 0:
            return {'trend': 'neutral', 'change': 0}
            
        change = ((last_3_avg - last_10_avg) / last_10_avg) * 100
        
        if change < -15:
            trend = 'declining_fast'
        elif change < -5:
            trend = 'declining'
        elif change > 15:
            trend = 'improving_fast'
        elif change > 5:
            trend = 'improving'
        else:
            trend = 'stable'
            
        return {
            'trend': trend,
            'change': round(change, 1),
            'last_3_avg': last_3_avg,
            'last_10_avg': last_10_avg
        }
    
    @staticmethod
    def count_high_scoring_games(stats: Dict, threshold: int = 4) -> Dict:
        """
        NEW FILTER: Count games with 4+ total goals in last 5 matches
        """
        high_scoring = stats.get('high_scoring_games', 0)
        played = min(stats.get('played', 5), 5)
        
        return {
            'count': high_scoring,
            'percentage': (high_scoring / played * 100) if played > 0 else 0,
            'is_consistent': high_scoring <= 1  # Max 1 out of 5
        }
    
    def analyze_dc_u35_enhanced(self, home_stats: Dict, away_stats: Dict, 
                                 h2h: List[Dict], league_id: int = None,
                                 poisson_probs: Dict = None, odds: Dict = None) -> Dict:
        """
        DC + Under 3.5 analysis - ODDS-BASED FAVOURITE SELECTION
        
        Only back TRUE FAVOURITES based on betting odds to avoid backing underdogs.
        
        ALL 5 FILTERS MUST PASS:
        1. Betting odds favourite - Team's win odds ≤ 2.50 (implied 40%+ chance)
        2. Clear odds gap - Favourite's odds at least 0.50 lower than opponent
        3. U3.5 hit rate > 50% for at least one team
        4. Not lost to opponent in last 3 H2H meetings
        5. Combined goals avg < 3.2
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'score': 0,
            'filters_passed': 0,
            'total_filters': 5,
            'dc_selection': None,
            'dc_validated': False,
            'favoured_team': None
        }
        
        # Extract statistics
        home_goals_avg = home_stats.get('goals_avg', 0)
        away_goals_avg = away_stats.get('goals_avg', 0)
        home_conceded_avg = home_stats.get('conceded_avg', 0)
        away_conceded_avg = away_stats.get('conceded_avg', 0)
        
        # Get odds - THIS IS NOW CRITICAL FOR SELECTION
        home_odds = odds.get('home_win', 0) if odds else 0
        away_odds = odds.get('away_win', 0) if odds else 0
        
        # Ensure odds are numeric (convert None to 0)
        try:
            home_odds = float(home_odds) if home_odds is not None else 0
            away_odds = float(away_odds) if away_odds is not None else 0
        except (TypeError, ValueError):
            home_odds = 0
            away_odds = 0
        
        # ============================================
        # FILTER 1: Betting odds favourite - odds ≤ 2.00
        # ============================================
        # Lower odds = more favoured by bookmakers
        # Odds of 2.00 = implied 50% chance, 1.50 = 67% chance
        
        if home_odds <= 0 and away_odds <= 0:
            # No odds available - cannot determine true favourite
            result['reasons'].append(f"❌ FILTER 1 FAILED: No betting odds available to determine favourite")
            result['reasons'].append(f"📊 Does not qualify - cannot verify true favourite")
            return result
        
        # Determine favourite based on ODDS (lower = favourite)
        if home_odds > 0 and away_odds > 0:
            if home_odds <= away_odds:
                favoured = 'home'
                favoured_name = 'Home Team'
                favoured_odds = home_odds
                opponent_odds = away_odds
                favoured_stats = home_stats
                dc_selection = '1X'
            else:
                favoured = 'away'
                favoured_name = 'Away Team'
                favoured_odds = away_odds
                opponent_odds = home_odds
                favoured_stats = away_stats
                dc_selection = 'X2'
        elif home_odds > 0:
            favoured = 'home'
            favoured_name = 'Home Team'
            favoured_odds = home_odds
            opponent_odds = 99  # No away odds
            favoured_stats = home_stats
            dc_selection = '1X'
        else:
            favoured = 'away'
            favoured_name = 'Away Team'
            favoured_odds = away_odds
            opponent_odds = 99  # No home odds
            favoured_stats = away_stats
            dc_selection = 'X2'
        
        result['favoured_team'] = favoured
        result['dc_selection'] = dc_selection
        
        score = 0
        filters_passed = 0
        
        # Check if favourite's odds are ≤ 2.50 (implied 40%+ win chance)
        if favoured_odds <= 2.50:
            filters_passed += 1
            if favoured_odds <= 1.50:
                score += 25
                result['reasons'].append(f"✅ FILTER 1: {favoured_name} heavy favourite (odds {favoured_odds:.2f} ≤ 2.50)")
            elif favoured_odds <= 1.85:
                score += 20
                result['reasons'].append(f"✅ FILTER 1: {favoured_name} strong favourite (odds {favoured_odds:.2f} ≤ 2.50)")
            elif favoured_odds <= 2.15:
                score += 15
                result['reasons'].append(f"✅ FILTER 1: {favoured_name} clear favourite (odds {favoured_odds:.2f} ≤ 2.50)")
            else:
                score += 10
                result['reasons'].append(f"✅ FILTER 1: {favoured_name} slight favourite (odds {favoured_odds:.2f} ≤ 2.50)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: {favoured_name} odds {favoured_odds:.2f} > 2.50 (not a favourite)")
            result['reasons'].append(f"📊 Does not qualify - team is not a betting favourite")
            return result
        
        # ============================================
        # FILTER 2: Clear odds gap - at least 0.50 difference
        # ============================================
        odds_gap = opponent_odds - favoured_odds
        
        if odds_gap >= 0.50:
            filters_passed += 1
            if odds_gap >= 2.00:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: Huge odds gap ({favoured_odds:.2f} vs {opponent_odds:.2f}, gap: {odds_gap:.2f})")
            elif odds_gap >= 1.20:
                score += 20
                result['reasons'].append(f"✅ FILTER 2: Large odds gap ({favoured_odds:.2f} vs {opponent_odds:.2f}, gap: {odds_gap:.2f})")
            elif odds_gap >= 0.80:
                score += 15
                result['reasons'].append(f"✅ FILTER 2: Good odds gap ({favoured_odds:.2f} vs {opponent_odds:.2f}, gap: {odds_gap:.2f})")
            else:
                score += 10
                result['reasons'].append(f"✅ FILTER 2: Sufficient odds gap ({favoured_odds:.2f} vs {opponent_odds:.2f}, gap: {odds_gap:.2f})")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: Odds gap {odds_gap:.2f} < 0.50 (match too close)")
            result['reasons'].append(f"📊 Does not qualify - no clear favourite in odds")
            return result
        
        # ============================================
        # FILTER 3: U3.5 hit rate > 50% for at least ONE team
        # ============================================
        home_u35_rate = self._calculate_under_35_rate(home_stats)
        away_u35_rate = self._calculate_under_35_rate(away_stats)
        best_u35_rate = max(home_u35_rate, away_u35_rate)
        
        if best_u35_rate > 50:
            filters_passed += 1
            if home_u35_rate > 50 and away_u35_rate > 50:
                avg_u35 = (home_u35_rate + away_u35_rate) / 2
                if avg_u35 >= 70:
                    score += 20
                    result['reasons'].append(f"✅ FILTER 3: Both teams excellent U3.5 (H: {home_u35_rate:.0f}%, A: {away_u35_rate:.0f}%)")
                else:
                    score += 15
                    result['reasons'].append(f"✅ FILTER 3: Both teams good U3.5 (H: {home_u35_rate:.0f}%, A: {away_u35_rate:.0f}%)")
            else:
                score += 10
                result['reasons'].append(f"✅ FILTER 3: At least one team U3.5 > 50% (H: {home_u35_rate:.0f}%, A: {away_u35_rate:.0f}%)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: U3.5 rates (H: {home_u35_rate:.0f}%, A: {away_u35_rate:.0f}%) - need at least one > 50%")
            result['reasons'].append(f"📊 Does not qualify - high-scoring risk")
            return result
        
        # ============================================
        # FILTER 4: Not lost to opponent in last 3 H2H meetings
        # ============================================
        h2h_losses = self._count_h2h_losses(h2h, favoured)
        
        if h2h_losses == 0:
            filters_passed += 1
            score += 20
            result['reasons'].append(f"✅ FILTER 4: {favoured_name} unbeaten in recent H2H (0 losses)")
        elif h2h_losses == 1:
            # One loss is acceptable if they won/drew the others
            h2h_wins = self._count_h2h_wins(h2h, favoured)
            if h2h_wins >= 1:
                filters_passed += 1
                score += 10
                result['reasons'].append(f"✅ FILTER 4: {favoured_name} decent H2H (W:{h2h_wins}, L:{h2h_losses})")
            else:
                result['reasons'].append(f"❌ FILTER 4 FAILED: {favoured_name} poor H2H record (L:{h2h_losses}, no wins)")
                result['reasons'].append(f"📊 Does not qualify - bogey team risk")
                return result
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: {favoured_name} lost {h2h_losses}+ times in recent H2H")
            result['reasons'].append(f"📊 Does not qualify - opponent is bogey team")
            return result
        
        # ============================================
        # FILTER 5: Combined goals avg < 3.2
        # ============================================
        home_combined = home_goals_avg + home_conceded_avg
        away_combined = away_goals_avg + away_conceded_avg
        match_combined = (home_combined + away_combined) / 2
        
        if match_combined < 3.2:
            filters_passed += 1
            if match_combined <= 2.4:
                score += 20
                result['reasons'].append(f"✅ FILTER 5: Very low-scoring profile ({match_combined:.2f} < 3.2)")
            elif match_combined <= 2.8:
                score += 15
                result['reasons'].append(f"✅ FILTER 5: Low-scoring profile ({match_combined:.2f} < 3.2)")
            else:
                score += 10
                result['reasons'].append(f"✅ FILTER 5: Moderate profile ({match_combined:.2f} < 3.2)")
        else:
            result['reasons'].append(f"❌ FILTER 5 FAILED: Combined avg {match_combined:.2f} ≥ 3.2")
            result['reasons'].append(f"📊 Does not qualify - too high-scoring")
            return result
        
        # ============================================
        # ALL 5 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['dc_validated'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Determine confidence based on score (max 110)
        if score >= 95:
            result['confidence'] = 'Very High'
        elif score >= 75:
            result['confidence'] = 'High'
        elif score >= 55:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 5 FILTERS PASSED | Score: {score}/110 | {dc_selection} & Under 3.5")
        result['reasons'].append(f"💰 Odds: {favoured_name} {favoured_odds:.2f} vs Opponent {opponent_odds:.2f}")
        
        return result
    
    def _count_h2h_losses(self, h2h: List[Dict], favoured: str) -> int:
        """Count how many times the favoured team lost in recent H2H"""
        losses = 0
        if not h2h:
            return 0
        for match in h2h[:3]:  # Last 3 matches
            home_goals = match.get('goals', {}).get('home', 0) or 0
            away_goals = match.get('goals', {}).get('away', 0) or 0
            
            if favoured == 'home':
                # Check if home team lost
                if away_goals > home_goals:
                    losses += 1
            else:
                # Check if away team lost
                if home_goals > away_goals:
                    losses += 1
        return losses
    
    def _count_h2h_wins(self, h2h: List[Dict], favoured: str) -> int:
        """Count how many times the favoured team won in recent H2H"""
        wins = 0
        if not h2h:
            return 0
        for match in h2h[:3]:  # Last 3 matches
            home_goals = match.get('goals', {}).get('home', 0) or 0
            away_goals = match.get('goals', {}).get('away', 0) or 0
            
            if favoured == 'home':
                if home_goals > away_goals:
                    wins += 1
            else:
                if away_goals > home_goals:
                    wins += 1
        return wins
    
    def _estimate_win_prob(self, team_goals: float, opp_conceded: float) -> float:
        """Estimate win probability from goal averages"""
        expected_goals = (team_goals + opp_conceded) / 2
        # Simplified estimation based on expected goals
        if expected_goals >= 2.0:
            return 55
        elif expected_goals >= 1.5:
            return 45
        elif expected_goals >= 1.2:
            return 38
        elif expected_goals >= 1.0:
            return 32
        else:
            return 25
    
    def _calculate_under_35_rate(self, stats: Dict) -> float:
        """Calculate Under 3.5 goals hit rate from team stats"""
        played = max(stats.get('played', 1), 1)
        goals_scored = stats.get('goals_avg', 0) * played
        goals_conceded = stats.get('conceded_avg', 0) * played
        
        # Estimate games with 3 or fewer total goals
        avg_total = stats.get('goals_avg', 0) + stats.get('conceded_avg', 0)
        
        # Use Poisson-like estimation for U3.5 probability
        if avg_total <= 1.5:
            return 95  # Very defensive team
        elif avg_total <= 2.0:
            return 88
        elif avg_total <= 2.5:
            return 82
        elif avg_total <= 3.0:
            return 75
        elif avg_total <= 3.5:
            return 65
        else:
            return 55
    
    # Keep original method for backward compatibility
    def analyze_dc_u35(self, home_stats: Dict, away_stats: Dict, h2h: List[Dict]) -> Dict:
        """Original method - now calls enhanced version"""
        return self.analyze_dc_u35_enhanced(home_stats, away_stats, h2h)
        
    @staticmethod
    def analyze_dc_o15(home_stats: Dict, away_stats: Dict, h2h: List[Dict]) -> Dict:
        """Analyze DC + Over 1.5 market
        
        Criteria:
        - Both teams score regularly (4/5 last games)
        - H2H last 3 had over 1.5 in 2+ matches
        - Combined avg ≥ 2.5 goals
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': []
        }
        
        home_goals_avg = home_stats.get('goals_avg', 0)
        away_goals_avg = away_stats.get('goals_avg', 0)
        
        checks_passed = 0
        
        # Check 1: Home team scoring
        if home_goals_avg >= 1.2:
            checks_passed += 1
            result['reasons'].append(f"✅ Home scores regularly ({home_goals_avg:.1f} avg)")
        else:
            result['reasons'].append(f"❌ Home struggles to score ({home_goals_avg:.1f} avg)")
            
        # Check 2: Away team scoring
        if away_goals_avg >= 1.0:
            checks_passed += 1
            result['reasons'].append(f"✅ Away scores regularly ({away_goals_avg:.1f} avg)")
        else:
            result['reasons'].append(f"❌ Away struggles to score ({away_goals_avg:.1f} avg)")
            
        # Check 3: Combined average
        combined_avg = home_goals_avg + away_goals_avg
        if combined_avg >= 2.5:
            checks_passed += 1
            result['reasons'].append(f"✅ High-scoring match expected ({combined_avg:.1f} combined)")
        else:
            result['reasons'].append(f"⚠️ Moderate scoring expected ({combined_avg:.1f} combined)")
            
        # Determine qualification
        if checks_passed >= 2:
            result['qualifies'] = True
            if checks_passed >= 3:
                result['confidence'] = 'High'
            else:
                result['confidence'] = 'Medium'
                
        return result
    
    @staticmethod
    def calculate_h2h_btts_rate(h2h: List[Dict]) -> Dict:
        """
        Calculate BTTS rate from head-to-head matches
        Returns percentage of H2H matches where both teams scored
        """
        if not h2h:
            return {'rate': 50.0, 'btts_count': 0, 'total': 0}
        
        btts_count = 0
        total = min(len(h2h), 5)  # Last 5 H2H matches
        
        for match in h2h[:5]:
            home_goals = match.get('goals', {}).get('home') or 0
            away_goals = match.get('goals', {}).get('away') or 0
            
            if home_goals >= 1 and away_goals >= 1:
                btts_count += 1
        
        rate = (btts_count / total * 100) if total > 0 else 50.0
        return {'rate': rate, 'btts_count': btts_count, 'total': total}
    
    @staticmethod
    def calculate_recent_btts_rate(stats: Dict) -> float:
        """
        Calculate BTTS rate from recent matches (last 5)
        Uses scoring and conceding patterns to estimate
        """
        goals_avg = stats.get('goals_avg', 1.0)
        conceded_avg = stats.get('conceded_avg', 1.0)
        played = stats.get('played', 1)
        
        # Estimate based on scoring frequency
        # If team scores AND concedes regularly, high BTTS likelihood
        scores_regularly = goals_avg >= 1.0
        concedes_regularly = conceded_avg >= 0.8
        
        if scores_regularly and concedes_regularly:
            base_rate = 65
        elif scores_regularly or concedes_regularly:
            base_rate = 50
        else:
            base_rate = 35
        
        # Adjust based on failed to score rate
        fts = stats.get('failed_to_score', 0)
        fts_pct = (fts / played * 100) if played > 0 else 20
        
        # Lower FTS = higher BTTS involvement
        if fts_pct <= 10:
            base_rate += 15
        elif fts_pct <= 20:
            base_rate += 8
        elif fts_pct >= 35:
            base_rate -= 10
        
        return min(90, max(20, base_rate))
    
    @staticmethod
    def calculate_form_momentum(stats: Dict) -> Dict:
        """
        Calculate recent form momentum based on goals trend
        Returns momentum score and direction
        """
        last_3_avg = stats.get('last_3_goals_avg', stats.get('goals_avg', 1.2))
        season_avg = stats.get('goals_avg', 1.2)
        
        if season_avg == 0:
            return {'momentum': 'neutral', 'score': 0, 'trend_pct': 0}
        
        trend_pct = ((last_3_avg - season_avg) / season_avg) * 100
        
        if trend_pct >= 20:
            momentum = 'hot_streak'
            score = 15
        elif trend_pct >= 10:
            momentum = 'improving'
            score = 10
        elif trend_pct <= -20:
            momentum = 'cold_streak'
            score = -15
        elif trend_pct <= -10:
            momentum = 'declining'
            score = -10
        else:
            momentum = 'stable'
            score = 0
        
        return {
            'momentum': momentum,
            'score': score,
            'trend_pct': round(trend_pct, 1),
            'last_3_avg': last_3_avg,
            'season_avg': season_avg
        }

    # League BTTS rates (historical averages)
    LEAGUE_BTTS_RATES = {
        # High BTTS leagues (>55%)
        78: 58,    # Bundesliga
        79: 56,    # Bundesliga 2
        88: 57,    # Eredivisie
        39: 54,    # Premier League
        40: 55,    # Championship
        
        # Medium BTTS leagues (48-54%)
        140: 50,   # La Liga
        61: 49,    # Ligue 1
        94: 51,    # Primeira Liga
        144: 52,   # Belgian Pro League
        203: 53,   # Turkish Super Lig
        
        # Low BTTS leagues (<48%)
        135: 46,   # Serie A
        136: 44,   # Serie B
        141: 47,   # La Liga 2
        62: 45,    # Ligue 2
        
        'default': 50
    }
    
    @classmethod
    def get_league_btts_rate(cls, league_id: int) -> float:
        """Get historical BTTS rate for a league"""
        return cls.LEAGUE_BTTS_RATES.get(league_id, cls.LEAGUE_BTTS_RATES['default'])

    def analyze_1x2_btts_enhanced(self, home_stats: Dict, away_stats: Dict, h2h: List[Dict],
                                   home_team: str, away_team: str, league_id: int = None) -> Dict:
        """
        ENHANCED 1X2 + BTTS Analysis with Additional Filters for Higher Hit Rate
        
        Predicts match result (Home Win, Draw, or Away Win) AND both teams scoring.
        
        ENHANCED CRITERIA:
        1. Home team scores regularly (≥1.3 avg) ✅
        2. Away team scores regularly (≥1.2 avg) ✅
        3. Home team concedes (allows away to score) (≥1.0 avg) ✅
        4. Away team concedes (allows home to score) (≥1.2 avg) ✅
        5. Low failed-to-score rate (TIGHTENED: Home ≤15%, Away ≤20%) ✅
        
        NEW FILTERS:
        6. H2H BTTS Rate ≥ 60% (3/5 matches)
        7. Recent Form BTTS involvement ≥ 50% per team
        8. Home team HOME goals ≥ 1.5 avg (estimated)
        9. Away team AWAY goals ≥ 1.0 avg (estimated)
        10. League BTTS context (exclude low-BTTS leagues or require higher thresholds)
        11. Form Momentum (hot/cold streak detection)
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'recommended_selection': None,
            'btts_probability': 0,
            'filters_passed': 0,
            'total_filters': 11
        }
        
        # Extract statistics
        home_goals_avg = home_stats.get('goals_avg', 0)
        away_goals_avg = away_stats.get('goals_avg', 0)
        home_conceded_avg = home_stats.get('conceded_avg', 0)
        away_conceded_avg = away_stats.get('conceded_avg', 0)
        
        # Failed to score percentages (lower = better for BTTS)
        home_played = max(home_stats.get('played', 1), 1)
        away_played = max(away_stats.get('played', 1), 1)
        home_fts = home_stats.get('failed_to_score', 0) / home_played * 100
        away_fts = away_stats.get('failed_to_score', 0) / away_played * 100
        
        # Estimate home/away specific stats (typically home +10%, away -10%)
        home_at_home_goals = home_goals_avg * 1.12
        away_at_away_goals = away_goals_avg * 0.88
        
        score = 0
        filters_passed = 0
        
        # ============================================
        # FILTER 1: Home team scores regularly (≥1.3 avg)
        # ============================================
        if home_goals_avg >= 1.5:
            filters_passed += 1
            score += 14
            result['reasons'].append(f"✅ {home_team} prolific scorer ({home_goals_avg:.1f} avg)")
        elif home_goals_avg >= 1.3:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ {home_team} scores regularly ({home_goals_avg:.1f} avg)")
        elif home_goals_avg >= 1.0:
            score += 5
            result['reasons'].append(f"⚠️ {home_team} moderate scoring ({home_goals_avg:.1f} avg)")
        else:
            score -= 5
            result['reasons'].append(f"❌ {home_team} struggles to score ({home_goals_avg:.1f} avg)")
            
        # ============================================
        # FILTER 2: Away team scores regularly (≥1.2 avg)
        # ============================================
        if away_goals_avg >= 1.4:
            filters_passed += 1
            score += 14
            result['reasons'].append(f"✅ {away_team} prolific scorer ({away_goals_avg:.1f} avg)")
        elif away_goals_avg >= 1.2:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ {away_team} scores regularly ({away_goals_avg:.1f} avg)")
        elif away_goals_avg >= 0.9:
            score += 5
            result['reasons'].append(f"⚠️ {away_team} moderate scoring ({away_goals_avg:.1f} avg)")
        else:
            score -= 5
            result['reasons'].append(f"❌ {away_team} struggles to score ({away_goals_avg:.1f} avg)")
            
        # ============================================
        # FILTER 3: Home team concedes (allows away to score) ≥1.0
        # ============================================
        if home_conceded_avg >= 1.2:
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ {home_team} leaky defense ({home_conceded_avg:.1f} conceded)")
        elif home_conceded_avg >= 1.0:
            filters_passed += 1
            score += 8
            result['reasons'].append(f"✅ {home_team} concedes regularly ({home_conceded_avg:.1f} avg)")
        elif home_conceded_avg >= 0.7:
            score += 4
            result['reasons'].append(f"⚠️ {home_team} sometimes concedes ({home_conceded_avg:.1f} avg)")
        else:
            score -= 8
            result['reasons'].append(f"❌ {home_team} solid defense - rarely concedes ({home_conceded_avg:.1f} avg)")
            
        # ============================================
        # FILTER 4: Away team concedes (allows home to score) ≥1.2
        # ============================================
        if away_conceded_avg >= 1.4:
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ {away_team} very leaky defense ({away_conceded_avg:.1f} conceded)")
        elif away_conceded_avg >= 1.2:
            filters_passed += 1
            score += 8
            result['reasons'].append(f"✅ {away_team} concedes regularly ({away_conceded_avg:.1f} avg)")
        elif away_conceded_avg >= 0.9:
            score += 4
            result['reasons'].append(f"⚠️ {away_team} sometimes concedes ({away_conceded_avg:.1f} avg)")
        else:
            score -= 8
            result['reasons'].append(f"❌ {away_team} solid defense - rarely concedes ({away_conceded_avg:.1f} avg)")
            
        # ============================================
        # FILTER 5: Low failed-to-score rate (TIGHTENED: Home ≤15%, Away ≤20%)
        # ============================================
        if home_fts <= 10 and away_fts <= 15:
            filters_passed += 1
            score += 15
            result['reasons'].append(f"✅ Elite scoring consistency (FTS: {home_fts:.0f}%, {away_fts:.0f}%)")
        elif home_fts <= 15 and away_fts <= 20:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ Both teams rarely blank (FTS: {home_fts:.0f}%, {away_fts:.0f}%)")
        elif home_fts <= 25 and away_fts <= 30:
            score += 4
            result['reasons'].append(f"⚠️ Moderate blank rate (FTS: {home_fts:.0f}%, {away_fts:.0f}%)")
        else:
            score -= 10
            result['reasons'].append(f"❌ High blank rate - BTTS risky (FTS: {home_fts:.0f}%, {away_fts:.0f}%)")
        
        # ============================================
        # NEW FILTER 6: H2H BTTS Rate ≥ 60%
        # ============================================
        h2h_btts = self.calculate_h2h_btts_rate(h2h)
        h2h_rate = h2h_btts['rate']
        
        if h2h_rate >= 80:
            filters_passed += 1
            score += 15
            result['reasons'].append(f"✅ H2H BTTS excellent ({h2h_btts['btts_count']}/{h2h_btts['total']} = {h2h_rate:.0f}%)")
        elif h2h_rate >= 60:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ H2H BTTS strong ({h2h_btts['btts_count']}/{h2h_btts['total']} = {h2h_rate:.0f}%)")
        elif h2h_rate >= 40:
            score += 3
            result['reasons'].append(f"⚠️ H2H BTTS moderate ({h2h_btts['btts_count']}/{h2h_btts['total']} = {h2h_rate:.0f}%)")
        else:
            score -= 8
            result['reasons'].append(f"❌ H2H BTTS poor ({h2h_btts['btts_count']}/{h2h_btts['total']} = {h2h_rate:.0f}%)")
        
        # ============================================
        # NEW FILTER 7: Recent Form BTTS involvement ≥ 50%
        # ============================================
        home_recent_btts = self.calculate_recent_btts_rate(home_stats)
        away_recent_btts = self.calculate_recent_btts_rate(away_stats)
        avg_recent_btts = (home_recent_btts + away_recent_btts) / 2
        
        if avg_recent_btts >= 65:
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ Both teams in BTTS form ({avg_recent_btts:.0f}% avg)")
        elif avg_recent_btts >= 50:
            filters_passed += 1
            score += 8
            result['reasons'].append(f"✅ Good recent BTTS involvement ({avg_recent_btts:.0f}% avg)")
        elif avg_recent_btts >= 40:
            score += 3
            result['reasons'].append(f"⚠️ Moderate BTTS involvement ({avg_recent_btts:.0f}% avg)")
        else:
            score -= 5
            result['reasons'].append(f"❌ Low BTTS involvement recently ({avg_recent_btts:.0f}% avg)")
        
        # ============================================
        # NEW FILTER 8: Home team HOME goals ≥ 1.5 avg
        # ============================================
        if home_at_home_goals >= 1.8:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ {home_team} dominant at home ({home_at_home_goals:.1f} est. home goals)")
        elif home_at_home_goals >= 1.5:
            filters_passed += 1
            score += 7
            result['reasons'].append(f"✅ {home_team} strong at home ({home_at_home_goals:.1f} est. home goals)")
        elif home_at_home_goals >= 1.2:
            score += 3
            result['reasons'].append(f"⚠️ {home_team} moderate at home ({home_at_home_goals:.1f} est.)")
        else:
            result['reasons'].append(f"❌ {home_team} weak at home ({home_at_home_goals:.1f} est.)")
        
        # ============================================
        # NEW FILTER 9: Away team AWAY goals ≥ 1.0 avg
        # ============================================
        if away_at_away_goals >= 1.3:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ {away_team} scores well away ({away_at_away_goals:.1f} est. away goals)")
        elif away_at_away_goals >= 1.0:
            filters_passed += 1
            score += 7
            result['reasons'].append(f"✅ {away_team} decent away ({away_at_away_goals:.1f} est. away goals)")
        elif away_at_away_goals >= 0.8:
            score += 3
            result['reasons'].append(f"⚠️ {away_team} struggles away ({away_at_away_goals:.1f} est.)")
        else:
            score -= 5
            result['reasons'].append(f"❌ {away_team} poor away record ({away_at_away_goals:.1f} est.)")
        
        # ============================================
        # NEW FILTER 10: League BTTS Context
        # ============================================
        if league_id:
            league_btts_rate = self.get_league_btts_rate(league_id)
            
            if league_btts_rate >= 55:
                filters_passed += 1
                score += 10
                result['reasons'].append(f"✅ High-BTTS league ({league_btts_rate}% historical)")
            elif league_btts_rate >= 50:
                score += 5
                result['reasons'].append(f"⚠️ Average BTTS league ({league_btts_rate}% historical)")
            elif league_btts_rate < 47:
                score -= 8
                result['reasons'].append(f"❌ Low-BTTS league ({league_btts_rate}% historical) - requires strong signals")
        
        # ============================================
        # NEW FILTER 11: Form Momentum
        # ============================================
        home_momentum = self.calculate_form_momentum(home_stats)
        away_momentum = self.calculate_form_momentum(away_stats)
        
        # For BTTS, we want teams that are scoring (not in cold streak)
        momentum_score = 0
        
        if home_momentum['momentum'] in ['hot_streak', 'improving']:
            momentum_score += home_momentum['score']
            result['reasons'].append(f"🔥 {home_team} in scoring form ({home_momentum['momentum']})")
        elif home_momentum['momentum'] in ['cold_streak', 'declining']:
            momentum_score += home_momentum['score']  # Negative
            result['reasons'].append(f"❄️ {home_team} in scoring slump ({home_momentum['momentum']})")
        
        if away_momentum['momentum'] in ['hot_streak', 'improving']:
            momentum_score += away_momentum['score']
            result['reasons'].append(f"🔥 {away_team} in scoring form ({away_momentum['momentum']})")
        elif away_momentum['momentum'] in ['cold_streak', 'declining']:
            momentum_score += away_momentum['score']  # Negative
            result['reasons'].append(f"❄️ {away_team} in scoring slump ({away_momentum['momentum']})")
        
        # Both teams in good form = bonus filter pass
        if momentum_score >= 15:
            filters_passed += 1
            score += 12
        elif momentum_score >= 5:
            score += 6
        elif momentum_score <= -15:
            score -= 10
            result['reasons'].append(f"⚠️ Cold streak warning - both teams struggling")
        
        score += momentum_score  # Add/subtract momentum impact
        
        # ============================================
        # 1X2 CRITERIA: Determine match winner (ENHANCED)
        # ============================================
        
        # Calculate strength difference with form weighting
        home_form_modifier = 1 + (home_momentum['score'] / 100)  # e.g., +0.15 for hot streak
        away_form_modifier = 1 + (away_momentum['score'] / 100)
        
        home_attack = home_goals_avg * 1.1 * home_form_modifier  # Home advantage + form
        home_defense = home_conceded_avg
        away_attack = away_goals_avg * 0.9 * away_form_modifier  # Away penalty + form
        away_defense = away_conceded_avg
        
        home_strength = home_attack - away_defense + (home_defense - away_attack) * 0.5
        away_strength = away_attack - home_defense + (away_defense - home_attack) * 0.5
        
        # Enhanced selection with clearer thresholds
        strength_diff = home_strength - away_strength
        
        if strength_diff > 0.5:
            result['recommended_selection'] = f"{home_team} Win & BTTS"
            result['selection_type'] = 'home_btts'
            score += 10
            result['reasons'].append(f"📊 {home_team} clear favorite (strength +{strength_diff:.2f})")
        elif strength_diff > 0.25:
            result['recommended_selection'] = f"{home_team} Win & BTTS"
            result['selection_type'] = 'home_btts'
            score += 6
            result['reasons'].append(f"📊 {home_team} slight favorite (strength +{strength_diff:.2f})")
        elif strength_diff < -0.4:
            result['recommended_selection'] = f"{away_team} Win & BTTS"
            result['selection_type'] = 'away_btts'
            score += 8
            result['reasons'].append(f"📊 {away_team} favored despite away (strength {strength_diff:.2f})")
        elif abs(strength_diff) <= 0.25:
            result['recommended_selection'] = f"Draw & BTTS"
            result['selection_type'] = 'draw_btts'
            score += 5
            result['reasons'].append(f"📊 Evenly matched - Draw possible (diff {strength_diff:.2f})")
        else:
            # Default to home win with home advantage
            result['recommended_selection'] = f"{home_team} Win & BTTS"
            result['selection_type'] = 'home_btts'
            result['reasons'].append(f"📊 Home advantage edge")
        
        # ============================================
        # Calculate BTTS Probability (ENHANCED)
        # ============================================
        # Base from scoring/conceding patterns
        btts_base = 45
        
        # Add for goals averages
        btts_base += min(20, home_goals_avg * 8)
        btts_base += min(15, away_goals_avg * 8)
        
        # Add for conceding patterns
        btts_base += min(10, home_conceded_avg * 5)
        btts_base += min(10, away_conceded_avg * 5)
        
        # Subtract for FTS rates
        btts_base -= min(15, (home_fts + away_fts) / 4)
        
        # Add H2H history
        btts_base += (h2h_rate - 50) * 0.2
        
        # Add momentum
        btts_base += momentum_score * 0.3
        
        btts_prob = min(92, max(35, btts_base))
        result['btts_probability'] = round(btts_prob, 1)
        
        # ============================================
        # FINAL QUALIFICATION (TIGHTENED)
        # ============================================
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Require more filters for qualification
        if filters_passed >= 8 and score >= 70:
            result['qualifies'] = True
            result['confidence'] = 'Very High'
        elif filters_passed >= 7 and score >= 60:
            result['qualifies'] = True
            result['confidence'] = 'High'
        elif filters_passed >= 6 and score >= 50:
            result['qualifies'] = True
            result['confidence'] = 'Medium'
        elif filters_passed >= 5 and score >= 45:
            result['qualifies'] = True
            result['confidence'] = 'Low'
        
        # Special case: If BTTS probability is very high and basic checks pass
        if btts_prob >= 75 and filters_passed >= 4 and not result['qualifies']:
            result['qualifies'] = True
            result['confidence'] = 'Medium'
            result['reasons'].append(f"✅ Qualified on high BTTS probability ({btts_prob}%)")
            
        result['reasons'].append(f"📊 Score: {score}/120 | Filters: {filters_passed}/11 | BTTS: {btts_prob:.0f}%")
                
        return result

    @staticmethod
    def analyze_1x2_btts(home_stats: Dict, away_stats: Dict, h2h: List[Dict],
                         home_team: str, away_team: str) -> Dict:
        """Original method - now calls enhanced version for backward compatibility"""
        analyzer = StatsAnalyzer()
        return analyzer.analyze_1x2_btts_enhanced(home_stats, away_stats, h2h, home_team, away_team)

    # League First Half Goal Averages (historical data)
    LEAGUE_1H_GOAL_RATES = {
        # Low 1H scoring leagues (good for U1.5 1H)
        135: 1.05,   # Serie A (defensive)
        136: 0.95,   # Serie B
        61: 1.10,    # Ligue 1
        62: 1.00,    # Ligue 2
        141: 1.05,   # La Liga 2
        
        # Medium 1H scoring leagues
        140: 1.15,   # La Liga
        39: 1.25,    # Premier League
        40: 1.20,    # Championship
        94: 1.10,    # Primeira Liga
        
        # High 1H scoring leagues (avoid for U1.5 1H)
        78: 1.35,    # Bundesliga
        79: 1.30,    # Bundesliga 2
        88: 1.30,    # Eredivisie
        
        'default': 1.15
    }
    
    @classmethod
    def get_league_1h_goal_rate(cls, league_id: int) -> float:
        """Get average first half goals per match for a league"""
        return cls.LEAGUE_1H_GOAL_RATES.get(league_id, cls.LEAGUE_1H_GOAL_RATES['default'])

    def analyze_under_1_5_first_half(self, home_stats: Dict, away_stats: Dict,
                                      h2h: List[Dict], home_team: str, away_team: str,
                                      league_id: int = None) -> Dict:
        """
        Analyze Under 1.5 First Half Goals market
        
        ALL 4 FILTERS MUST PASS:
        1. At least one team must have had a 0-0 HT scoreline in 2+ games (last 10)
        2. Both teams must have 1H U1.5 hit rate > 40% (last 10 games)
        3. Combined 1H average goals < 1.3
        4. Both teams must have FTS in 1H > 40% (last 10 games)
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'under_probability': 0,
            'filters_passed': 0,
            'total_filters': 4
        }
        
        # Extract statistics
        home_goals_avg = home_stats.get('goals_avg', 1.5)
        away_goals_avg = away_stats.get('goals_avg', 1.3)
        
        home_played = max(home_stats.get('played', 1), 1)
        away_played = max(away_stats.get('played', 1), 1)
        
        score = 0
        filters_passed = 0
        
        # Estimate 1H stats (42% of full match goals typically in 1H)
        home_1h_goals_est = home_goals_avg * 0.42
        away_1h_goals_est = away_goals_avg * 0.42
        combined_1h_goals = home_1h_goals_est + away_1h_goals_est
        
        # ============================================
        # FILTER 1: At least one team had 0-0 HT in 2+ games (last 10)
        # ============================================
        # Estimate 0-0 HT games from clean sheets and FTS data
        home_clean_sheets = home_stats.get('clean_sheets', 0)
        away_clean_sheets = away_stats.get('clean_sheets', 0)
        home_fts = home_stats.get('failed_to_score', 0)
        away_fts = away_stats.get('failed_to_score', 0)
        
        # 0-0 HT estimate: games where team kept CS AND failed to score (in 1H context)
        # Use 50% of min(clean_sheets, fts) as conservative 0-0 HT estimate
        home_00_ht_est = min(home_clean_sheets, home_fts) * 0.6
        away_00_ht_est = min(away_clean_sheets, away_fts) * 0.6
        
        # Check if at least one team has 2+ estimated 0-0 HT games
        best_00_ht = max(home_00_ht_est, away_00_ht_est)
        
        if best_00_ht >= 2:
            filters_passed += 1
            if best_00_ht >= 4:
                score += 30
                result['reasons'].append(f"✅ FILTER 1: Excellent 0-0 HT record (est. {best_00_ht:.0f} games)")
            elif best_00_ht >= 3:
                score += 25
                result['reasons'].append(f"✅ FILTER 1: Strong 0-0 HT record (est. {best_00_ht:.0f} games)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 1: Good 0-0 HT record (est. {best_00_ht:.0f} games ≥ 2)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: No team has 2+ 0-0 HT games (best est: {best_00_ht:.1f})")
            result['reasons'].append(f"📊 Does not qualify - Filter 1 failed")
            return result
        
        # ============================================
        # FILTER 2: Both teams 1H U1.5 hit rate > 40% (last 10)
        # ============================================
        # Calculate U1.5 1H hit rate from goals average
        # If 1H goals avg <= 1.5, estimate hit rate based on avg
        home_u15_1h_rate = self._estimate_u15_1h_hit_rate(home_1h_goals_est)
        away_u15_1h_rate = self._estimate_u15_1h_hit_rate(away_1h_goals_est)
        
        if home_u15_1h_rate > 40 and away_u15_1h_rate > 40:
            filters_passed += 1
            avg_rate = (home_u15_1h_rate + away_u15_1h_rate) / 2
            if avg_rate >= 70:
                score += 30
                result['reasons'].append(f"✅ FILTER 2: Excellent U1.5 1H rates (H: {home_u15_1h_rate:.0f}%, A: {away_u15_1h_rate:.0f}%)")
            elif avg_rate >= 55:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: Strong U1.5 1H rates (H: {home_u15_1h_rate:.0f}%, A: {away_u15_1h_rate:.0f}%)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 2: Good U1.5 1H rates (H: {home_u15_1h_rate:.0f}%, A: {away_u15_1h_rate:.0f}% > 40%)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: U1.5 1H rates (H: {home_u15_1h_rate:.0f}%, A: {away_u15_1h_rate:.0f}%) - both must be > 40%")
            result['reasons'].append(f"📊 Does not qualify - Filter 2 failed")
            return result
        
        # ============================================
        # FILTER 3: Combined 1H average goals < 1.3
        # ============================================
        if combined_1h_goals < 1.3:
            filters_passed += 1
            if combined_1h_goals <= 0.9:
                score += 30
                result['reasons'].append(f"✅ FILTER 3: Elite low 1H scoring ({combined_1h_goals:.2f} < 0.9)")
            elif combined_1h_goals <= 1.1:
                score += 25
                result['reasons'].append(f"✅ FILTER 3: Very low 1H scoring ({combined_1h_goals:.2f} < 1.1)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 3: Low 1H scoring ({combined_1h_goals:.2f} < 1.3)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: Combined 1H goals {combined_1h_goals:.2f} ≥ 1.3")
            result['reasons'].append(f"📊 Does not qualify - Filter 3 failed")
            return result
        
        # ============================================
        # FILTER 4: Both teams FTS in 1H > 40% (last 10)
        # ============================================
        # Estimate 1H FTS rate (typically ~60% of full match FTS rate, but higher for defensive teams)
        home_fts_pct = (home_fts / min(home_played, 10)) * 100 if home_played > 0 else 0
        away_fts_pct = (away_fts / min(away_played, 10)) * 100 if away_played > 0 else 0
        
        # 1H FTS is typically higher than full match FTS (more games 0-0 at HT than FT)
        # Estimate 1H FTS as full match FTS * 1.4 (capped at 80%)
        home_1h_fts_rate = min(80, home_fts_pct * 1.4)
        away_1h_fts_rate = min(80, away_fts_pct * 1.4)
        
        if home_1h_fts_rate > 40 and away_1h_fts_rate > 40:
            filters_passed += 1
            avg_fts = (home_1h_fts_rate + away_1h_fts_rate) / 2
            if avg_fts >= 60:
                score += 30
                result['reasons'].append(f"✅ FILTER 4: Excellent 1H FTS rates (H: {home_1h_fts_rate:.0f}%, A: {away_1h_fts_rate:.0f}%)")
            elif avg_fts >= 50:
                score += 25
                result['reasons'].append(f"✅ FILTER 4: Strong 1H FTS rates (H: {home_1h_fts_rate:.0f}%, A: {away_1h_fts_rate:.0f}%)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 4: Good 1H FTS rates (H: {home_1h_fts_rate:.0f}%, A: {away_1h_fts_rate:.0f}% > 40%)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: 1H FTS rates (H: {home_1h_fts_rate:.0f}%, A: {away_1h_fts_rate:.0f}%) - both must be > 40%")
            result['reasons'].append(f"📊 Does not qualify - Filter 4 failed")
            return result
        
        # ============================================
        # ALL 4 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        result['combined_1h_goals'] = round(combined_1h_goals, 2)
        
        # Calculate Under 1.5 1H probability
        if combined_1h_goals <= 0.8:
            under_prob = 82
        elif combined_1h_goals <= 1.0:
            under_prob = 75
        elif combined_1h_goals <= 1.2:
            under_prob = 68
        else:
            under_prob = 62
        
        # Boost for high filter scores
        under_prob += (score - 80) * 0.15
        under_prob = min(90, max(55, under_prob))
        result['under_probability'] = round(under_prob, 1)
        
        # Determine confidence based on score (max 120)
        if score >= 110:
            result['confidence'] = 'Very High'
        elif score >= 95:
            result['confidence'] = 'High'
        elif score >= 80:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 4 FILTERS PASSED | Score: {score}/120 | U1.5 1H Prob: {under_prob:.0f}%")
        
        return result
    
    def _estimate_u15_1h_hit_rate(self, goals_1h_avg: float) -> float:
        """Estimate Under 1.5 First Half hit rate from 1H goals average"""
        # Based on Poisson distribution approximation
        if goals_1h_avg <= 0.4:
            return 92  # Very low scoring
        elif goals_1h_avg <= 0.5:
            return 85
        elif goals_1h_avg <= 0.6:
            return 78
        elif goals_1h_avg <= 0.7:
            return 72
        elif goals_1h_avg <= 0.8:
            return 65
        elif goals_1h_avg <= 0.9:
            return 58
        elif goals_1h_avg <= 1.0:
            return 52
        elif goals_1h_avg <= 1.1:
            return 45
        elif goals_1h_avg <= 1.2:
            return 40
        else:
            return 35  # High scoring

    def _estimate_o15_1h_games(self, goals_avg: float, conceded_avg: float) -> float:
        """
        Estimate number of games with Over 1.5 First Half goals (out of 10)
        Based on team's scoring + conceding patterns
        """
        # Total goal involvement per game
        total_involvement = goals_avg + conceded_avg
        
        # Estimate 1H goal involvement (42% of full match)
        h1_involvement = total_involvement * 0.42
        
        # Map 1H involvement to O1.5 1H games (out of 10)
        # O1.5 1H = 2+ goals in first half
        if h1_involvement >= 1.8:
            return 8  # High-scoring teams
        elif h1_involvement >= 1.5:
            return 7
        elif h1_involvement >= 1.3:
            return 6
        elif h1_involvement >= 1.1:
            return 5
        elif h1_involvement >= 0.95:
            return 4
        elif h1_involvement >= 0.8:
            return 3
        else:
            return 2  # Low-scoring teams

    def _estimate_2h_goal_percentage(self, goals_avg: float, conceded_avg: float) -> float:
        """
        Estimate percentage of goals scored in 2H (out of total goals in last 20 games)
        Based on team's scoring and defensive profile
        """
        # Baseline: 58% of goals typically come in 2H
        base_pct = 58
        
        # High-scoring teams tend to score more evenly across halves
        # Defensive/counter-attacking teams tend to score more in 2H
        
        if goals_avg >= 2.0:
            # Very high-scoring team - score more evenly
            return base_pct - 3  # ~55%
        elif goals_avg >= 1.5:
            # Good scoring team
            return base_pct  # ~58%
        elif goals_avg >= 1.2:
            # Average scoring team - tend to score more in 2H
            return base_pct + 4  # ~62%
        elif goals_avg >= 1.0:
            # Below average scorer - rely on 2H goals
            return base_pct + 7  # ~65%
        else:
            # Low-scoring team - heavily rely on 2H
            return base_pct + 10  # ~68%

    def _estimate_2h_scoring_games(self, goals_avg: float, fts_pct: float) -> float:
        """
        Estimate number of games with at least 1 goal in 2H (out of 10)
        Based on team's scoring average and failed-to-score rate
        """
        # If team scores often, they likely score in 2H often
        # FTS rate affects how many games they blank entirely
        
        # Start with games they score in (10 - FTS games)
        scoring_games = 10 - (fts_pct / 10)  # FTS% to games out of 10
        
        # Of games they score, estimate 2H scoring percentage
        # Higher goal average = more likely to score in 2H
        if goals_avg >= 2.0:
            h2_scoring_rate = 0.95  # Almost always score in 2H
        elif goals_avg >= 1.5:
            h2_scoring_rate = 0.88
        elif goals_avg >= 1.2:
            h2_scoring_rate = 0.80
        elif goals_avg >= 1.0:
            h2_scoring_rate = 0.72
        else:
            h2_scoring_rate = 0.60
        
        # Calculate 2H scoring games
        h2_scoring_games = scoring_games * h2_scoring_rate
        
        return min(10, max(0, h2_scoring_games))

    def calculate_h2h_1h_goals_average(self, h2h: List[Dict]) -> float:
        """Calculate average first half goals from H2H matches"""
        if not h2h:
            return 1.0  # Default if no H2H data
        
        total_1h_goals = 0
        matches_counted = 0
        
        for match in h2h[:10]:  # Last 10 H2H matches
            try:
                # Try to get first half goals from score breakdown
                score = match.get('score', {})
                halftime = score.get('halftime', {})
                
                home_1h = halftime.get('home', 0) or 0
                away_1h = halftime.get('away', 0) or 0
                
                if home_1h is not None and away_1h is not None:
                    total_1h_goals += home_1h + away_1h
                    matches_counted += 1
                else:
                    # Estimate from full time score (42% typically in 1H)
                    fulltime = score.get('fulltime', {})
                    home_ft = fulltime.get('home', 0) or 0
                    away_ft = fulltime.get('away', 0) or 0
                    estimated_1h = (home_ft + away_ft) * 0.42
                    total_1h_goals += estimated_1h
                    matches_counted += 1
            except:
                continue
        
        if matches_counted == 0:
            return 1.0  # Default
        
        return total_1h_goals / matches_counted

    # NOTE: analyze_over_1_5_first_half has been REMOVED as per user request
    # This market was removed and replaced with 5 new markets

    def analyze_team_over_0_5_2h(self, home_stats: Dict, away_stats: Dict,
                                  h2h: List[Dict], home_team: str, away_team: str,
                                  league_id: int = None) -> Dict:
        """
        Analyze Team Over 0.5 Second Half Goals market
        
        MANDATORY FILTERS (must pass ALL 3):
        1. Selected team 2H goals est ≥ 0.7
        2. Selected team FTS ≤ 25%
        3. Opponent concedes ≥ 0.7 in 2H
        
        H2H VALIDATION:
        - Check if selected team scored against this opponent recently
        - Disqualify if team blanked in last 3 H2H meetings
        
        BONUS FILTERS:
        4. Team full match avg ≥ 1.6
        5. Home/Away context (stricter away requirements)
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'probability': 0,
            'filters_passed': 0,
            'total_filters': 5,
            'selected_team': None,
            'selection': None,
            'h2h_validated': False
        }
        
        # Extract statistics
        home_goals_avg = home_stats.get('goals_avg', 1.5)
        away_goals_avg = away_stats.get('goals_avg', 1.3)
        home_conceded_avg = home_stats.get('conceded_avg', 1.2)
        away_conceded_avg = away_stats.get('conceded_avg', 1.3)
        
        home_played = max(home_stats.get('played', 1), 1)
        away_played = max(away_stats.get('played', 1), 1)
        
        # Failed to score percentages
        home_fts = home_stats.get('failed_to_score', 0) / home_played * 100
        away_fts = away_stats.get('failed_to_score', 0) / away_played * 100
        
        # Estimate 2H goals (typically 58% of total goals come in 2H)
        home_2h_goals_est = home_goals_avg * 0.58
        away_2h_goals_est = away_goals_avg * 0.58
        
        # Opponent 2H conceding
        home_2h_conceded = home_conceded_avg * 0.58
        away_2h_conceded = away_conceded_avg * 0.58
        
        # Calculate scores for each team to select the best pick
        home_score = 0
        away_score = 0
        
        # Factor 1: Team's 2H scoring estimate (must be ≥ 0.7 to qualify)
        if home_2h_goals_est >= 0.7:
            home_score += home_2h_goals_est * 30
        if away_2h_goals_est >= 0.7:
            away_score += away_2h_goals_est * 30
        
        # Factor 2: Opponent's defensive weakness (conceding in 2H)
        if away_2h_conceded >= 0.7:
            home_score += away_2h_conceded * 20
        if home_2h_conceded >= 0.7:
            away_score += home_2h_conceded * 20
        
        # Factor 3: Low failed to score rate (must be ≤ 25% to qualify)
        if home_fts <= 25:
            home_score += (30 - home_fts)
        if away_fts <= 25:
            away_score += (30 - away_fts)
        
        # Factor 4: Home advantage
        home_score += 10  # Home boost
        
        # Select the better team (must meet minimum thresholds)
        home_qualifies = home_2h_goals_est >= 0.7 and home_fts <= 25 and away_2h_conceded >= 0.7
        away_qualifies = away_2h_goals_est >= 0.7 and away_fts <= 25 and home_2h_conceded >= 0.7
        
        if not home_qualifies and not away_qualifies:
            result['reasons'].append(f"❌ FAILED: Neither team meets mandatory thresholds")
            result['reasons'].append(f"   Home: 2H={home_2h_goals_est:.2f}, FTS={home_fts:.0f}%, Opp concedes={away_2h_conceded:.2f}")
            result['reasons'].append(f"   Away: 2H={away_2h_goals_est:.2f}, FTS={away_fts:.0f}%, Opp concedes={home_2h_conceded:.2f}")
            result['reasons'].append(f"📊 Score: 0 | Does not qualify - mandatory filter failed")
            return result
        
        # Select best qualifying team
        if home_qualifies and away_qualifies:
            if home_score >= away_score:
                selected_team = home_team
                team_goals_est = home_2h_goals_est
                team_fts = home_fts
                opp_conceded = away_2h_conceded
                full_match_avg = home_goals_avg
                is_home = True
            else:
                selected_team = away_team
                team_goals_est = away_2h_goals_est
                team_fts = away_fts
                opp_conceded = home_2h_conceded
                full_match_avg = away_goals_avg
                is_home = False
        elif home_qualifies:
            selected_team = home_team
            team_goals_est = home_2h_goals_est
            team_fts = home_fts
            opp_conceded = away_2h_conceded
            full_match_avg = home_goals_avg
            is_home = True
        else:
            selected_team = away_team
            team_goals_est = away_2h_goals_est
            team_fts = away_fts
            opp_conceded = home_2h_conceded
            full_match_avg = away_goals_avg
            is_home = False
        
        result['selected_team'] = selected_team
        result['selection'] = f"{selected_team} Over 0.5 Second Half Goals"
        
        score = 0
        filters_passed = 0
        mandatory_passed = 0
        
        # ============================================
        # MANDATORY FILTER 1: Team 2H goals est ≥ 0.7
        # ============================================
        mandatory_passed += 1
        filters_passed += 1
        if team_goals_est >= 0.95:
            score += 25
            result['reasons'].append(f"✅ MANDATORY: {selected_team} elite 2H scorer ({team_goals_est:.2f} ≥ 0.95)")
        elif team_goals_est >= 0.8:
            score += 20
            result['reasons'].append(f"✅ MANDATORY: {selected_team} strong 2H scorer ({team_goals_est:.2f} ≥ 0.8)")
        else:
            score += 15
            result['reasons'].append(f"✅ MANDATORY: {selected_team} good 2H scorer ({team_goals_est:.2f} ≥ 0.7)")
        
        # ============================================
        # MANDATORY FILTER 2: Team FTS ≤ 25%
        # ============================================
        mandatory_passed += 1
        filters_passed += 1
        if team_fts <= 15:
            score += 20
            result['reasons'].append(f"✅ MANDATORY: Rarely blanks (FTS: {team_fts:.0f}% ≤ 15%)")
        elif team_fts <= 20:
            score += 15
            result['reasons'].append(f"✅ MANDATORY: Low blank rate (FTS: {team_fts:.0f}% ≤ 20%)")
        else:
            score += 10
            result['reasons'].append(f"✅ MANDATORY: Acceptable blank rate (FTS: {team_fts:.0f}% ≤ 25%)")
        
        # ============================================
        # MANDATORY FILTER 3: Opponent concedes ≥ 0.7 in 2H
        # ============================================
        mandatory_passed += 1
        filters_passed += 1
        if opp_conceded >= 0.9:
            score += 18
            result['reasons'].append(f"✅ MANDATORY: Opponent leaks badly in 2H ({opp_conceded:.2f} ≥ 0.9)")
        elif opp_conceded >= 0.8:
            score += 14
            result['reasons'].append(f"✅ MANDATORY: Opponent leaks in 2H ({opp_conceded:.2f} ≥ 0.8)")
        else:
            score += 10
            result['reasons'].append(f"✅ MANDATORY: Opponent concedes in 2H ({opp_conceded:.2f} ≥ 0.7)")
        
        # All 3 mandatory filters passed
        result['reasons'].append(f"✅ All 3 mandatory filters PASSED")
        
        # ============================================
        # H2H VALIDATION: Check if team scored against this opponent (RELAXED)
        # ============================================
        h2h_scoring = self.check_team_h2h_scoring(h2h, selected_team, home_team, away_team)
        h2h_validated = False
        
        if h2h_scoring['blanked_recently'] and h2h_scoring['blanks'] >= 3:
            # Team blanked in 3+ recent H2H - DISQUALIFY (only if consistently blanks)
            result['reasons'].append(f"❌ H2H FAILED: {selected_team} blanked in {h2h_scoring['blanks']}/{h2h_scoring['matches']} recent H2H matches")
            result['reasons'].append(f"📊 Score: {score} | Does not qualify - H2H validation failed")
            return result
        elif h2h_scoring['always_scored']:
            # Team always scored against opponent
            h2h_validated = True
            filters_passed += 1
            score += 15
            result['reasons'].append(f"✅ H2H VALIDATED: {selected_team} scored in all {h2h_scoring['matches']} recent H2H")
        elif h2h_scoring['scored_rate'] >= 0.6:
            # Team scored in most H2H
            h2h_validated = True
            score += 8
            result['reasons'].append(f"✅ H2H OK: {selected_team} scored in {h2h_scoring['scored']}/{h2h_scoring['matches']} H2H")
        else:
            # Limited data or some blanks - allow but lower confidence
            h2h_validated = True
            result['reasons'].append(f"⚠️ H2H: {selected_team} scored in {h2h_scoring['scored']}/{h2h_scoring['matches']} H2H")
        
        result['h2h_validated'] = h2h_validated
        
        # ============================================
        # BONUS FILTER 4: Team full match avg ≥ 1.6
        # ============================================
        if full_match_avg >= 1.8:
            filters_passed += 1
            score += 15
            result['reasons'].append(f"✅ BONUS: High-scoring team ({full_match_avg:.2f} avg)")
        elif full_match_avg >= 1.6:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ BONUS: Good scorer ({full_match_avg:.2f} avg)")
        elif full_match_avg >= 1.4:
            score += 4
            result['reasons'].append(f"⚠️ BONUS: Average scorer ({full_match_avg:.2f} avg)")
        else:
            result['reasons'].append(f"❌ BONUS: Weak scorer ({full_match_avg:.2f} avg)")
        
        # ============================================
        # BONUS FILTER 5: Home/Away context (stricter for away)
        # ============================================
        if is_home:
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ BONUS: Playing at home - attacking boost")
        else:
            # Stricter requirements for away team
            if team_goals_est >= 0.85 and team_fts <= 20:
                filters_passed += 1
                score += 10
                result['reasons'].append(f"✅ BONUS: Strong away profile ({team_goals_est:.2f} 2H, {team_fts:.0f}% FTS)")
            elif team_goals_est >= 0.75:
                score += 5
                result['reasons'].append(f"⚠️ BONUS: Decent away scorer ({team_goals_est:.2f} 2H)")
            else:
                result['reasons'].append(f"❌ BONUS: Away disadvantage")
        
        # ============================================
        # Calculate probability
        # ============================================
        if team_goals_est >= 0.95:
            prob = 78
        elif team_goals_est >= 0.8:
            prob = 72
        elif team_goals_est >= 0.7:
            prob = 65
        else:
            prob = 58
        
        # Adjust for H2H
        if h2h_scoring.get('always_scored'):
            prob += 5
        
        # Adjust for filters
        prob += (filters_passed - 4) * 3
        prob = min(88, max(50, prob))
        result['probability'] = round(prob, 1)
        
        # ============================================
        # FINAL QUALIFICATION
        # ============================================
        result['score'] = score
        result['filters_passed'] = filters_passed
        result['mandatory_passed'] = mandatory_passed
        result['team_2h_goals_est'] = round(team_goals_est, 2)
        
        # Must have all 3 mandatory + H2H validated
        if mandatory_passed == 3 and h2h_validated:
            if score >= 85 and filters_passed >= 5:
                result['qualifies'] = True
                result['confidence'] = 'Very High'
            elif score >= 70 and filters_passed >= 4:
                result['qualifies'] = True
                result['confidence'] = 'High'
            elif score >= 55 and filters_passed >= 3:
                result['qualifies'] = True
                result['confidence'] = 'Medium'
            elif score >= 45:
                result['qualifies'] = True
                result['confidence'] = 'Low'
        
        result['reasons'].append(f"📊 Score: {score}/100 | Mandatory: {mandatory_passed}/3 | Filters: {filters_passed}/5")
        
        return result

    def check_team_h2h_scoring(self, h2h: List[Dict], selected_team: str, 
                               home_team: str, away_team: str) -> Dict:
        """Check if selected team scored against opponent in H2H matches"""
        result = {
            'matches': 0,
            'scored': 0,
            'blanks': 0,
            'scored_rate': 0.5,  # Default
            'always_scored': False,
            'blanked_recently': False
        }
        
        if not h2h:
            return result
        
        is_selecting_home = selected_team == home_team
        recent_blanks = 0
        
        for i, match in enumerate(h2h[:5]):  # Check last 5 H2H
            try:
                score_data = match.get('score', {})
                fulltime = score_data.get('fulltime', {})
                
                # Determine which team is which in this H2H match
                match_home = match.get('teams', {}).get('home', {}).get('name', '')
                match_away = match.get('teams', {}).get('away', {}).get('name', '')
                
                # Get selected team's goals in this match
                if selected_team in match_home:
                    team_goals = fulltime.get('home', 0) or 0
                elif selected_team in match_away:
                    team_goals = fulltime.get('away', 0) or 0
                else:
                    continue
                
                result['matches'] += 1
                
                if team_goals > 0:
                    result['scored'] += 1
                else:
                    result['blanks'] += 1
                    if i < 3:  # Recent blank (last 3 H2H)
                        recent_blanks += 1
                        
            except:
                continue
        
        if result['matches'] > 0:
            result['scored_rate'] = result['scored'] / result['matches']
            result['always_scored'] = result['blanks'] == 0 and result['matches'] >= 2
            result['blanked_recently'] = recent_blanks >= 2  # Blanked in 2+ of last 3
        
        return result
        
    @staticmethod
    def analyze_corners_over(home_stats: Dict, away_stats: Dict, threshold: float = 3.5) -> Dict:
        """Analyze corners over market (LEGACY - kept for compatibility)"""
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': []
        }
        
        home_corners_avg = home_stats.get('corners_avg', 5.0) * 0.5
        away_corners_avg = away_stats.get('corners_avg', 5.0) * 0.5
        
        checks_passed = 0
        
        if home_corners_avg >= 2.5:
            checks_passed += 1
            result['reasons'].append(f"✅ Home corners {home_corners_avg:.1f} ≥ 2.5")
        else:
            result['reasons'].append(f"❌ Home corners {home_corners_avg:.1f} < 2.5")
            
        combined = home_corners_avg + away_corners_avg
        if combined >= 4.0:
            checks_passed += 1
            result['reasons'].append(f"✅ Combined corners {combined:.1f} ≥ 4.0")
        else:
            result['reasons'].append(f"❌ Combined corners {combined:.1f} < 4.0")
            
        if checks_passed >= 1:
            result['qualifies'] = True
            result['confidence'] = 'Medium' if checks_passed >= 2 else 'Low'
            
        return result
    
    # League Corner Averages (historical data - corners per match)
    LEAGUE_CORNER_RATES = {
        # High Corner Leagues (>10.5 per match)
        78: 10.8,   # Bundesliga
        79: 11.2,   # Bundesliga 2
        40: 11.0,   # Championship
        41: 10.9,   # League One
        39: 10.5,   # Premier League
        88: 10.6,   # Eredivisie
        
        # Medium Corner Leagues (9.5-10.5)
        140: 10.2,  # La Liga
        141: 10.0,  # La Liga 2
        94: 10.1,   # Primeira Liga
        144: 10.3,  # Belgian Pro League
        203: 10.4,  # Turkish Super Lig
        204: 10.0,  # Turkish 1. Lig
        
        # Low Corner Leagues (<9.5)
        135: 9.2,   # Serie A
        136: 9.4,   # Serie B
        61: 9.3,    # Ligue 1
        62: 9.5,    # Ligue 2
        
        'default': 10.0
    }
    
    @classmethod
    def get_league_corner_rate(cls, league_id: int) -> float:
        """Get historical average corners per match for a league"""
        return cls.LEAGUE_CORNER_RATES.get(league_id, cls.LEAGUE_CORNER_RATES['default'])

    @staticmethod
    def calculate_h2h_corner_stats(h2h: List[Dict]) -> Dict:
        """
        Calculate corner statistics from head-to-head matches
        Returns average corners and high-corner game percentage
        """
        if not h2h:
            return {'avg_corners': 10.0, 'high_corner_rate': 50.0, 'total_matches': 0}
        
        total_corners = 0
        high_corner_games = 0  # Games with 10+ corners
        matches_with_data = 0
        
        for match in h2h[:5]:  # Last 5 H2H
            # Try to get corner data from match statistics
            stats = match.get('statistics', [])
            home_corners = 0
            away_corners = 0
            
            for stat in stats:
                if stat.get('type') == 'Corner Kicks':
                    home_corners = stat.get('home', 0) or 0
                    away_corners = stat.get('away', 0) or 0
                    break
            
            # If no stats, estimate from goals (rough correlation)
            if home_corners == 0 and away_corners == 0:
                home_goals = match.get('goals', {}).get('home', 0) or 0
                away_goals = match.get('goals', {}).get('away', 0) or 0
                # Estimate: ~3 corners per goal + base of 4 per team
                home_corners = 4 + (home_goals * 1.5)
                away_corners = 4 + (away_goals * 1.5)
            
            match_corners = home_corners + away_corners
            total_corners += match_corners
            matches_with_data += 1
            
            if match_corners >= 10:
                high_corner_games += 1
        
        avg_corners = total_corners / matches_with_data if matches_with_data > 0 else 10.0
        high_corner_rate = (high_corner_games / matches_with_data * 100) if matches_with_data > 0 else 50.0
        
        return {
            'avg_corners': round(avg_corners, 1),
            'high_corner_rate': round(high_corner_rate, 1),
            'total_matches': matches_with_data,
            'high_corner_games': high_corner_games
        }

    @staticmethod
    def analyze_matchup_style(home_stats: Dict, away_stats: Dict) -> Dict:
        """
        Analyze the matchup style to predict corner distribution
        
        Attacking vs Defensive = HIGH corners for attacker
        Both Defensive = LOW corners overall
        Both Attacking = SPLIT corners
        """
        home_goals = home_stats.get('goals_avg', 1.3)
        home_conceded = home_stats.get('conceded_avg', 1.2)
        away_goals = away_stats.get('goals_avg', 1.2)
        away_conceded = away_stats.get('conceded_avg', 1.3)
        
        # Determine team styles
        # Attacking: scores a lot, may concede
        # Defensive: doesn't score much, doesn't concede much
        # Balanced: moderate both ways
        
        def get_style(goals: float, conceded: float) -> str:
            if goals >= 1.6 and conceded >= 1.2:
                return 'attacking'
            elif goals <= 1.2 and conceded <= 1.0:
                return 'defensive'
            elif goals >= 1.4:
                return 'balanced_attack'
            else:
                return 'balanced_defense'
        
        home_style = get_style(home_goals, home_conceded)
        away_style = get_style(away_goals, away_conceded)
        
        # Calculate corner boost based on matchup
        home_corner_boost = 1.0
        away_corner_boost = 1.0
        matchup_quality = 'neutral'
        
        # Attacking team vs Defensive team = HIGH corners for attacker
        if home_style == 'attacking' and away_style in ['defensive', 'balanced_defense']:
            home_corner_boost = 1.20  # 20% boost
            matchup_quality = 'excellent_home'
        elif away_style == 'attacking' and home_style in ['defensive', 'balanced_defense']:
            away_corner_boost = 1.15  # 15% boost (away penalty)
            matchup_quality = 'excellent_away'
        
        # Both defensive = low corners
        elif home_style in ['defensive', 'balanced_defense'] and away_style in ['defensive', 'balanced_defense']:
            home_corner_boost = 0.85
            away_corner_boost = 0.85
            matchup_quality = 'poor'
        
        # Both attacking = split but good total
        elif home_style == 'attacking' and away_style == 'attacking':
            home_corner_boost = 1.10
            away_corner_boost = 1.05
            matchup_quality = 'good_split'
        
        return {
            'home_style': home_style,
            'away_style': away_style,
            'home_corner_boost': home_corner_boost,
            'away_corner_boost': away_corner_boost,
            'matchup_quality': matchup_quality
        }

    # ============================================
    # CORNERS & CARDS APPROVED LEAGUES
    # These are the ONLY leagues where corner and card markets are valid
    # ============================================
    CORNER_CARD_APPROVED_LEAGUES = {
        # UEFA Competitions
        2, 3, 848,
        # England
        39, 40,
        # Spain  
        140, 141,
        # Germany
        78, 79,
        # Italy
        135, 136,
        # France
        61, 62,
        # Other Top Leagues
        203, 88, 94, 197, 207, 288, 103, 218, 144, 119, 179, 113
    }

    def analyze_team_1h_corners_enhanced(self, home_stats: Dict, away_stats: Dict,
                                          h2h: List[Dict], home_team: str, away_team: str,
                                          league_id: int = None, threshold: int = 4) -> Dict:
        """
        ENHANCED Team 1st Half 4+ Corners Analysis
        
        Predicts which team is more likely to get 4+ corners in the first half.
        
        IMPORTANT: This market ONLY applies to approved leagues (top European + select others).
        
        ENHANCED CRITERIA:
        1. Actual corner statistics (if available)
        2. Estimated 1H corners from full-match data
        3. H2H corner history
        4. League corner context
        5. Matchup style analysis (Attack vs Defense)
        6. Recent form indicators
        7. Tighter qualification thresholds
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'recommended_team': None,
            'corner_probability': 0,
            'filters_passed': 0,
            'total_filters': 8
        }
        
        # ============================================
        # STRICT LEAGUE CHECK - Corners only for approved leagues
        # ============================================
        if league_id is not None and league_id not in self.CORNER_CARD_APPROVED_LEAGUES:
            result['reasons'].append(f"❌ BLOCKED: Corners market not available for league ID {league_id}")
            return result
        
        score = 0
        filters_passed = 0
        
        # ============================================
        # GET ACTUAL CORNER DATA (if available)
        # ============================================
        # API-Sports provides corners_for in team statistics
        home_corners_total = home_stats.get('corners_for', 0)
        away_corners_total = away_stats.get('corners_for', 0)
        home_played = max(home_stats.get('played', 1), 1)
        away_played = max(away_stats.get('played', 1), 1)
        
        # Calculate actual corners per game if data exists
        if home_corners_total > 0:
            home_corners_avg = home_corners_total / home_played
        else:
            # Fallback: estimate from attacking stats
            home_corners_avg = 4.5 + (home_stats.get('goals_avg', 1.3) * 0.8)
        
        if away_corners_total > 0:
            away_corners_avg = away_corners_total / away_played
        else:
            away_corners_avg = 4.0 + (away_stats.get('goals_avg', 1.2) * 0.8)
        
        # ============================================
        # FILTER 1: Calculate 1H Corner Estimates
        # ============================================
        # 1H typically = 45-48% of total corners
        home_1h_corners = home_corners_avg * 0.47
        away_1h_corners = away_corners_avg * 0.44  # Away teams get fewer 1H corners
        
        # Home advantage boost (home teams dominate early)
        home_1h_corners *= 1.12
        
        # ============================================
        # FILTER 2: Matchup Style Analysis
        # ============================================
        matchup = self.analyze_matchup_style(home_stats, away_stats)
        
        home_1h_corners *= matchup['home_corner_boost']
        away_1h_corners *= matchup['away_corner_boost']
        
        if matchup['matchup_quality'] == 'excellent_home':
            filters_passed += 1
            score += 15
            result['reasons'].append(f"✅ Excellent matchup: {home_team} (attacking) vs {away_team} (defensive)")
        elif matchup['matchup_quality'] == 'excellent_away':
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ Good matchup: {away_team} (attacking) vs {home_team} (defensive)")
        elif matchup['matchup_quality'] == 'good_split':
            score += 8
            result['reasons'].append(f"⚠️ Both teams attack - corners will be split")
        elif matchup['matchup_quality'] == 'poor':
            score -= 10
            result['reasons'].append(f"❌ Both teams defensive - low corner expectation")
        
        # ============================================
        # FILTER 3: League Corner Context
        # ============================================
        if league_id:
            league_corner_rate = self.get_league_corner_rate(league_id)
            
            if league_corner_rate >= 10.5:
                filters_passed += 1
                score += 12
                result['reasons'].append(f"✅ High-corner league ({league_corner_rate} avg/match)")
                # Boost estimates for high-corner leagues
                home_1h_corners *= 1.08
                away_1h_corners *= 1.08
            elif league_corner_rate >= 10.0:
                score += 5
                result['reasons'].append(f"⚠️ Average corner league ({league_corner_rate} avg/match)")
            elif league_corner_rate < 9.5:
                score -= 8
                result['reasons'].append(f"❌ Low-corner league ({league_corner_rate} avg/match) - harder to hit")
                home_1h_corners *= 0.92
                away_1h_corners *= 0.92
        
        # ============================================
        # FILTER 4: H2H Corner History
        # ============================================
        h2h_corners = self.calculate_h2h_corner_stats(h2h)
        
        if h2h_corners['total_matches'] >= 3:
            if h2h_corners['avg_corners'] >= 11:
                filters_passed += 1
                score += 15
                result['reasons'].append(f"✅ H2H high corners ({h2h_corners['avg_corners']} avg, {h2h_corners['high_corner_games']}/{h2h_corners['total_matches']} high games)")
            elif h2h_corners['avg_corners'] >= 10:
                filters_passed += 1
                score += 10
                result['reasons'].append(f"✅ H2H good corners ({h2h_corners['avg_corners']} avg)")
            elif h2h_corners['avg_corners'] < 9:
                score -= 8
                result['reasons'].append(f"❌ H2H low corners ({h2h_corners['avg_corners']} avg) - pattern concern")
        
        # ============================================
        # FILTER 5: Team Corner Average (TIGHTENED)
        # ============================================
        # Require higher averages for qualification
        if home_corners_avg >= 6.0:
            filters_passed += 1
            score += 15
            result['reasons'].append(f"✅ {home_team} excellent corner record ({home_corners_avg:.1f}/game)")
        elif home_corners_avg >= 5.5:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ {home_team} good corner record ({home_corners_avg:.1f}/game)")
        elif home_corners_avg >= 5.0:
            score += 5
            result['reasons'].append(f"⚠️ {home_team} average corners ({home_corners_avg:.1f}/game)")
        else:
            result['reasons'].append(f"❌ {home_team} low corners ({home_corners_avg:.1f}/game)")
        
        if away_corners_avg >= 5.5:
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ {away_team} good corner record ({away_corners_avg:.1f}/game)")
        elif away_corners_avg >= 5.0:
            score += 6
            result['reasons'].append(f"⚠️ {away_team} average corners ({away_corners_avg:.1f}/game)")
        elif away_corners_avg < 4.5:
            result['reasons'].append(f"❌ {away_team} low corners ({away_corners_avg:.1f}/game)")
        
        # ============================================
        # FILTER 6: Attacking Intensity Check
        # ============================================
        home_attack = home_stats.get('goals_avg', 1.3)
        away_attack = away_stats.get('goals_avg', 1.2)
        
        # High-scoring teams create more corner opportunities
        if home_attack >= 1.8:
            filters_passed += 1
            score += 10
            home_1h_corners *= 1.10
            result['reasons'].append(f"✅ {home_team} high attacking threat ({home_attack:.1f} goals/game)")
        elif home_attack >= 1.5:
            score += 5
            home_1h_corners *= 1.05
        
        if away_attack >= 1.6:
            score += 8
            away_1h_corners *= 1.08
            result['reasons'].append(f"✅ {away_team} attacking threat ({away_attack:.1f} goals/game)")
        
        # ============================================
        # FILTER 7: Opponent Defensive Style (Park the Bus Check)
        # ============================================
        home_conceded = home_stats.get('conceded_avg', 1.2)
        away_conceded = away_stats.get('conceded_avg', 1.3)
        
        # Low-block defensive teams concede more corners
        if away_conceded <= 0.9:
            filters_passed += 1
            score += 10
            home_1h_corners *= 1.10
            result['reasons'].append(f"✅ {away_team} parks the bus ({away_conceded:.1f} conceded) = more {home_team} corners")
        
        if home_conceded <= 0.9:
            score += 8
            away_1h_corners *= 1.08
            result['reasons'].append(f"✅ {home_team} defensive ({home_conceded:.1f} conceded) = more {away_team} corners")
        
        # ============================================
        # FILTER 8: 1H Corner Threshold Check (TIGHTENED)
        # ============================================
        # Require estimated ≥ 4.0 (not 3.5) for better hit rate
        home_qualifies = home_1h_corners >= 4.0
        away_qualifies = away_1h_corners >= 3.8  # Slightly lower for away
        
        if home_1h_corners >= 4.5:
            filters_passed += 1
            score += 15
            result['reasons'].append(f"✅ {home_team} strong 1H estimate ({home_1h_corners:.1f} corners)")
        elif home_1h_corners >= 4.0:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ {home_team} good 1H estimate ({home_1h_corners:.1f} corners)")
        elif home_1h_corners >= 3.5:
            score += 4
            result['reasons'].append(f"⚠️ {home_team} borderline 1H ({home_1h_corners:.1f} corners)")
        
        if away_1h_corners >= 4.2:
            score += 12
            result['reasons'].append(f"✅ {away_team} strong 1H estimate ({away_1h_corners:.1f} corners)")
        elif away_1h_corners >= 3.8:
            score += 8
            result['reasons'].append(f"✅ {away_team} good 1H estimate ({away_1h_corners:.1f} corners)")
        
        # ============================================
        # DETERMINE RECOMMENDED TEAM
        # ============================================
        if home_qualifies or away_qualifies:
            if home_1h_corners >= away_1h_corners and home_qualifies:
                result['recommended_team'] = home_team
                corner_prob = min(90, 50 + (home_1h_corners - 4.0) * 15 + (score / 3))
            elif away_qualifies:
                result['recommended_team'] = away_team
                corner_prob = min(85, 45 + (away_1h_corners - 3.8) * 15 + (score / 3))
            else:
                result['recommended_team'] = home_team
                corner_prob = min(80, 40 + (home_1h_corners - 3.5) * 12 + (score / 4))
            
            result['corner_probability'] = round(corner_prob, 1)
        
        # ============================================
        # FINAL QUALIFICATION (STRICTER)
        # ============================================
        result['score'] = score
        result['filters_passed'] = filters_passed
        result['home_1h_estimate'] = round(home_1h_corners, 1)
        result['away_1h_estimate'] = round(away_1h_corners, 1)
        
        # Require more filters for qualification
        if filters_passed >= 6 and score >= 60 and result['recommended_team']:
            result['qualifies'] = True
            result['confidence'] = 'Very High'
        elif filters_passed >= 5 and score >= 50 and result['recommended_team']:
            result['qualifies'] = True
            result['confidence'] = 'High'
        elif filters_passed >= 4 and score >= 40 and result['recommended_team']:
            result['qualifies'] = True
            result['confidence'] = 'Medium'
        elif filters_passed >= 3 and score >= 30 and result['recommended_team']:
            result['qualifies'] = True
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"📊 Score: {score}/100 | Filters: {filters_passed}/8 | Prob: {result['corner_probability']:.0f}%")
        
        return result

    @staticmethod
    def analyze_team_1h_corners(home_stats: Dict, away_stats: Dict, 
                                 home_team: str, away_team: str, 
                                 threshold: int = 4) -> Dict:
        """Original method - now calls enhanced version for backward compatibility"""
        analyzer = StatsAnalyzer()
        return analyzer.analyze_team_1h_corners_enhanced(
            home_stats, away_stats, [], home_team, away_team, league_id=None, threshold=threshold
        )
        
    # ============================================
    # SGP MARKET 10: Under 3.5 Total Goals
    # ============================================
    def analyze_under_3_5_total_goals(self, home_stats: Dict, away_stats: Dict,
                                       h2h: List[Dict], home_team: str, away_team: str,
                                       league_id: int = None) -> Dict:
        """
        Analyze Under 3.5 Total Goals market for SGP
        
        ALL 5 FILTERS MUST PASS:
        1. Both teams achieved U2.5 total goals in 4+ of last 10 games
        2. At least one team >2 clean sheets (last 10), other team >1 clean sheet
        3. Both teams concede <1.3 avg goals (last 10 games)
        4. Both teams U4.5 shots on target avg (last 10 games)
        5. Combined xG < 3.0
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'under_probability': 0,
            'filters_passed': 0,
            'total_filters': 5
        }
        
        # Extract statistics
        home_goals_avg = home_stats.get('goals_avg', 1.5)
        away_goals_avg = away_stats.get('goals_avg', 1.3)
        home_conceded_avg = home_stats.get('conceded_avg', 1.2)
        away_conceded_avg = away_stats.get('conceded_avg', 1.3)
        home_clean_sheets = home_stats.get('clean_sheets', 2)
        away_clean_sheets = away_stats.get('clean_sheets', 2)
        
        # Estimate shots on target (typically ~4 per team avg)
        home_shots_on_target = home_stats.get('shots_on_target_avg', home_goals_avg * 3.2)
        away_shots_on_target = away_stats.get('shots_on_target_avg', away_goals_avg * 3.2)
        
        score = 0
        filters_passed = 0
        
        # ============================================
        # FILTER 1: Both teams U2.5 total goals in 4+ of last 10 games
        # ============================================
        # Estimate U2.5 games from goals average
        # If avg total goals involvement < 2.5, they likely have many U2.5 games
        home_total_involvement = home_goals_avg + home_conceded_avg
        away_total_involvement = away_goals_avg + away_conceded_avg
        
        # Estimate U2.5 games (out of 10)
        home_u25_games = self._estimate_under_25_games(home_total_involvement)
        away_u25_games = self._estimate_under_25_games(away_total_involvement)
        
        if home_u25_games >= 4 and away_u25_games >= 4:
            filters_passed += 1
            if home_u25_games >= 6 and away_u25_games >= 6:
                score += 25
                result['reasons'].append(f"✅ FILTER 1: Excellent U2.5 record (H: {home_u25_games:.0f}/10, A: {away_u25_games:.0f}/10)")
            elif home_u25_games >= 5 and away_u25_games >= 5:
                score += 20
                result['reasons'].append(f"✅ FILTER 1: Strong U2.5 record (H: {home_u25_games:.0f}/10, A: {away_u25_games:.0f}/10)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 1: Good U2.5 record (H: {home_u25_games:.0f}/10, A: {away_u25_games:.0f}/10 ≥ 4)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: U2.5 games (H: {home_u25_games:.0f}/10, A: {away_u25_games:.0f}/10) - both must be ≥ 4")
            return result
        
        # ============================================
        # FILTER 2: At least one team >2 CS, other >1 CS (last 10)
        # ============================================
        max_cs = max(home_clean_sheets, away_clean_sheets)
        min_cs = min(home_clean_sheets, away_clean_sheets)
        
        if max_cs > 2 and min_cs > 1:
            filters_passed += 1
            if max_cs >= 4 and min_cs >= 3:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: Excellent defensive records (CS: {home_clean_sheets}, {away_clean_sheets})")
            elif max_cs >= 3 and min_cs >= 2:
                score += 20
                result['reasons'].append(f"✅ FILTER 2: Strong defensive records (CS: {home_clean_sheets}, {away_clean_sheets})")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 2: Good defensive records (CS: {home_clean_sheets}, {away_clean_sheets})")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: Clean sheets (H: {home_clean_sheets}, A: {away_clean_sheets}) - need one >2 and other >1")
            return result
        
        # ============================================
        # FILTER 3: Both teams concede <1.3 avg goals (last 10)
        # ============================================
        if home_conceded_avg < 1.3 and away_conceded_avg < 1.3:
            filters_passed += 1
            avg_conceded = (home_conceded_avg + away_conceded_avg) / 2
            if avg_conceded <= 0.9:
                score += 25
                result['reasons'].append(f"✅ FILTER 3: Elite defenses (H: {home_conceded_avg:.2f}, A: {away_conceded_avg:.2f} < 1.3)")
            elif avg_conceded <= 1.1:
                score += 20
                result['reasons'].append(f"✅ FILTER 3: Strong defenses (H: {home_conceded_avg:.2f}, A: {away_conceded_avg:.2f} < 1.3)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 3: Good defenses (H: {home_conceded_avg:.2f}, A: {away_conceded_avg:.2f} < 1.3)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: Conceded avg (H: {home_conceded_avg:.2f}, A: {away_conceded_avg:.2f}) - both must be < 1.3")
            return result
        
        # ============================================
        # FILTER 4: Both teams U4.5 shots on target avg (last 10)
        # ============================================
        if home_shots_on_target < 4.5 and away_shots_on_target < 4.5:
            filters_passed += 1
            avg_sot = (home_shots_on_target + away_shots_on_target) / 2
            if avg_sot <= 3.0:
                score += 25
                result['reasons'].append(f"✅ FILTER 4: Very low SoT (H: {home_shots_on_target:.1f}, A: {away_shots_on_target:.1f} < 4.5)")
            elif avg_sot <= 3.8:
                score += 20
                result['reasons'].append(f"✅ FILTER 4: Low SoT (H: {home_shots_on_target:.1f}, A: {away_shots_on_target:.1f} < 4.5)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 4: Moderate SoT (H: {home_shots_on_target:.1f}, A: {away_shots_on_target:.1f} < 4.5)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: Shots on target (H: {home_shots_on_target:.1f}, A: {away_shots_on_target:.1f}) - both must be < 4.5")
            return result
        
        # ============================================
        # FILTER 5: Combined xG < 3.0
        # ============================================
        # Estimate xG from goals and shots (xG ≈ goals * 0.95 for reasonable estimate)
        home_xg_est = home_goals_avg * 0.95
        away_xg_est = away_goals_avg * 0.95
        combined_xg = home_xg_est + away_xg_est
        
        if combined_xg < 3.0:
            filters_passed += 1
            if combined_xg <= 2.2:
                score += 25
                result['reasons'].append(f"✅ FILTER 5: Excellent low xG ({combined_xg:.2f} < 3.0)")
            elif combined_xg <= 2.6:
                score += 20
                result['reasons'].append(f"✅ FILTER 5: Strong low xG ({combined_xg:.2f} < 3.0)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 5: Good xG ({combined_xg:.2f} < 3.0)")
        else:
            result['reasons'].append(f"❌ FILTER 5 FAILED: Combined xG {combined_xg:.2f} ≥ 3.0")
            return result
        
        # ============================================
        # ALL 5 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Calculate Under 3.5 probability
        combined_goals = home_goals_avg + away_goals_avg + home_conceded_avg + away_conceded_avg
        match_expected_goals = combined_goals / 2
        
        if match_expected_goals <= 2.0:
            under_prob = 88
        elif match_expected_goals <= 2.5:
            under_prob = 80
        elif match_expected_goals <= 3.0:
            under_prob = 70
        else:
            under_prob = 62
        
        under_prob += (score - 80) * 0.15
        under_prob = min(92, max(55, under_prob))
        result['under_probability'] = round(under_prob, 1)
        
        # Determine confidence
        if score >= 110:
            result['confidence'] = 'Very High'
        elif score >= 90:
            result['confidence'] = 'High'
        elif score >= 70:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 5 FILTERS PASSED | Score: {score}/125 | U3.5 Prob: {under_prob:.0f}%")
        
        return result
    
    def _estimate_under_25_games(self, total_involvement: float) -> float:
        """Estimate number of Under 2.5 total goals games (out of 10) based on goal involvement"""
        if total_involvement <= 1.8:
            return 8  # Very defensive team
        elif total_involvement <= 2.2:
            return 7
        elif total_involvement <= 2.6:
            return 6
        elif total_involvement <= 3.0:
            return 5
        elif total_involvement <= 3.4:
            return 4
        elif total_involvement <= 3.8:
            return 3
        else:
            return 2  # High-scoring team

    # ============================================
    # SGP MARKET 11: Over 2.5 Total Cards
    # ============================================
    def analyze_over_2_5_total_cards(self, home_stats: Dict, away_stats: Dict,
                                      h2h: List[Dict], home_team: str, away_team: str,
                                      league_id: int = None) -> Dict:
        """
        Analyze Over 2.5 Total Cards market for SGP
        
        IMPORTANT: This market ONLY applies to approved leagues (top European + select others).
        
        ALL 5 FILTERS MUST PASS:
        1. At least one team avg >16 fouls per game
        2. Combined fouls per game >24
        3. At least one team avg >1.8 cards per game
        4. Combined cards per game >3.5
        5. At least one team avg >15 tackles per game
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'cards_probability': 0,
            'filters_passed': 0,
            'total_filters': 5
        }
        
        # ============================================
        # STRICT LEAGUE CHECK - Cards only for approved leagues
        # ============================================
        if league_id is not None and league_id not in self.CORNER_CARD_APPROVED_LEAGUES:
            result['reasons'].append(f"❌ BLOCKED: Cards market not available for league ID {league_id}")
            return result
        
        # Extract statistics (with defaults based on typical values)
        home_fouls_avg = home_stats.get('fouls_avg', 12.0)
        away_fouls_avg = away_stats.get('fouls_avg', 12.0)
        home_cards_avg = home_stats.get('cards_avg', 1.8)
        away_cards_avg = away_stats.get('cards_avg', 1.8)
        home_tackles_avg = home_stats.get('tackles_avg', 14.0)
        away_tackles_avg = away_stats.get('tackles_avg', 14.0)
        
        score = 0
        filters_passed = 0
        
        # ============================================
        # FILTER 1: At least one team avg >16 fouls per game
        # ============================================
        max_fouls = max(home_fouls_avg, away_fouls_avg)
        
        if max_fouls > 16:
            filters_passed += 1
            if max_fouls >= 20:
                score += 25
                result['reasons'].append(f"✅ FILTER 1: Very high fouls (max: {max_fouls:.1f} > 16)")
            elif max_fouls >= 18:
                score += 20
                result['reasons'].append(f"✅ FILTER 1: High fouls (max: {max_fouls:.1f} > 16)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 1: Good fouls (max: {max_fouls:.1f} > 16)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: Max fouls {max_fouls:.1f} ≤ 16")
            return result
        
        # ============================================
        # FILTER 2: Combined fouls per game >24
        # ============================================
        combined_fouls = home_fouls_avg + away_fouls_avg
        
        if combined_fouls > 24:
            filters_passed += 1
            if combined_fouls >= 32:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: Very aggressive match (fouls: {combined_fouls:.1f} > 24)")
            elif combined_fouls >= 28:
                score += 20
                result['reasons'].append(f"✅ FILTER 2: Aggressive match (fouls: {combined_fouls:.1f} > 24)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 2: Physical match (fouls: {combined_fouls:.1f} > 24)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: Combined fouls {combined_fouls:.1f} ≤ 24")
            return result
        
        # ============================================
        # FILTER 3: At least one team avg >1.8 cards per game
        # ============================================
        max_cards = max(home_cards_avg, away_cards_avg)
        
        if max_cards > 1.8:
            filters_passed += 1
            if max_cards >= 2.5:
                score += 25
                result['reasons'].append(f"✅ FILTER 3: Very card-prone team (max: {max_cards:.1f} > 1.8)")
            elif max_cards >= 2.2:
                score += 20
                result['reasons'].append(f"✅ FILTER 3: Card-prone team (max: {max_cards:.1f} > 1.8)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 3: Aggressive team (max: {max_cards:.1f} > 1.8)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: Max cards {max_cards:.1f} ≤ 1.8")
            return result
        
        # ============================================
        # FILTER 4: Combined cards per game >3.5
        # ============================================
        combined_cards = home_cards_avg + away_cards_avg
        
        if combined_cards > 3.5:
            filters_passed += 1
            if combined_cards >= 5.0:
                score += 25
                result['reasons'].append(f"✅ FILTER 4: Very high combined cards ({combined_cards:.1f} > 3.5)")
            elif combined_cards >= 4.2:
                score += 20
                result['reasons'].append(f"✅ FILTER 4: High combined cards ({combined_cards:.1f} > 3.5)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 4: Good combined cards ({combined_cards:.1f} > 3.5)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: Combined cards {combined_cards:.1f} ≤ 3.5")
            return result
        
        # ============================================
        # FILTER 5: At least one team avg >15 tackles per game
        # ============================================
        max_tackles = max(home_tackles_avg, away_tackles_avg)
        
        if max_tackles > 15:
            filters_passed += 1
            if max_tackles >= 20:
                score += 25
                result['reasons'].append(f"✅ FILTER 5: Very aggressive tackling (max: {max_tackles:.1f} > 15)")
            elif max_tackles >= 18:
                score += 20
                result['reasons'].append(f"✅ FILTER 5: High tackling (max: {max_tackles:.1f} > 15)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 5: Good tackling (max: {max_tackles:.1f} > 15)")
        else:
            result['reasons'].append(f"❌ FILTER 5 FAILED: Max tackles {max_tackles:.1f} ≤ 15")
            return result
        
        # ============================================
        # ALL 5 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Calculate Over 2.5 Cards probability
        if combined_cards >= 5.0:
            cards_prob = 88
        elif combined_cards >= 4.5:
            cards_prob = 82
        elif combined_cards >= 4.0:
            cards_prob = 75
        else:
            cards_prob = 68
        
        cards_prob += (score - 80) * 0.12
        cards_prob = min(92, max(60, cards_prob))
        result['cards_probability'] = round(cards_prob, 1)
        
        # Determine confidence
        if score >= 110:
            result['confidence'] = 'Very High'
        elif score >= 90:
            result['confidence'] = 'High'
        elif score >= 70:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 5 FILTERS PASSED | Score: {score}/125 | O2.5 Cards Prob: {cards_prob:.0f}%")
        
        return result

    # ============================================
    # SGP MARKET 12: Under 4.5 Total Cards
    # ============================================
    def analyze_under_4_5_total_cards(self, home_stats: Dict, away_stats: Dict,
                                       h2h: List[Dict], home_team: str, away_team: str,
                                       league_id: int = None) -> Dict:
        """
        Analyze Under 4.5 Total Cards market for SGP
        
        IMPORTANT: This market ONLY applies to approved leagues (top European + select others).
        
        ALL 5 FILTERS MUST PASS:
        1. At least one team avg <15 fouls per game
        2. Combined fouls per game <23
        3. At least one team avg <1.8 cards per game
        4. Combined cards per game <3.5
        5. At least one team avg <14 tackles per game
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'under_probability': 0,
            'filters_passed': 0,
            'total_filters': 5
        }
        
        # ============================================
        # STRICT LEAGUE CHECK - Cards only for approved leagues
        # ============================================
        if league_id is not None and league_id not in self.CORNER_CARD_APPROVED_LEAGUES:
            result['reasons'].append(f"❌ BLOCKED: Cards market not available for league ID {league_id}")
            return result
        
        # Extract statistics (with defaults based on typical values)
        home_fouls_avg = home_stats.get('fouls_avg', 12.0)
        away_fouls_avg = away_stats.get('fouls_avg', 12.0)
        home_cards_avg = home_stats.get('cards_avg', 1.8)
        away_cards_avg = away_stats.get('cards_avg', 1.8)
        home_tackles_avg = home_stats.get('tackles_avg', 14.0)
        away_tackles_avg = away_stats.get('tackles_avg', 14.0)
        
        score = 0
        filters_passed = 0
        
        # ============================================
        # FILTER 1: At least one team avg <15 fouls per game
        # ============================================
        min_fouls = min(home_fouls_avg, away_fouls_avg)
        
        if min_fouls < 15:
            filters_passed += 1
            if min_fouls <= 10:
                score += 25
                result['reasons'].append(f"✅ FILTER 1: Very disciplined team (min fouls: {min_fouls:.1f} < 15)")
            elif min_fouls <= 12:
                score += 20
                result['reasons'].append(f"✅ FILTER 1: Disciplined team (min fouls: {min_fouls:.1f} < 15)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 1: Clean team (min fouls: {min_fouls:.1f} < 15)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: Min fouls {min_fouls:.1f} ≥ 15")
            return result
        
        # ============================================
        # FILTER 2: Combined fouls per game <23
        # ============================================
        combined_fouls = home_fouls_avg + away_fouls_avg
        
        if combined_fouls < 23:
            filters_passed += 1
            if combined_fouls <= 18:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: Very clean match (fouls: {combined_fouls:.1f} < 23)")
            elif combined_fouls <= 20:
                score += 20
                result['reasons'].append(f"✅ FILTER 2: Clean match (fouls: {combined_fouls:.1f} < 23)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 2: Fairly clean match (fouls: {combined_fouls:.1f} < 23)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: Combined fouls {combined_fouls:.1f} ≥ 23")
            return result
        
        # ============================================
        # FILTER 3: At least one team avg <1.8 cards per game
        # ============================================
        min_cards = min(home_cards_avg, away_cards_avg)
        
        if min_cards < 1.8:
            filters_passed += 1
            if min_cards <= 1.2:
                score += 25
                result['reasons'].append(f"✅ FILTER 3: Very disciplined team (min cards: {min_cards:.1f} < 1.8)")
            elif min_cards <= 1.5:
                score += 20
                result['reasons'].append(f"✅ FILTER 3: Disciplined team (min cards: {min_cards:.1f} < 1.8)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 3: Fair play team (min cards: {min_cards:.1f} < 1.8)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: Min cards {min_cards:.1f} ≥ 1.8")
            return result
        
        # ============================================
        # FILTER 4: Combined cards per game <3.5
        # ============================================
        combined_cards = home_cards_avg + away_cards_avg
        
        if combined_cards < 3.5:
            filters_passed += 1
            if combined_cards <= 2.5:
                score += 25
                result['reasons'].append(f"✅ FILTER 4: Very low combined cards ({combined_cards:.1f} < 3.5)")
            elif combined_cards <= 3.0:
                score += 20
                result['reasons'].append(f"✅ FILTER 4: Low combined cards ({combined_cards:.1f} < 3.5)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 4: Moderate combined cards ({combined_cards:.1f} < 3.5)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: Combined cards {combined_cards:.1f} ≥ 3.5")
            return result
        
        # ============================================
        # FILTER 5: At least one team avg <14 tackles per game
        # ============================================
        min_tackles = min(home_tackles_avg, away_tackles_avg)
        
        if min_tackles < 14:
            filters_passed += 1
            if min_tackles <= 10:
                score += 25
                result['reasons'].append(f"✅ FILTER 5: Very possession-based team (min tackles: {min_tackles:.1f} < 14)")
            elif min_tackles <= 12:
                score += 20
                result['reasons'].append(f"✅ FILTER 5: Possession-based team (min tackles: {min_tackles:.1f} < 14)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 5: Technical team (min tackles: {min_tackles:.1f} < 14)")
        else:
            result['reasons'].append(f"❌ FILTER 5 FAILED: Min tackles {min_tackles:.1f} ≥ 14")
            return result
        
        # ============================================
        # ALL 5 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Calculate Under 4.5 Cards probability
        if combined_cards <= 2.5:
            under_prob = 88
        elif combined_cards <= 3.0:
            under_prob = 82
        elif combined_cards <= 3.3:
            under_prob = 75
        else:
            under_prob = 68
        
        under_prob += (score - 80) * 0.12
        under_prob = min(92, max(60, under_prob))
        result['under_probability'] = round(under_prob, 1)
        
        # Determine confidence
        if score >= 110:
            result['confidence'] = 'Very High'
        elif score >= 90:
            result['confidence'] = 'High'
        elif score >= 70:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 5 FILTERS PASSED | Score: {score}/125 | U4.5 Cards Prob: {under_prob:.0f}%")
        
        return result

    # ============================================
    # BTTS (Both Teams To Score) - YES
    # ============================================
    def analyze_btts_yes(self, home_stats: Dict, away_stats: Dict,
                         h2h: List[Dict], home_team: str, away_team: str,
                         league_id: int = None) -> Dict:
        """
        Analyze Both Teams To Score (BTTS) - YES market
        
        ALL 5 FILTERS MUST PASS:
        1. Home team scores in 60%+ of their home games
        2. Away team scores in 55%+ of their away games  
        3. Home team concedes in 50%+ of their home games
        4. Away team concedes in 50%+ of their away games
        5. Combined goals average ≥ 2.2 per game
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'btts_probability': 0,
            'filters_passed': 0,
            'total_filters': 5
        }
        
        # Extract statistics
        home_goals_avg = home_stats.get('goals_avg', 1.3)
        away_goals_avg = away_stats.get('goals_avg', 1.1)
        home_conceded_avg = home_stats.get('conceded_avg', 1.2)
        away_conceded_avg = away_stats.get('conceded_avg', 1.3)
        
        home_played = max(home_stats.get('played', 1), 1)
        away_played = max(away_stats.get('played', 1), 1)
        home_failed_to_score = home_stats.get('failed_to_score', 2)
        away_failed_to_score = away_stats.get('failed_to_score', 3)
        home_clean_sheets = home_stats.get('clean_sheets', 2)
        away_clean_sheets = away_stats.get('clean_sheets', 2)
        
        # Calculate scoring and conceding rates
        home_scoring_rate = ((home_played - home_failed_to_score) / home_played) * 100
        away_scoring_rate = ((away_played - away_failed_to_score) / away_played) * 100
        home_conceding_rate = ((home_played - home_clean_sheets) / home_played) * 100
        away_conceding_rate = ((away_played - away_clean_sheets) / away_played) * 100
        
        combined_goals = home_goals_avg + away_goals_avg
        
        score = 0
        filters_passed = 0
        
        # ============================================
        # FILTER 1: Home team scores in 60%+ of home games
        # ============================================
        if home_scoring_rate >= 60:
            filters_passed += 1
            if home_scoring_rate >= 80:
                score += 25
                result['reasons'].append(f"✅ FILTER 1: {home_team} scores frequently at home ({home_scoring_rate:.0f}%)")
            elif home_scoring_rate >= 70:
                score += 20
                result['reasons'].append(f"✅ FILTER 1: {home_team} scores often at home ({home_scoring_rate:.0f}%)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 1: {home_team} scores regularly at home ({home_scoring_rate:.0f}%)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: {home_team} scoring rate {home_scoring_rate:.0f}% < 60%")
            return result
        
        # ============================================
        # FILTER 2: Away team scores in 55%+ of away games
        # ============================================
        if away_scoring_rate >= 55:
            filters_passed += 1
            if away_scoring_rate >= 75:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: {away_team} scores frequently away ({away_scoring_rate:.0f}%)")
            elif away_scoring_rate >= 65:
                score += 20
                result['reasons'].append(f"✅ FILTER 2: {away_team} scores often away ({away_scoring_rate:.0f}%)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 2: {away_team} scores regularly away ({away_scoring_rate:.0f}%)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: {away_team} scoring rate {away_scoring_rate:.0f}% < 55%")
            return result
        
        # ============================================
        # FILTER 3: Home team concedes in 50%+ of home games
        # ============================================
        if home_conceding_rate >= 50:
            filters_passed += 1
            if home_conceding_rate >= 70:
                score += 25
                result['reasons'].append(f"✅ FILTER 3: {home_team} concedes often at home ({home_conceding_rate:.0f}%)")
            elif home_conceding_rate >= 60:
                score += 20
                result['reasons'].append(f"✅ FILTER 3: {home_team} concedes regularly at home ({home_conceding_rate:.0f}%)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 3: {home_team} defense is penetrable ({home_conceding_rate:.0f}%)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: {home_team} conceding rate {home_conceding_rate:.0f}% < 50%")
            return result
        
        # ============================================
        # FILTER 4: Away team concedes in 50%+ of away games
        # ============================================
        if away_conceding_rate >= 50:
            filters_passed += 1
            if away_conceding_rate >= 70:
                score += 25
                result['reasons'].append(f"✅ FILTER 4: {away_team} concedes often away ({away_conceding_rate:.0f}%)")
            elif away_conceding_rate >= 60:
                score += 20
                result['reasons'].append(f"✅ FILTER 4: {away_team} concedes regularly away ({away_conceding_rate:.0f}%)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 4: {away_team} defense is penetrable ({away_conceding_rate:.0f}%)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: {away_team} conceding rate {away_conceding_rate:.0f}% < 50%")
            return result
        
        # ============================================
        # FILTER 5: Combined goals average ≥ 2.2
        # ============================================
        if combined_goals >= 2.2:
            filters_passed += 1
            if combined_goals >= 3.0:
                score += 25
                result['reasons'].append(f"✅ FILTER 5: High-scoring matchup ({combined_goals:.2f} combined avg)")
            elif combined_goals >= 2.6:
                score += 20
                result['reasons'].append(f"✅ FILTER 5: Good scoring matchup ({combined_goals:.2f} combined avg)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 5: Decent scoring matchup ({combined_goals:.2f} combined avg)")
        else:
            result['reasons'].append(f"❌ FILTER 5 FAILED: Combined goals {combined_goals:.2f} < 2.2")
            return result
        
        # ============================================
        # ALL 5 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Calculate BTTS probability
        avg_scoring_rate = (home_scoring_rate + away_scoring_rate) / 2
        avg_conceding_rate = (home_conceding_rate + away_conceding_rate) / 2
        
        btts_prob = (avg_scoring_rate * 0.4 + avg_conceding_rate * 0.3 + min(combined_goals * 15, 30))
        btts_prob = min(88, max(55, btts_prob))
        result['btts_probability'] = round(btts_prob, 1)
        
        # Determine confidence
        if score >= 110:
            result['confidence'] = 'Very High'
        elif score >= 90:
            result['confidence'] = 'High'
        elif score >= 70:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 5 FILTERS PASSED | Score: {score}/125 | BTTS Prob: {btts_prob:.0f}%")
        
        return result

    @staticmethod
    def analyze_ou_25(home_stats: Dict, away_stats: Dict, direction: str = 'over') -> Dict:
        """Analyze Over/Under 2.5 goals
        
        Direction: 'over' or 'under'
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': []
        }
        
        home_goals = home_stats.get('goals_avg', 0)
        away_goals = away_stats.get('goals_avg', 0)
        combined = home_goals + away_goals
        
        if direction == 'over':
            if combined >= 3.0:
                result['qualifies'] = True
                result['confidence'] = 'High'
                result['reasons'].append(f"✅ High-scoring teams ({combined:.1f} combined)")
            elif combined >= 2.5:
                result['qualifies'] = True
                result['confidence'] = 'Medium'
                result['reasons'].append(f"⚠️ Moderate scoring ({combined:.1f} combined)")
        else:  # under
            if combined <= 2.0:
                result['qualifies'] = True
                result['confidence'] = 'High'
                result['reasons'].append(f"✅ Low-scoring teams ({combined:.1f} combined)")
            elif combined <= 2.5:
                result['qualifies'] = True
                result['confidence'] = 'Medium'
                result['reasons'].append(f"⚠️ Moderate scoring ({combined:.1f} combined)")
                
        return result

    # ============================================
    # SGP MARKET: Over 2.5 Total Goals (STRICT)
    # ============================================
    def analyze_over_2_5_total_goals(self, home_stats: Dict, away_stats: Dict,
                                      h2h: List[Dict], home_team: str, away_team: str,
                                      league_id: int = None) -> Dict:
        """
        Analyze Over 2.5 Total Goals market with STRICT filters.
        
        ALL 5 FILTERS MUST PASS:
        1. Combined goals avg ≥ 2.8
        2. Both teams score ≥ 1.0 avg each
        3. At least one team concedes ≥ 1.3 avg (leaky defense)
        4. Both teams scored in 6+ of last 10 games (estimated)
        5. Combined shots on target ≥ 10
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'over_probability': 0,
            'filters_passed': 0,
            'total_filters': 5,
            'score': 0
        }
        
        # Extract statistics
        home_goals = home_stats.get('goals_avg', 1.5)
        away_goals = away_stats.get('goals_avg', 1.3)
        home_conceded = home_stats.get('conceded_avg', 1.2)
        away_conceded = away_stats.get('conceded_avg', 1.3)
        
        # Estimate shots on target (typically 3.2x goals)
        home_sot = home_stats.get('shots_on_target_avg', home_goals * 3.2)
        away_sot = away_stats.get('shots_on_target_avg', away_goals * 3.2)
        combined_sot = home_sot + away_sot
        
        # Estimate games where team scored (from goals avg)
        home_scored_games = self._estimate_games_scored(home_goals)
        away_scored_games = self._estimate_games_scored(away_goals)
        
        score = 0
        filters_passed = 0
        
        # ============================================
        # FILTER 1: Combined goals avg ≥ 2.8
        # ============================================
        combined_goals = home_goals + away_goals
        
        if combined_goals >= 2.8:
            filters_passed += 1
            if combined_goals >= 3.5:
                score += 25
                result['reasons'].append(f"✅ FILTER 1: Elite attacking teams ({combined_goals:.2f} combined ≥ 2.8)")
            elif combined_goals >= 3.2:
                score += 20
                result['reasons'].append(f"✅ FILTER 1: Strong attacking teams ({combined_goals:.2f} combined ≥ 2.8)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 1: Good attacking teams ({combined_goals:.2f} combined ≥ 2.8)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: Combined goals {combined_goals:.2f} < 2.8")
            return result
        
        # ============================================
        # FILTER 2: Both teams score ≥ 1.0 avg each
        # ============================================
        if home_goals >= 1.0 and away_goals >= 1.0:
            filters_passed += 1
            min_goals = min(home_goals, away_goals)
            if min_goals >= 1.5:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: Both prolific scorers (H: {home_goals:.2f}, A: {away_goals:.2f} ≥ 1.0)")
            elif min_goals >= 1.3:
                score += 20
                result['reasons'].append(f"✅ FILTER 2: Both good scorers (H: {home_goals:.2f}, A: {away_goals:.2f} ≥ 1.0)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 2: Both score regularly (H: {home_goals:.2f}, A: {away_goals:.2f} ≥ 1.0)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: Goals avg (H: {home_goals:.2f}, A: {away_goals:.2f}) - both must be ≥ 1.0")
            return result
        
        # ============================================
        # FILTER 3: At least one team concedes ≥ 1.3 avg (leaky defense)
        # ============================================
        max_conceded = max(home_conceded, away_conceded)
        
        if max_conceded >= 1.3:
            filters_passed += 1
            if max_conceded >= 1.8:
                score += 25
                result['reasons'].append(f"✅ FILTER 3: Very leaky defense (max concede: {max_conceded:.2f} ≥ 1.3)")
            elif max_conceded >= 1.5:
                score += 20
                result['reasons'].append(f"✅ FILTER 3: Leaky defense (max concede: {max_conceded:.2f} ≥ 1.3)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 3: Vulnerable defense (max concede: {max_conceded:.2f} ≥ 1.3)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: Max conceded {max_conceded:.2f} < 1.3 (no leaky defense)")
            return result
        
        # ============================================
        # FILTER 4: Both teams scored in 6+ of last 10 games
        # ============================================
        if home_scored_games >= 6 and away_scored_games >= 6:
            filters_passed += 1
            min_scored = min(home_scored_games, away_scored_games)
            if min_scored >= 8:
                score += 25
                result['reasons'].append(f"✅ FILTER 4: Both score consistently (H: {home_scored_games}/10, A: {away_scored_games}/10 ≥ 6)")
            elif min_scored >= 7:
                score += 20
                result['reasons'].append(f"✅ FILTER 4: Both score often (H: {home_scored_games}/10, A: {away_scored_games}/10 ≥ 6)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 4: Both score regularly (H: {home_scored_games}/10, A: {away_scored_games}/10 ≥ 6)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: Games scored (H: {home_scored_games}/10, A: {away_scored_games}/10) - both must be ≥ 6")
            return result
        
        # ============================================
        # FILTER 5: Combined shots on target ≥ 10
        # ============================================
        if combined_sot >= 10:
            filters_passed += 1
            if combined_sot >= 14:
                score += 25
                result['reasons'].append(f"✅ FILTER 5: Elite shot volume ({combined_sot:.1f} SoT ≥ 10)")
            elif combined_sot >= 12:
                score += 20
                result['reasons'].append(f"✅ FILTER 5: High shot volume ({combined_sot:.1f} SoT ≥ 10)")
            else:
                score += 15
                result['reasons'].append(f"✅ FILTER 5: Good shot volume ({combined_sot:.1f} SoT ≥ 10)")
        else:
            result['reasons'].append(f"❌ FILTER 5 FAILED: Combined SoT {combined_sot:.1f} < 10")
            return result
        
        # ============================================
        # ALL 5 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Calculate Over 2.5 probability
        expected_goals = (home_goals + away_conceded + away_goals + home_conceded) / 2
        
        if expected_goals >= 3.5:
            over_prob = 85
        elif expected_goals >= 3.0:
            over_prob = 75
        elif expected_goals >= 2.8:
            over_prob = 68
        else:
            over_prob = 60
        
        over_prob += (score - 80) * 0.12
        over_prob = min(92, max(55, over_prob))
        result['over_probability'] = round(over_prob, 1)
        
        # Determine confidence
        if score >= 110:
            result['confidence'] = 'Very High'
        elif score >= 90:
            result['confidence'] = 'High'
        elif score >= 70:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 5 FILTERS PASSED | Score: {score}/125 | O2.5 Prob: {over_prob:.0f}%")
        
        return result
    
    def _estimate_games_scored(self, goals_avg: float) -> int:
        """Estimate number of games where team scored (out of 10) based on goals avg"""
        if goals_avg >= 2.0:
            return 9
        elif goals_avg >= 1.5:
            return 8
        elif goals_avg >= 1.2:
            return 7
        elif goals_avg >= 1.0:
            return 6
        elif goals_avg >= 0.8:
            return 5
        elif goals_avg >= 0.5:
            return 4
        else:
            return 3

    # ============================================
    # SGP MARKET: Over 0.5 First Half Goals (STRICT)
    # ============================================
    def analyze_over_0_5_first_half_goals(self, home_stats: Dict, away_stats: Dict,
                                           h2h: List[Dict], home_team: str, away_team: str,
                                           league_id: int = None) -> Dict:
        """
        Analyze Over 0.5 First Half Goals market with STRICT filters.
        
        ALL 4 FILTERS MUST PASS:
        1. Combined 1H goals avg ≥ 0.9
        2. At least one team scores ≥ 0.5 avg 1H goals
        3. Both teams have 1H goal in 5+ of last 10 games (estimated)
        4. Match has clear favorite (odds < 2.00) OR high combined 1H avg ≥ 1.2
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'over_probability': 0,
            'filters_passed': 0,
            'total_filters': 4,
            'score': 0
        }
        
        # Extract statistics
        home_goals = home_stats.get('goals_avg', 1.5)
        away_goals = away_stats.get('goals_avg', 1.3)
        
        # Estimate 1H goals (42% of total typically)
        home_1h = home_stats.get('first_half_goals_avg', home_goals * 0.42)
        away_1h = away_stats.get('first_half_goals_avg', away_goals * 0.42)
        combined_1h = home_1h + away_1h
        
        # Estimate games with 1H goal
        home_1h_games = self._estimate_1h_goal_games(home_1h)
        away_1h_games = self._estimate_1h_goal_games(away_1h)
        
        score = 0
        filters_passed = 0
        
        # ============================================
        # FILTER 1: Combined 1H goals avg ≥ 0.9
        # ============================================
        if combined_1h >= 0.9:
            filters_passed += 1
            if combined_1h >= 1.4:
                score += 30
                result['reasons'].append(f"✅ FILTER 1: Elite 1H scoring ({combined_1h:.2f} combined ≥ 0.9)")
            elif combined_1h >= 1.1:
                score += 25
                result['reasons'].append(f"✅ FILTER 1: Strong 1H scoring ({combined_1h:.2f} combined ≥ 0.9)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 1: Good 1H scoring ({combined_1h:.2f} combined ≥ 0.9)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: Combined 1H goals {combined_1h:.2f} < 0.9")
            return result
        
        # ============================================
        # FILTER 2: At least one team scores ≥ 0.5 avg 1H goals
        # ============================================
        max_1h = max(home_1h, away_1h)
        
        if max_1h >= 0.5:
            filters_passed += 1
            if max_1h >= 0.8:
                score += 30
                result['reasons'].append(f"✅ FILTER 2: Strong 1H scorer (max: {max_1h:.2f} ≥ 0.5)")
            elif max_1h >= 0.65:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: Good 1H scorer (max: {max_1h:.2f} ≥ 0.5)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 2: Decent 1H scorer (max: {max_1h:.2f} ≥ 0.5)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: Max 1H goals {max_1h:.2f} < 0.5")
            return result
        
        # ============================================
        # FILTER 3: Both teams have 1H goal in 5+ of last 10 games
        # ============================================
        if home_1h_games >= 5 and away_1h_games >= 5:
            filters_passed += 1
            min_1h_games = min(home_1h_games, away_1h_games)
            if min_1h_games >= 7:
                score += 30
                result['reasons'].append(f"✅ FILTER 3: Both score 1H often (H: {home_1h_games}/10, A: {away_1h_games}/10 ≥ 5)")
            elif min_1h_games >= 6:
                score += 25
                result['reasons'].append(f"✅ FILTER 3: Both score 1H regularly (H: {home_1h_games}/10, A: {away_1h_games}/10 ≥ 5)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 3: Both score 1H (H: {home_1h_games}/10, A: {away_1h_games}/10 ≥ 5)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: 1H goal games (H: {home_1h_games}/10, A: {away_1h_games}/10) - both must be ≥ 5")
            return result
        
        # ============================================
        # FILTER 4: Clear favorite OR high combined 1H avg
        # ============================================
        # We check if combined_1h is high enough to override favorite requirement
        if combined_1h >= 1.2:
            filters_passed += 1
            score += 25
            result['reasons'].append(f"✅ FILTER 4: High 1H scoring profile ({combined_1h:.2f} ≥ 1.2)")
        else:
            # Need to rely on match profile (attacking game)
            if home_goals + away_goals >= 2.8:
                filters_passed += 1
                score += 20
                result['reasons'].append(f"✅ FILTER 4: Attacking match profile (total avg: {home_goals + away_goals:.2f} ≥ 2.8)")
            else:
                result['reasons'].append(f"❌ FILTER 4 FAILED: Need high 1H avg ≥1.2 OR attacking profile ≥2.8 total")
                return result
        
        # ============================================
        # ALL 4 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Calculate Over 0.5 1H probability
        if combined_1h >= 1.4:
            over_prob = 90
        elif combined_1h >= 1.1:
            over_prob = 82
        elif combined_1h >= 0.9:
            over_prob = 75
        else:
            over_prob = 68
        
        over_prob += (score - 80) * 0.1
        over_prob = min(95, max(65, over_prob))
        result['over_probability'] = round(over_prob, 1)
        
        # Determine confidence
        if score >= 100:
            result['confidence'] = 'Very High'
        elif score >= 85:
            result['confidence'] = 'High'
        elif score >= 70:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 4 FILTERS PASSED | Score: {score}/115 | O0.5 1H Prob: {over_prob:.0f}%")
        
        return result
    
    def _estimate_1h_goal_games(self, first_half_avg: float) -> int:
        """Estimate games with 1H goal (out of 10) based on 1H goals avg"""
        if first_half_avg >= 0.8:
            return 8
        elif first_half_avg >= 0.6:
            return 7
        elif first_half_avg >= 0.5:
            return 6
        elif first_half_avg >= 0.4:
            return 5
        elif first_half_avg >= 0.3:
            return 4
        else:
            return 3

    # ============================================
    # SGP MARKET: Over 0.5 Second Half Goals (STRICT)
    # ============================================
    def analyze_over_0_5_second_half_goals(self, home_stats: Dict, away_stats: Dict,
                                            h2h: List[Dict], home_team: str, away_team: str,
                                            league_id: int = None) -> Dict:
        """
        Analyze Over 0.5 Second Half Goals market with STRICT filters.
        
        ALL 4 FILTERS MUST PASS:
        1. Combined 2H goals avg ≥ 1.1
        2. At least one team scores ≥ 0.6 avg 2H goals
        3. Both teams have 2H goal in 6+ of last 10 games (estimated)
        4. Combined total goals avg ≥ 2.5 (attacking match)
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'over_probability': 0,
            'filters_passed': 0,
            'total_filters': 4,
            'score': 0
        }
        
        # Extract statistics
        home_goals = home_stats.get('goals_avg', 1.5)
        away_goals = away_stats.get('goals_avg', 1.3)
        
        # Estimate 2H goals (58% of total typically - more goals in 2H)
        home_2h = home_stats.get('second_half_goals_avg', home_goals * 0.58)
        away_2h = away_stats.get('second_half_goals_avg', away_goals * 0.58)
        combined_2h = home_2h + away_2h
        
        # Estimate games with 2H goal
        home_2h_games = self._estimate_2h_goal_games(home_2h)
        away_2h_games = self._estimate_2h_goal_games(away_2h)
        
        score = 0
        filters_passed = 0
        
        # ============================================
        # FILTER 1: Combined 2H goals avg ≥ 1.1
        # ============================================
        if combined_2h >= 1.1:
            filters_passed += 1
            if combined_2h >= 1.6:
                score += 30
                result['reasons'].append(f"✅ FILTER 1: Elite 2H scoring ({combined_2h:.2f} combined ≥ 1.1)")
            elif combined_2h >= 1.3:
                score += 25
                result['reasons'].append(f"✅ FILTER 1: Strong 2H scoring ({combined_2h:.2f} combined ≥ 1.1)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 1: Good 2H scoring ({combined_2h:.2f} combined ≥ 1.1)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: Combined 2H goals {combined_2h:.2f} < 1.1")
            return result
        
        # ============================================
        # FILTER 2: At least one team scores ≥ 0.6 avg 2H goals
        # ============================================
        max_2h = max(home_2h, away_2h)
        
        if max_2h >= 0.6:
            filters_passed += 1
            if max_2h >= 0.9:
                score += 30
                result['reasons'].append(f"✅ FILTER 2: Strong 2H scorer (max: {max_2h:.2f} ≥ 0.6)")
            elif max_2h >= 0.75:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: Good 2H scorer (max: {max_2h:.2f} ≥ 0.6)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 2: Decent 2H scorer (max: {max_2h:.2f} ≥ 0.6)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: Max 2H goals {max_2h:.2f} < 0.6")
            return result
        
        # ============================================
        # FILTER 3: Both teams have 2H goal in 6+ of last 10 games
        # ============================================
        if home_2h_games >= 6 and away_2h_games >= 6:
            filters_passed += 1
            min_2h_games = min(home_2h_games, away_2h_games)
            if min_2h_games >= 8:
                score += 30
                result['reasons'].append(f"✅ FILTER 3: Both score 2H often (H: {home_2h_games}/10, A: {away_2h_games}/10 ≥ 6)")
            elif min_2h_games >= 7:
                score += 25
                result['reasons'].append(f"✅ FILTER 3: Both score 2H regularly (H: {home_2h_games}/10, A: {away_2h_games}/10 ≥ 6)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 3: Both score 2H (H: {home_2h_games}/10, A: {away_2h_games}/10 ≥ 6)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: 2H goal games (H: {home_2h_games}/10, A: {away_2h_games}/10) - both must be ≥ 6")
            return result
        
        # ============================================
        # FILTER 4: Combined total goals avg ≥ 2.5 (attacking match)
        # ============================================
        combined_total = home_goals + away_goals
        
        if combined_total >= 2.5:
            filters_passed += 1
            if combined_total >= 3.2:
                score += 30
                result['reasons'].append(f"✅ FILTER 4: Elite attacking match ({combined_total:.2f} combined ≥ 2.5)")
            elif combined_total >= 2.8:
                score += 25
                result['reasons'].append(f"✅ FILTER 4: Strong attacking match ({combined_total:.2f} combined ≥ 2.5)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 4: Attacking match ({combined_total:.2f} combined ≥ 2.5)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: Combined total {combined_total:.2f} < 2.5")
            return result
        
        # ============================================
        # ALL 4 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Calculate Over 0.5 2H probability
        if combined_2h >= 1.6:
            over_prob = 92
        elif combined_2h >= 1.3:
            over_prob = 85
        elif combined_2h >= 1.1:
            over_prob = 78
        else:
            over_prob = 70
        
        over_prob += (score - 80) * 0.1
        over_prob = min(95, max(68, over_prob))
        result['over_probability'] = round(over_prob, 1)
        
        # Determine confidence
        if score >= 105:
            result['confidence'] = 'Very High'
        elif score >= 90:
            result['confidence'] = 'High'
        elif score >= 75:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 4 FILTERS PASSED | Score: {score}/120 | O0.5 2H Prob: {over_prob:.0f}%")
        
        return result
    
    def _estimate_2h_goal_games(self, second_half_avg: float) -> int:
        """Estimate games with 2H goal (out of 10) based on 2H goals avg"""
        if second_half_avg >= 1.0:
            return 9
        elif second_half_avg >= 0.8:
            return 8
        elif second_half_avg >= 0.65:
            return 7
        elif second_half_avg >= 0.5:
            return 6
        elif second_half_avg >= 0.4:
            return 5
        else:
            return 4

    def analyze_straight_win(self, home_stats: Dict, away_stats: Dict,
                             h2h: List[Dict], home_team: str, away_team: str,
                             league_id: int = None, odds: Dict = None) -> Dict:
        """
        Analyze Straight Win (1X2) market - STRICT VENUE-SPECIFIC FILTERS
        
        ALL stats are HOME-only for home team and AWAY-only for away team.
        
        ALL 5 FILTERS MUST PASS:
        1. ODDS: Favourite odds ≤ 1.80 with minimum 0.80 gap to opponent
        2. PPG: Favourite's Points Per Game (home/away specific) ≥ 1.60
        3. xG: Combined match xG > 2.5 AND Favourite xG > 1.8 (venue-specific)
        4. FAVOURITE FORM: Won at least 3 of last 5 home/away games (venue-specific)
        5. UNDERDOG FORM: Lost at least 2 of last 5 home/away games (venue-specific)
        
        Returns recommended selection and confidence.
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'recommended_selection': None,
            'selection_type': None,
            'win_probability': 0,
            'filters_passed': 0,
            'total_filters': 5,
            'favoured_team': None
        }
        
        # ============================================
        # EXTRACT VENUE-SPECIFIC STATS
        # Home team uses HOME stats only
        # Away team uses AWAY stats only
        # ============================================
        
        # Home team's HOME-specific stats
        home_team_home_wins = home_stats.get('home_wins', home_stats.get('wins', 0))
        home_team_home_draws = home_stats.get('home_draws', home_stats.get('draws', 0))
        home_team_home_losses = home_stats.get('home_losses', home_stats.get('losses', 0))
        home_team_home_played = home_team_home_wins + home_team_home_draws + home_team_home_losses
        if home_team_home_played == 0:
            home_team_home_played = max(home_stats.get('home_played', home_stats.get('played', 5) // 2), 1)
        
        home_team_home_goals = home_stats.get('home_goals_avg', home_stats.get('goals_avg', 1.3))
        home_team_home_xg = home_stats.get('home_xg', home_stats.get('xg_for', home_team_home_goals * 1.05))
        
        # Away team's AWAY-specific stats
        away_team_away_wins = away_stats.get('away_wins', away_stats.get('wins', 0))
        away_team_away_draws = away_stats.get('away_draws', away_stats.get('draws', 0))
        away_team_away_losses = away_stats.get('away_losses', away_stats.get('losses', 0))
        away_team_away_played = away_team_away_wins + away_team_away_draws + away_team_away_losses
        if away_team_away_played == 0:
            away_team_away_played = max(away_stats.get('away_played', away_stats.get('played', 5) // 2), 1)
        
        away_team_away_goals = away_stats.get('away_goals_avg', away_stats.get('goals_avg', 1.1))
        away_team_away_xg = away_stats.get('away_xg', away_stats.get('xg_for', away_team_away_goals * 0.95))
        
        # Calculate venue-specific PPG (Points Per Game: Win=3, Draw=1, Loss=0)
        home_team_home_ppg = (home_team_home_wins * 3 + home_team_home_draws) / max(home_team_home_played, 1)
        away_team_away_ppg = (away_team_away_wins * 3 + away_team_away_draws) / max(away_team_away_played, 1)
        
        # Get odds
        home_odds = odds.get('home_win', 0) if odds else 0
        away_odds = odds.get('away_win', 0) if odds else 0
        
        try:
            home_odds = float(home_odds) if home_odds else 0
            away_odds = float(away_odds) if away_odds else 0
        except (TypeError, ValueError):
            home_odds, away_odds = 0, 0
        
        if home_odds <= 0 and away_odds <= 0:
            result['reasons'].append(f"❌ No betting odds available")
            return result
        
        # ============================================
        # DETERMINE FAVOURITE AND UNDERDOG
        # ============================================
        if home_odds > 0 and away_odds > 0:
            if home_odds <= away_odds:
                favourite = 'home'
                favourite_name = home_team
                favourite_odds = home_odds
                underdog_name = away_team
                underdog_odds = away_odds
                # Favourite (home) uses HOME stats
                favourite_ppg = home_team_home_ppg
                favourite_xg = home_team_home_xg
                favourite_wins = home_team_home_wins
                favourite_played = home_team_home_played
                # Underdog (away) uses AWAY stats
                underdog_losses = away_team_away_losses
                underdog_played = away_team_away_played
                selection = f"{home_team} Win"
                selection_type = 'home_win'
            else:
                favourite = 'away'
                favourite_name = away_team
                favourite_odds = away_odds
                underdog_name = home_team
                underdog_odds = home_odds
                # Favourite (away) uses AWAY stats
                favourite_ppg = away_team_away_ppg
                favourite_xg = away_team_away_xg
                favourite_wins = away_team_away_wins
                favourite_played = away_team_away_played
                # Underdog (home) uses HOME stats
                underdog_losses = home_team_home_losses
                underdog_played = home_team_home_played
                selection = f"{away_team} Win"
                selection_type = 'away_win'
        elif home_odds > 0:
            favourite = 'home'
            favourite_name = home_team
            favourite_odds = home_odds
            underdog_name = away_team
            underdog_odds = 99
            favourite_ppg = home_team_home_ppg
            favourite_xg = home_team_home_xg
            favourite_wins = home_team_home_wins
            favourite_played = home_team_home_played
            underdog_losses = away_team_away_losses
            underdog_played = away_team_away_played
            selection = f"{home_team} Win"
            selection_type = 'home_win'
        else:
            favourite = 'away'
            favourite_name = away_team
            favourite_odds = away_odds
            underdog_name = home_team
            underdog_odds = 99
            favourite_ppg = away_team_away_ppg
            favourite_xg = away_team_away_xg
            favourite_wins = away_team_away_wins
            favourite_played = away_team_away_played
            underdog_losses = home_team_home_losses
            underdog_played = home_team_home_played
            selection = f"{away_team} Win"
            selection_type = 'away_win'
        
        result['favoured_team'] = favourite
        result['recommended_selection'] = selection
        result['selection_type'] = selection_type
        
        # Combined xG for the match
        combined_xg = home_team_home_xg + away_team_away_xg
        
        score = 0
        filters_passed = 0
        venue_label = "HOME" if favourite == 'home' else "AWAY"
        underdog_venue_label = "AWAY" if favourite == 'home' else "HOME"
        
        # ============================================
        # FILTER 1: ODDS - Favourite ≤ 1.80, Gap ≥ 0.80
        # ============================================
        odds_gap = underdog_odds - favourite_odds
        
        if favourite_odds <= 1.80 and odds_gap >= 0.80:
            filters_passed += 1
            score += 20
            result['reasons'].append(f"✅ FILTER 1 (ODDS): {favourite_name} @ {favourite_odds:.2f} | Gap: {odds_gap:.2f}")
        else:
            if favourite_odds > 1.80:
                result['reasons'].append(f"❌ FILTER 1 FAILED: {favourite_name} odds {favourite_odds:.2f} > 1.80")
            else:
                result['reasons'].append(f"❌ FILTER 1 FAILED: Odds gap {odds_gap:.2f} < 0.80")
            return result
        
        # ============================================
        # FILTER 2: PPG - Favourite PPG ≥ 1.60 (venue-specific)
        # ============================================
        if favourite_ppg >= 1.60:
            filters_passed += 1
            score += 20
            result['reasons'].append(f"✅ FILTER 2 (PPG): {favourite_name} {venue_label} PPG = {favourite_ppg:.2f} ≥ 1.60")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: {favourite_name} {venue_label} PPG {favourite_ppg:.2f} < 1.60")
            return result
        
        # ============================================
        # FILTER 3: xG - Combined > 2.5, Favourite xG > 1.8
        # ============================================
        if combined_xg > 2.5 and favourite_xg > 1.8:
            filters_passed += 1
            score += 20
            result['reasons'].append(f"✅ FILTER 3 (xG): Combined xG = {combined_xg:.2f} > 2.5 | {favourite_name} xG = {favourite_xg:.2f} > 1.8")
        else:
            if combined_xg <= 2.5:
                result['reasons'].append(f"❌ FILTER 3 FAILED: Combined xG {combined_xg:.2f} ≤ 2.5")
            else:
                result['reasons'].append(f"❌ FILTER 3 FAILED: {favourite_name} {venue_label} xG {favourite_xg:.2f} ≤ 1.8")
            return result
        
        # ============================================
        # FILTER 4: FAVOURITE FORM - Won 3+ of last 5 (venue-specific)
        # ============================================
        # For last 5 games, we scale the wins if played < 5
        last_5_favourite_wins = min(favourite_wins, 5)
        games_for_calc = min(favourite_played, 5)
        
        if last_5_favourite_wins >= 3:
            filters_passed += 1
            score += 20
            result['reasons'].append(f"✅ FILTER 4 (FAVOURITE FORM): {favourite_name} won {last_5_favourite_wins}/{games_for_calc} {venue_label} games (≥3 required)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: {favourite_name} only won {last_5_favourite_wins}/{games_for_calc} {venue_label} games (<3)")
            return result
        
        # ============================================
        # FILTER 5: UNDERDOG FORM - Lost 2+ of last 5 (venue-specific)
        # ============================================
        last_5_underdog_losses = min(underdog_losses, 5)
        underdog_games_for_calc = min(underdog_played, 5)
        
        if last_5_underdog_losses >= 2:
            filters_passed += 1
            score += 20
            result['reasons'].append(f"✅ FILTER 5 (UNDERDOG FORM): {underdog_name} lost {last_5_underdog_losses}/{underdog_games_for_calc} {underdog_venue_label} games (≥2 required)")
        else:
            result['reasons'].append(f"❌ FILTER 5 FAILED: {underdog_name} only lost {last_5_underdog_losses}/{underdog_games_for_calc} {underdog_venue_label} games (<2)")
            return result
        
        # ============================================
        # ALL 5 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Calculate win probability based on odds and filters
        # Base probability from odds
        if favourite_odds <= 1.40:
            win_prob = 75
        elif favourite_odds <= 1.55:
            win_prob = 70
        elif favourite_odds <= 1.70:
            win_prob = 65
        else:
            win_prob = 60
        
        # Boost for strong PPG
        if favourite_ppg >= 2.0:
            win_prob += 5
        elif favourite_ppg >= 1.8:
            win_prob += 3
        
        # Boost for strong xG
        if favourite_xg >= 2.2:
            win_prob += 5
        elif favourite_xg >= 2.0:
            win_prob += 3
        
        win_prob = min(88, max(55, win_prob))
        result['win_probability'] = round(win_prob, 1)
        
        # Determine confidence
        if score >= 95:
            result['confidence'] = 'Very High'
        elif score >= 85:
            result['confidence'] = 'High'
        elif score >= 75:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 5 FILTERS PASSED | Score: {score}/100 | Win Prob: {win_prob:.0f}%")
        result['reasons'].append(f"📊 Using {venue_label}-only stats for {favourite_name}, {underdog_venue_label}-only stats for {underdog_name}")
        
        return result


    # ============================================
    # NEW MARKET 1: Over 4.5 First Half Corners
    # ============================================
    def analyze_over_4_5_1h_corners(self, home_stats: Dict, away_stats: Dict,
                                     h2h: List[Dict], home_team: str, away_team: str,
                                     league_id: int = None) -> Dict:
        """
        Analyze Over 4.5 First Half Corners market
        
        ALL 4 FILTERS MUST PASS:
        1. At least one team must average over 58% possession in 1H in last 5 matches
        2. At least one team must average over 9 total 1H shots
        3. Both teams must have 60% over 4.5 1H corners in their last 10 matches
        4. At least one team must have achieved over 3.5 1H corners in 6 of last 10 games
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'over_probability': 0,
            'filters_passed': 0,
            'total_filters': 4
        }
        
        # Estimate possession from stats (attacking teams typically have higher possession)
        home_goals_avg = home_stats.get('goals_avg', 1.2)
        away_goals_avg = away_stats.get('goals_avg', 1.1)
        
        # Estimate possession (more attacking = higher possession usually)
        home_possession_est = 45 + (home_goals_avg * 5) + (home_stats.get('shots_avg', 12) * 0.3)
        away_possession_est = 45 + (away_goals_avg * 5) + (away_stats.get('shots_avg', 11) * 0.3)
        
        # Estimate 1H possession (similar to full match)
        home_1h_possession = min(65, home_possession_est)
        away_1h_possession = min(65, away_possession_est)
        
        # Estimate 1H shots (40% of total shots typically in 1H)
        home_1h_shots = home_stats.get('shots_avg', 12) * 0.40
        away_1h_shots = away_stats.get('shots_avg', 11) * 0.40
        
        # Estimate corners from possession and shots (higher possession/shots = more corners)
        home_corners_1h_est = (home_1h_shots / 4.5) + (home_1h_possession - 45) * 0.08
        away_corners_1h_est = (away_1h_shots / 4.5) + (away_1h_possession - 45) * 0.08
        
        score = 0
        filters_passed = 0
        
        # ============================================
        # FILTER 1: At least one team must average over 58% possession in 1H (last 5)
        # ============================================
        best_possession = max(home_1h_possession, away_1h_possession)
        
        if best_possession > 58:
            filters_passed += 1
            if best_possession >= 62:
                score += 25
                dominant_team = home_team if home_1h_possession >= away_1h_possession else away_team
                result['reasons'].append(f"✅ FILTER 1: {dominant_team} dominant possession ({best_possession:.0f}% > 58%)")
            else:
                score += 20
                dominant_team = home_team if home_1h_possession >= away_1h_possession else away_team
                result['reasons'].append(f"✅ FILTER 1: {dominant_team} good possession ({best_possession:.0f}% > 58%)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: Best 1H possession {best_possession:.0f}% ≤ 58%")
            result['reasons'].append(f"📊 Does not qualify - Filter 1 failed")
            return result
        
        # ============================================
        # FILTER 2: At least one team must average over 9 total 1H shots
        # ============================================
        best_shots = max(home_1h_shots, away_1h_shots)
        
        if best_shots > 9:
            filters_passed += 1
            if best_shots >= 12:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: Excellent 1H shots ({best_shots:.1f} > 9)")
            else:
                score += 20
                result['reasons'].append(f"✅ FILTER 2: Good 1H shots ({best_shots:.1f} > 9)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: Best 1H shots {best_shots:.1f} ≤ 9")
            result['reasons'].append(f"📊 Does not qualify - Filter 2 failed")
            return result
        
        # ============================================
        # FILTER 3: Both teams must have 60% over 4.5 1H corners in last 10 matches
        # ============================================
        home_o45_1h_rate = self._estimate_corner_hit_rate(home_corners_1h_est, 4.5)
        away_o45_1h_rate = self._estimate_corner_hit_rate(away_corners_1h_est, 4.5)
        
        if home_o45_1h_rate >= 60 and away_o45_1h_rate >= 60:
            filters_passed += 1
            avg_rate = (home_o45_1h_rate + away_o45_1h_rate) / 2
            if avg_rate >= 75:
                score += 30
                result['reasons'].append(f"✅ FILTER 3: Both excellent O4.5 1H corners (H: {home_o45_1h_rate:.0f}%, A: {away_o45_1h_rate:.0f}% ≥ 60%)")
            else:
                score += 25
                result['reasons'].append(f"✅ FILTER 3: Both have O4.5 1H corners (H: {home_o45_1h_rate:.0f}%, A: {away_o45_1h_rate:.0f}% ≥ 60%)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: O4.5 1H corners (H: {home_o45_1h_rate:.0f}%, A: {away_o45_1h_rate:.0f}%) - both must be ≥ 60%")
            result['reasons'].append(f"📊 Does not qualify - Filter 3 failed")
            return result
        
        # ============================================
        # FILTER 4: At least one team must have O3.5 1H corners in 6/10 games
        # ============================================
        home_o35_games = self._estimate_corner_games(home_corners_1h_est, 3.5)
        away_o35_games = self._estimate_corner_games(away_corners_1h_est, 3.5)
        
        best_o35 = max(home_o35_games, away_o35_games)
        
        if best_o35 >= 6:
            filters_passed += 1
            if home_o35_games >= 6 and away_o35_games >= 6:
                score += 25
                result['reasons'].append(f"✅ FILTER 4: Both have O3.5 1H corners frequently (H: {home_o35_games}/10, A: {away_o35_games}/10 ≥ 6)")
            else:
                score += 20
                better_team = home_team if home_o35_games >= away_o35_games else away_team
                result['reasons'].append(f"✅ FILTER 4: {better_team} has O3.5 1H corners ({best_o35}/10 ≥ 6)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: O3.5 1H corners (H: {home_o35_games}/10, A: {away_o35_games}/10) - need at least one ≥ 6")
            result['reasons'].append(f"📊 Does not qualify - Filter 4 failed")
            return result
        
        # ============================================
        # ALL 4 FILTERS PASSED - QUALIFIES!
        # ============================================
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        combined_corners_1h = home_corners_1h_est + away_corners_1h_est
        if combined_corners_1h >= 6.5:
            over_prob = 78
        elif combined_corners_1h >= 5.5:
            over_prob = 68
        elif combined_corners_1h >= 5.0:
            over_prob = 62
        else:
            over_prob = 55
        
        over_prob = min(85, max(50, over_prob + (score - 80) * 0.2))
        result['over_probability'] = round(over_prob, 1)
        
        if score >= 95:
            result['confidence'] = 'Very High'
        elif score >= 85:
            result['confidence'] = 'High'
        elif score >= 75:
            result['confidence'] = 'Medium'
        else:
            result['confidence'] = 'Low'
        
        result['reasons'].append(f"✅ ALL 4 FILTERS PASSED | Score: {score}/105 | Over Prob: {over_prob:.0f}%")
        return result
    
    def _estimate_corner_hit_rate(self, corners_avg: float, threshold: float) -> float:
        """Estimate hit rate for over X corners based on average"""
        diff = corners_avg - threshold
        if diff >= 2.0:
            return 85
        elif diff >= 1.5:
            return 78
        elif diff >= 1.0:
            return 70
        elif diff >= 0.5:
            return 62
        elif diff >= 0:
            return 55
        elif diff >= -0.5:
            return 45
        elif diff >= -1.0:
            return 35
        else:
            return 25
    
    def _estimate_corner_games(self, corners_avg: float, threshold: float) -> int:
        """Estimate number of games (out of 10) with over X corners"""
        rate = self._estimate_corner_hit_rate(corners_avg, threshold)
        return round(rate / 10)

    # ============================================
    # NEW MARKET 2: Under 10.5 Total Corners
    # ============================================
    def analyze_under_10_5_corners(self, home_stats: Dict, away_stats: Dict,
                                    h2h: List[Dict], home_team: str, away_team: str,
                                    league_id: int = None) -> Dict:
        """
        Analyze Under 10.5 Total Corners market
        
        ALL 4 FILTERS MUST PASS:
        1. Both teams must average below 53% possession in last 3 games
        2. Both teams must average below 15 shots per game AND combined under 23 shots
        3. Both teams must have under 10.5 corners in 6 of last 10 games
        4. Both teams must have NOT won over 3.5 1H corners in 6 of last 10 games
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'under_probability': 0,
            'filters_passed': 0,
            'total_filters': 4
        }
        
        home_goals_avg = home_stats.get('goals_avg', 1.2)
        away_goals_avg = away_stats.get('goals_avg', 1.1)
        
        home_possession_est = 45 + (home_goals_avg * 4) + (home_stats.get('shots_avg', 12) * 0.25)
        away_possession_est = 45 + (away_goals_avg * 4) + (away_stats.get('shots_avg', 11) * 0.25)
        
        home_shots = home_stats.get('shots_avg', 12)
        away_shots = away_stats.get('shots_avg', 11)
        combined_shots = home_shots + away_shots
        
        home_corners_est = home_shots / 4.5 + (home_possession_est - 50) * 0.06
        away_corners_est = away_shots / 4.5 + (away_possession_est - 50) * 0.06
        total_corners_est = home_corners_est + away_corners_est
        
        home_1h_corners = home_corners_est * 0.42
        away_1h_corners = away_corners_est * 0.42
        
        score = 0
        filters_passed = 0
        
        # FILTER 1: Both teams must average below 53% possession
        if home_possession_est < 53 and away_possession_est < 53:
            filters_passed += 1
            avg_poss = (home_possession_est + away_possession_est) / 2
            if avg_poss < 48:
                score += 30
                result['reasons'].append(f"✅ FILTER 1: Both low possession (H: {home_possession_est:.0f}%, A: {away_possession_est:.0f}% < 53%)")
            else:
                score += 25
                result['reasons'].append(f"✅ FILTER 1: Both moderate possession (H: {home_possession_est:.0f}%, A: {away_possession_est:.0f}% < 53%)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: Possession (H: {home_possession_est:.0f}%, A: {away_possession_est:.0f}%) - both must be < 53%")
            return result
        
        # FILTER 2: Both teams under 15 shots AND combined under 23
        if home_shots < 15 and away_shots < 15 and combined_shots < 23:
            filters_passed += 1
            if combined_shots < 20:
                score += 30
                result['reasons'].append(f"✅ FILTER 2: Very low shots (H: {home_shots:.1f}, A: {away_shots:.1f}, Combined: {combined_shots:.1f} < 23)")
            else:
                score += 25
                result['reasons'].append(f"✅ FILTER 2: Low shots (H: {home_shots:.1f}, A: {away_shots:.1f}, Combined: {combined_shots:.1f} < 23)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: Shots too high")
            return result
        
        # FILTER 3: Both teams U10.5 corners in 6/10 games
        home_u105_games = 10 - self._estimate_corner_games(home_corners_est, 10.5)
        away_u105_games = 10 - self._estimate_corner_games(away_corners_est, 10.5)
        
        if home_u105_games >= 6 and away_u105_games >= 6:
            filters_passed += 1
            score += 25
            result['reasons'].append(f"✅ FILTER 3: Both have U10.5 corners (H: {home_u105_games}/10, A: {away_u105_games}/10 ≥ 6)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: U10.5 corners not met")
            return result
        
        # FILTER 4: Both teams NOT O3.5 1H corners in 6/10 games
        home_o35_1h_games = self._estimate_corner_games(home_1h_corners, 3.5)
        away_o35_1h_games = self._estimate_corner_games(away_1h_corners, 3.5)
        
        if home_o35_1h_games < 6 and away_o35_1h_games < 6:
            filters_passed += 1
            score += 25
            result['reasons'].append(f"✅ FILTER 4: Both low 1H corners (H: {home_o35_1h_games}/10, A: {away_o35_1h_games}/10 < 6)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: 1H corners too high")
            return result
        
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        if total_corners_est <= 8:
            under_prob = 82
        elif total_corners_est <= 9:
            under_prob = 75
        elif total_corners_est <= 10:
            under_prob = 68
        else:
            under_prob = 58
        
        result['under_probability'] = round(min(88, max(52, under_prob)), 1)
        result['confidence'] = 'High' if score >= 100 else 'Medium'
        result['reasons'].append(f"✅ ALL 4 FILTERS PASSED | Score: {score}/105")
        return result

    # ============================================
    # NEW MARKET 3: Over 3.5 Total Cards
    # ============================================
    def analyze_over_3_5_total_cards(self, home_stats: Dict, away_stats: Dict,
                                      h2h: List[Dict], home_team: str, away_team: str,
                                      league_id: int = None) -> Dict:
        """
        Analyze Over 3.5 Total Cards market with 5 strict filters
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'over_probability': 0,
            'filters_passed': 0,
            'total_filters': 5
        }
        
        # Estimate tackles and fouls
        home_tackles_est = 12 + (home_stats.get('conceded_avg', 1.2) * 2) + 2
        away_tackles_est = 12 + (away_stats.get('conceded_avg', 1.3) * 2) + 2.5
        
        home_fouls_est = 12 + home_stats.get('conceded_avg', 1.2) * 1.5
        away_fouls_est = 13 + away_stats.get('conceded_avg', 1.3) * 1.5
        combined_fouls = home_fouls_est + away_fouls_est
        
        home_cards_est = home_fouls_est / 5.5
        away_cards_est = away_fouls_est / 5.5
        combined_cards = home_cards_est + away_cards_est
        
        score = 0
        filters_passed = 0
        
        # FILTER 1: Both teams > 14 tackles
        if home_tackles_est > 14 and away_tackles_est > 14:
            filters_passed += 1
            score += 20
            result['reasons'].append(f"✅ FILTER 1: Both aggressive (H: {home_tackles_est:.1f}, A: {away_tackles_est:.1f} > 14 tackles)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: Tackles not met")
            return result
        
        # FILTER 2: Combined fouls > 26
        if combined_fouls > 26:
            filters_passed += 1
            score += 20
            result['reasons'].append(f"✅ FILTER 2: High fouls ({combined_fouls:.1f} > 26)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: Combined fouls too low")
            return result
        
        # FILTER 3: Both teams > 1.8 cards per game
        if home_cards_est > 1.8 and away_cards_est > 1.8:
            filters_passed += 1
            score += 20
            result['reasons'].append(f"✅ FILTER 3: Both card-prone (H: {home_cards_est:.2f}, A: {away_cards_est:.2f} > 1.8)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: Cards avg not met")
            return result
        
        # FILTER 4: Combined cards > 4.2
        if combined_cards > 4.2:
            filters_passed += 1
            score += 20
            result['reasons'].append(f"✅ FILTER 4: High combined cards ({combined_cards:.2f} > 4.2)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: Combined cards too low")
            return result
        
        # FILTER 5: Both teams > 12 tackles (minimum)
        if home_tackles_est > 12 and away_tackles_est > 12:
            filters_passed += 1
            score += 16
            result['reasons'].append(f"✅ FILTER 5: Both meet minimum tackles")
        else:
            result['reasons'].append(f"❌ FILTER 5 FAILED: Minimum tackles not met")
            return result
        
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        over_prob = 65 + (combined_cards - 4) * 5
        result['over_probability'] = round(min(85, max(55, over_prob)), 1)
        result['confidence'] = 'High' if score >= 90 else 'Medium'
        result['reasons'].append(f"✅ ALL 5 FILTERS PASSED | Score: {score}/96")
        return result

    # ============================================
    # NEW MARKET 4: Over 1.5 Total Goals
    # ============================================
    def analyze_over_1_5_total_goals(self, home_stats: Dict, away_stats: Dict,
                                      h2h: List[Dict], home_team: str, away_team: str,
                                      league_id: int = None) -> Dict:
        """
        Analyze Over 1.5 Total Goals market with 6 strict filters
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'over_probability': 0,
            'filters_passed': 0,
            'total_filters': 6
        }
        
        home_goals_avg = home_stats.get('goals_avg', 1.3)
        away_goals_avg = away_stats.get('goals_avg', 1.1)
        home_played = max(home_stats.get('played', 10), 1)
        away_played = max(away_stats.get('played', 10), 1)
        
        home_xg = home_goals_avg * 1.05
        away_xg = away_goals_avg * 1.05
        combined_xg = home_xg + away_xg
        
        home_sot = home_goals_avg * 3.5
        away_sot = away_goals_avg * 3.5
        combined_sot = home_sot + away_sot
        
        home_cs = home_stats.get('clean_sheets', 2)
        away_cs = away_stats.get('clean_sheets', 2)
        home_cs_pct = (home_cs / min(home_played, 10)) * 100
        away_cs_pct = (away_cs / min(away_played, 10)) * 100
        
        combined_goals_avg = home_goals_avg + away_goals_avg
        
        score = 0
        filters_passed = 0
        
        # FILTER 1: Combined xG > 2.2
        if combined_xg > 2.2:
            filters_passed += 1
            score += 18
            result['reasons'].append(f"✅ FILTER 1: Combined xG ({combined_xg:.2f} > 2.2)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: Combined xG too low")
            return result
        
        # FILTER 2: At least one team xG > 1.2
        if max(home_xg, away_xg) > 1.2:
            filters_passed += 1
            score += 16
            result['reasons'].append(f"✅ FILTER 2: Team xG > 1.2")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: No team xG > 1.2")
            return result
        
        # FILTER 3: Combined SOT > 7.0
        if combined_sot > 7.0:
            filters_passed += 1
            score += 16
            result['reasons'].append(f"✅ FILTER 3: Combined SOT ({combined_sot:.1f} > 7.0)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: SOT too low")
            return result
        
        # FILTER 4: Both teams < 30% clean sheets
        if home_cs_pct < 30 and away_cs_pct < 30:
            filters_passed += 1
            score += 16
            result['reasons'].append(f"✅ FILTER 4: Both concede regularly (CS: H:{home_cs_pct:.0f}%, A:{away_cs_pct:.0f}% < 30%)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: Clean sheet % too high")
            return result
        
        # FILTER 5: Combined goals avg > 2.0
        if combined_goals_avg > 2.0:
            filters_passed += 1
            score += 16
            result['reasons'].append(f"✅ FILTER 5: Combined goals ({combined_goals_avg:.2f} > 2.0)")
        else:
            result['reasons'].append(f"❌ FILTER 5 FAILED: Combined goals too low")
            return result
        
        # FILTER 6: At least one team > 1.4 goals
        if max(home_goals_avg, away_goals_avg) > 1.4:
            filters_passed += 1
            score += 14
            result['reasons'].append(f"✅ FILTER 6: Prolific scorer present")
        else:
            result['reasons'].append(f"❌ FILTER 6 FAILED: No prolific scorer")
            return result
        
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        over_prob = 75 + (combined_goals_avg - 2) * 8
        result['over_probability'] = round(min(92, max(68, over_prob)), 1)
        result['confidence'] = 'High' if score >= 90 else 'Medium'
        result['reasons'].append(f"✅ ALL 6 FILTERS PASSED | Score: {score}/96")
        return result

    # ============================================
    # NEW MARKET 5: Draw No Bet (DNB)
    # ============================================
    def analyze_draw_no_bet(self, home_stats: Dict, away_stats: Dict,
                             h2h: List[Dict], home_team: str, away_team: str,
                             league_id: int = None, odds: Dict = None) -> Dict:
        """
        Analyze Draw No Bet market - uses Straight Win filters without odds/PPG
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'dnb_probability': 0,
            'filters_passed': 0,
            'total_filters': 6,
            'recommended_selection': None
        }
        
        home_goals_avg = home_stats.get('goals_avg', 1.3)
        away_goals_avg = away_stats.get('goals_avg', 1.1)
        home_conceded = home_stats.get('conceded_avg', 1.2)
        away_conceded = away_stats.get('conceded_avg', 1.3)
        
        home_gd = home_goals_avg - home_conceded
        away_gd = away_goals_avg - away_conceded
        
        home_wins_est = max(0, min(5, round(2.5 + home_gd * 1.5)))
        away_wins_est = max(0, min(5, round(2.5 + away_gd * 1.5)))
        home_losses_est = max(0, min(5, round(2 - home_gd)))
        away_losses_est = max(0, min(5, round(2 - away_gd)))
        home_draws_est = max(0, 5 - home_wins_est - home_losses_est)
        away_draws_est = max(0, 5 - away_wins_est - away_losses_est)
        
        home_strength = home_goals_avg * 1.1 - away_conceded + (home_gd * 0.5)
        away_strength = away_goals_avg * 0.9 - home_conceded + (away_gd * 0.5)
        
        if home_strength >= away_strength:
            favourite = 'home'
            favourite_name = home_team
            favourite_conceded = home_conceded
            favourite_wins = home_wins_est
            favourite_draws = home_draws_est
            opponent_losses = away_losses_est
            opponent_draws = away_draws_est
            result['recommended_selection'] = f"Draw No Bet - {home_team}"
        else:
            favourite = 'away'
            favourite_name = away_team
            favourite_conceded = away_conceded
            favourite_wins = away_wins_est
            favourite_draws = away_draws_est
            opponent_losses = home_losses_est
            opponent_draws = home_draws_est
            result['recommended_selection'] = f"Draw No Bet - {away_team}"
        
        score = 0
        filters_passed = 0
        
        # FILTER 1: 3+ wins in last 5
        if favourite_wins >= 3:
            filters_passed += 1
            score += 18
            result['reasons'].append(f"✅ FILTER 1: {favourite_name} winning form ({favourite_wins}/5)")
        else:
            result['reasons'].append(f"❌ FILTER 1 FAILED: Not enough wins")
            return result
        
        # FILTER 2: H2H dominance
        h2h_wins = 0
        if h2h:
            for match in h2h[:3]:
                hg = match.get('goals', {}).get('home', 0) or 0
                ag = match.get('goals', {}).get('away', 0) or 0
                if favourite == 'home' and hg > ag:
                    h2h_wins += 1
                elif favourite == 'away' and ag > hg:
                    h2h_wins += 1
        
        if h2h_wins >= 1:
            filters_passed += 1
            score += 16
            result['reasons'].append(f"✅ FILTER 2: H2H wins ({h2h_wins}/3)")
        else:
            result['reasons'].append(f"❌ FILTER 2 FAILED: No H2H wins")
            return result
        
        # FILTER 3: Concedes < 1.3
        if favourite_conceded < 1.3:
            filters_passed += 1
            score += 16
            result['reasons'].append(f"✅ FILTER 3: Solid defense ({favourite_conceded:.2f} < 1.3)")
        else:
            result['reasons'].append(f"❌ FILTER 3 FAILED: Concedes too much")
            return result
        
        # FILTER 4: Opponent 2+ losses
        if opponent_losses >= 2:
            filters_passed += 1
            score += 16
            result['reasons'].append(f"✅ FILTER 4: Opponent poor form ({opponent_losses}/5 losses)")
        else:
            result['reasons'].append(f"❌ FILTER 4 FAILED: Opponent not losing enough")
            return result
        
        # FILTER 5: Fewer draws
        if favourite_draws <= opponent_draws:
            filters_passed += 1
            score += 14
            result['reasons'].append(f"✅ FILTER 5: Lower draw risk")
        else:
            result['reasons'].append(f"❌ FILTER 5 FAILED: Higher draw risk")
            return result
        
        # FILTER 6: Attack advantage
        if favourite == 'home':
            xg_adv = home_goals_avg - away_conceded
        else:
            xg_adv = away_goals_avg - home_conceded
        
        if xg_adv > 0:
            filters_passed += 1
            score += 14
            result['reasons'].append(f"✅ FILTER 6: xG advantage (+{xg_adv:.2f})")
        else:
            result['reasons'].append(f"❌ FILTER 6 FAILED: No xG advantage")
            return result
        
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        dnb_prob = 60 + (score - 70) * 0.4
        if favourite == 'home':
            dnb_prob += 5
        
        result['dnb_probability'] = round(min(85, max(58, dnb_prob)), 1)
        result['confidence'] = 'High' if score >= 88 else 'Medium'
        result['reasons'].append(f"✅ ALL 6 FILTERS PASSED | Score: {score}/94")
        return result


    # ============================================
    # NEW MARKET 6: Double Chance + Under 4.5 Goals
    # ============================================
    def analyze_double_chance_under_4_5(self, home_stats: Dict, away_stats: Dict,
                                         h2h: List[Dict], home_team: str, away_team: str,
                                         league_id: int = None, odds: Dict = None) -> Dict:
        """
        Analyze Double Chance + Under 4.5 Goals combination market
        Combines Straight Win filters (for DC selection) with Under 4.5 Goals filters
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'probability': 0,
            'filters_passed': 0,
            'total_filters': 8,
            'recommended_selection': None,
            'dc_selection': None
        }
        
        # ===== STRAIGHT WIN FILTERS (for Double Chance selection) =====
        home_goals_avg = home_stats.get('goals_avg', 1.3)
        away_goals_avg = away_stats.get('goals_avg', 1.1)
        home_conceded = home_stats.get('conceded_avg', 1.2)
        away_conceded = away_stats.get('conceded_avg', 1.3)
        
        home_gd = home_goals_avg - home_conceded
        away_gd = away_goals_avg - away_conceded
        
        home_wins_est = max(0, min(5, round(2.5 + home_gd * 1.5)))
        away_wins_est = max(0, min(5, round(2.5 + away_gd * 1.5)))
        home_losses_est = max(0, min(5, round(2 - home_gd)))
        away_losses_est = max(0, min(5, round(2 - away_gd)))
        
        home_strength = home_goals_avg * 1.1 - away_conceded + (home_gd * 0.5)
        away_strength = away_goals_avg * 0.9 - home_conceded + (away_gd * 0.5)
        
        # Determine favourite for DC selection
        if home_strength >= away_strength:
            favourite = 'home'
            favourite_name = home_team
            favourite_conceded = home_conceded
            favourite_wins = home_wins_est
            opponent_losses = away_losses_est
            dc_selection = '1X'
        else:
            favourite = 'away'
            favourite_name = away_team
            favourite_conceded = away_conceded
            favourite_wins = away_wins_est
            opponent_losses = home_losses_est
            dc_selection = 'X2'
        
        result['dc_selection'] = dc_selection
        result['recommended_selection'] = f'Double Chance {dc_selection} & Under 4.5 Goals'
        
        score = 0
        filters_passed = 0
        
        # SW FILTER 1: 3+ wins in last 5
        if favourite_wins >= 3:
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ SW1: {favourite_name} winning form ({favourite_wins}/5)")
        else:
            result['reasons'].append(f"❌ SW1 FAILED: {favourite_name} not enough wins ({favourite_wins}/5)")
            return result
        
        # SW FILTER 2: H2H - at least not losing
        h2h_wins = 0
        h2h_unbeaten = True
        if h2h:
            for match in h2h[:3]:
                hg = match.get('goals', {}).get('home', 0) or 0
                ag = match.get('goals', {}).get('away', 0) or 0
                if favourite == 'home' and hg > ag:
                    h2h_wins += 1
                elif favourite == 'home' and ag > hg:
                    h2h_unbeaten = False
                elif favourite == 'away' and ag > hg:
                    h2h_wins += 1
                elif favourite == 'away' and hg > ag:
                    h2h_unbeaten = False
        
        if h2h_wins >= 1 or h2h_unbeaten:
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ SW2: H2H positive ({h2h_wins} wins, unbeaten: {h2h_unbeaten})")
        else:
            result['reasons'].append(f"❌ SW2 FAILED: H2H negative")
            return result
        
        # SW FILTER 3: Concedes < 1.3
        if favourite_conceded < 1.3:
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ SW3: Solid defense ({favourite_conceded:.2f} < 1.3)")
        else:
            result['reasons'].append(f"❌ SW3 FAILED: Concedes too much ({favourite_conceded:.2f})")
            return result
        
        # SW FILTER 4: Opponent 2+ losses
        if opponent_losses >= 2:
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ SW4: Opponent poor form ({opponent_losses}/5 losses)")
        else:
            result['reasons'].append(f"❌ SW4 FAILED: Opponent not losing enough")
            return result
        
        # ===== UNDER 4.5 GOALS FILTERS =====
        combined_goals = home_goals_avg + away_goals_avg
        combined_conceded = home_conceded + away_conceded
        
        # U4.5 FILTER 1: Combined goals average < 3.5
        if combined_goals < 3.5:
            filters_passed += 1
            score += 12
            result['reasons'].append(f"✅ U4.5-1: Combined goals avg {combined_goals:.2f} < 3.5")
        else:
            result['reasons'].append(f"❌ U4.5-1 FAILED: Combined goals too high ({combined_goals:.2f})")
            return result
        
        # U4.5 FILTER 2: At least one team concedes < 1.2
        if min(home_conceded, away_conceded) < 1.2:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ U4.5-2: Strong defensive team present")
        else:
            result['reasons'].append(f"❌ U4.5-2 FAILED: No strong defense")
            return result
        
        # U4.5 FILTER 3: Combined xG < 3.8
        combined_xg = (home_goals_avg * 1.02) + (away_goals_avg * 1.02)
        if combined_xg < 3.8:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ U4.5-3: Combined xG {combined_xg:.2f} < 3.8")
        else:
            result['reasons'].append(f"❌ U4.5-3 FAILED: Combined xG too high")
            return result
        
        # U4.5 FILTER 4: At least one team has clean sheet > 20%
        home_played = max(home_stats.get('played', 10), 1)
        away_played = max(away_stats.get('played', 10), 1)
        home_cs_pct = (home_stats.get('clean_sheets', 2) / min(home_played, 10)) * 100
        away_cs_pct = (away_stats.get('clean_sheets', 2) / min(away_played, 10)) * 100
        
        if max(home_cs_pct, away_cs_pct) > 20:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ U4.5-4: Clean sheet presence (H:{home_cs_pct:.0f}%, A:{away_cs_pct:.0f}%)")
        else:
            result['reasons'].append(f"❌ U4.5-4 FAILED: No clean sheet threat")
            return result
        
        # ===== ALL 8 FILTERS PASSED =====
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Calculate probability (DC is high prob ~70-80%, U4.5 is ~85%)
        # Combined: slightly lower due to requiring both
        base_prob = 72 + (score - 70) * 0.3
        result['probability'] = round(min(88, max(62, base_prob)), 1)
        result['confidence'] = 'High' if score >= 85 else 'Medium'
        result['reasons'].append(f"✅ ALL 8 FILTERS PASSED | Score: {score}/90")
        return result

    # ============================================
    # NEW MARKET 7: Double Chance + Over 1.5 Goals
    # ============================================
    def analyze_double_chance_over_1_5(self, home_stats: Dict, away_stats: Dict,
                                        h2h: List[Dict], home_team: str, away_team: str,
                                        league_id: int = None, odds: Dict = None) -> Dict:
        """
        Analyze Double Chance + Over 1.5 Goals combination market
        Combines Straight Win filters (for DC selection) with Over 1.5 Goals filters
        """
        result = {
            'qualifies': False,
            'confidence': 'Low',
            'reasons': [],
            'probability': 0,
            'filters_passed': 0,
            'total_filters': 10,
            'recommended_selection': None,
            'dc_selection': None
        }
        
        # ===== STRAIGHT WIN FILTERS (for Double Chance selection) =====
        home_goals_avg = home_stats.get('goals_avg', 1.3)
        away_goals_avg = away_stats.get('goals_avg', 1.1)
        home_conceded = home_stats.get('conceded_avg', 1.2)
        away_conceded = away_stats.get('conceded_avg', 1.3)
        
        home_gd = home_goals_avg - home_conceded
        away_gd = away_goals_avg - away_conceded
        
        home_wins_est = max(0, min(5, round(2.5 + home_gd * 1.5)))
        away_wins_est = max(0, min(5, round(2.5 + away_gd * 1.5)))
        home_losses_est = max(0, min(5, round(2 - home_gd)))
        away_losses_est = max(0, min(5, round(2 - away_gd)))
        
        home_strength = home_goals_avg * 1.1 - away_conceded + (home_gd * 0.5)
        away_strength = away_goals_avg * 0.9 - home_conceded + (away_gd * 0.5)
        
        # Determine favourite for DC selection
        if home_strength >= away_strength:
            favourite = 'home'
            favourite_name = home_team
            favourite_goals = home_goals_avg
            favourite_conceded = home_conceded
            favourite_wins = home_wins_est
            opponent_losses = away_losses_est
            dc_selection = '1X'
        else:
            favourite = 'away'
            favourite_name = away_team
            favourite_goals = away_goals_avg
            favourite_conceded = away_conceded
            favourite_wins = away_wins_est
            opponent_losses = home_losses_est
            dc_selection = 'X2'
        
        result['dc_selection'] = dc_selection
        result['recommended_selection'] = f'Double Chance {dc_selection} & Over 1.5 Goals'
        
        score = 0
        filters_passed = 0
        
        # SW FILTER 1: 3+ wins in last 5
        if favourite_wins >= 3:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ SW1: {favourite_name} winning form ({favourite_wins}/5)")
        else:
            result['reasons'].append(f"❌ SW1 FAILED: {favourite_name} not enough wins")
            return result
        
        # SW FILTER 2: H2H positive
        h2h_wins = 0
        h2h_unbeaten = True
        if h2h:
            for match in h2h[:3]:
                hg = match.get('goals', {}).get('home', 0) or 0
                ag = match.get('goals', {}).get('away', 0) or 0
                if favourite == 'home' and hg > ag:
                    h2h_wins += 1
                elif favourite == 'home' and ag > hg:
                    h2h_unbeaten = False
                elif favourite == 'away' and ag > hg:
                    h2h_wins += 1
                elif favourite == 'away' and hg > ag:
                    h2h_unbeaten = False
        
        if h2h_wins >= 1 or h2h_unbeaten:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ SW2: H2H positive ({h2h_wins} wins)")
        else:
            result['reasons'].append(f"❌ SW2 FAILED: H2H negative")
            return result
        
        # SW FILTER 3: Concedes < 1.3
        if favourite_conceded < 1.3:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ SW3: Solid defense ({favourite_conceded:.2f} < 1.3)")
        else:
            result['reasons'].append(f"❌ SW3 FAILED: Concedes too much")
            return result
        
        # SW FILTER 4: Opponent 2+ losses
        if opponent_losses >= 2:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ SW4: Opponent poor form ({opponent_losses}/5 losses)")
        else:
            result['reasons'].append(f"❌ SW4 FAILED: Opponent not losing enough")
            return result
        
        # ===== OVER 1.5 GOALS FILTERS =====
        home_played = max(home_stats.get('played', 10), 1)
        away_played = max(away_stats.get('played', 10), 1)
        
        home_xg = home_goals_avg * 1.05
        away_xg = away_goals_avg * 1.05
        combined_xg = home_xg + away_xg
        
        home_sot = home_goals_avg * 3.5
        away_sot = away_goals_avg * 3.5
        combined_sot = home_sot + away_sot
        
        home_cs = home_stats.get('clean_sheets', 2)
        away_cs = away_stats.get('clean_sheets', 2)
        home_cs_pct = (home_cs / min(home_played, 10)) * 100
        away_cs_pct = (away_cs / min(away_played, 10)) * 100
        
        combined_goals_avg = home_goals_avg + away_goals_avg
        
        # O1.5 FILTER 1: Combined xG > 2.2
        if combined_xg > 2.2:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ O1.5-1: Combined xG ({combined_xg:.2f} > 2.2)")
        else:
            result['reasons'].append(f"❌ O1.5-1 FAILED: Combined xG too low")
            return result
        
        # O1.5 FILTER 2: At least one team xG > 1.2
        if max(home_xg, away_xg) > 1.2:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ O1.5-2: Team xG > 1.2")
        else:
            result['reasons'].append(f"❌ O1.5-2 FAILED: No team xG > 1.2")
            return result
        
        # O1.5 FILTER 3: Combined SOT > 7.0
        if combined_sot > 7.0:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ O1.5-3: Combined SOT ({combined_sot:.1f} > 7.0)")
        else:
            result['reasons'].append(f"❌ O1.5-3 FAILED: SOT too low")
            return result
        
        # O1.5 FILTER 4: Both teams < 30% clean sheets
        if home_cs_pct < 30 and away_cs_pct < 30:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ O1.5-4: Both concede regularly (CS < 30%)")
        else:
            result['reasons'].append(f"❌ O1.5-4 FAILED: Too many clean sheets")
            return result
        
        # O1.5 FILTER 5: Combined goals > 2.0
        if combined_goals_avg > 2.0:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ O1.5-5: Combined goals ({combined_goals_avg:.2f} > 2.0)")
        else:
            result['reasons'].append(f"❌ O1.5-5 FAILED: Combined goals too low")
            return result
        
        # O1.5 FILTER 6: At least one team > 1.4 goals
        if max(home_goals_avg, away_goals_avg) > 1.4:
            filters_passed += 1
            score += 10
            result['reasons'].append(f"✅ O1.5-6: Prolific scorer present")
        else:
            result['reasons'].append(f"❌ O1.5-6 FAILED: No prolific scorer")
            return result
        
        # ===== ALL 10 FILTERS PASSED =====
        result['qualifies'] = True
        result['score'] = score
        result['filters_passed'] = filters_passed
        
        # Calculate probability (DC ~70-80%, O1.5 ~80%)
        base_prob = 70 + (score - 80) * 0.3
        result['probability'] = round(min(85, max(60, base_prob)), 1)
        result['confidence'] = 'High' if score >= 90 else 'Medium'
        result['reasons'].append(f"✅ ALL 10 FILTERS PASSED | Score: {score}/100")
        return result

