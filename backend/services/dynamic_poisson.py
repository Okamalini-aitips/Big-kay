"""
Dynamic Poisson Enhancement System
Flexible, context-aware probability calculator for soccer betting
"""
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DynamicPoissonCalculator:
    """
    Enhanced Poisson calculator that adjusts expected goals based on
    match-specific dynamics rather than rigid averages.
    """
    
    def __init__(self):
        # Default league averages (fallback)
        self.default_home_goals = 1.5
        self.default_away_goals = 1.2
        
        # Adjustment weights (how much each factor influences xG)
        self.weights = {
            'form': 0.20,           # Recent form impact (20%)
            'h2h': 0.15,            # Head-to-head impact (15%)
            'home_away': 0.15,      # Home/away specific (15%)
            'fatigue': 0.10,        # Rest days impact (10%)
            'motivation': 0.10,     # Context/motivation (10%)
            'base': 0.30            # Base statistics (30%)
        }
    
    def poisson_probability(self, expected: float, actual: int) -> float:
        """Calculate Poisson probability for exact goal count"""
        if expected <= 0:
            expected = 0.1  # Avoid math errors
        return (math.exp(-expected) * (expected ** actual)) / math.factorial(actual)
    
    def calculate_form_factor(self, recent_matches: List[Dict], is_home: bool) -> float:
        """
        Calculate form adjustment based on last 5 matches.
        Returns multiplier (1.0 = neutral, >1 = good form, <1 = bad form)
        
        Weights: Most recent match = 5, oldest = 1
        """
        if not recent_matches or len(recent_matches) == 0:
            return 1.0
        
        form_score = 0
        total_weight = 0
        
        for i, match in enumerate(recent_matches[:5]):
            weight = 5 - i  # Most recent = 5, then 4, 3, 2, 1
            total_weight += weight
            
            goals_for = match.get('goals_for', 0)
            goals_against = match.get('goals_against', 0)
            result = match.get('result', 'D')  # W, D, L
            
            # Score based on result and goal difference
            if result == 'W':
                match_score = 1.0 + min((goals_for - goals_against) * 0.1, 0.3)
            elif result == 'D':
                match_score = 0.5
            else:  # Loss
                match_score = max(0.0, 0.2 - (goals_against - goals_for) * 0.05)
            
            form_score += match_score * weight
        
        # Normalize to 0-1 scale, then convert to multiplier (0.7 - 1.3 range)
        if total_weight > 0:
            normalized = form_score / total_weight
            # Convert to multiplier: 0.7 (terrible form) to 1.3 (excellent form)
            multiplier = 0.7 + (normalized * 0.6)
            return round(multiplier, 3)
        
        return 1.0
    
    def calculate_h2h_factor(self, h2h_matches: List[Dict], team_id: int) -> float:
        """
        Calculate head-to-head adjustment.
        Some teams have psychological edge over others.
        
        Returns multiplier based on historical performance vs this opponent
        """
        if not h2h_matches or len(h2h_matches) == 0:
            return 1.0
        
        wins = 0
        draws = 0
        losses = 0
        goals_for = 0
        goals_against = 0
        
        for match in h2h_matches[:5]:  # Last 5 H2H
            home_id = match.get('home_id')
            home_goals = match.get('home_goals', 0)
            away_goals = match.get('away_goals', 0)
            
            if home_id == team_id:
                goals_for += home_goals
                goals_against += away_goals
                if home_goals > away_goals:
                    wins += 1
                elif home_goals == away_goals:
                    draws += 1
                else:
                    losses += 1
            else:
                goals_for += away_goals
                goals_against += home_goals
                if away_goals > home_goals:
                    wins += 1
                elif away_goals == home_goals:
                    draws += 1
                else:
                    losses += 1
        
        total_matches = wins + draws + losses
        if total_matches == 0:
            return 1.0
        
        # Calculate H2H score
        win_rate = wins / total_matches
        goal_diff_avg = (goals_for - goals_against) / total_matches
        
        # Convert to multiplier (0.8 - 1.2 range)
        # Strong H2H record = boost, weak = reduce
        multiplier = 0.9 + (win_rate * 0.2) + (goal_diff_avg * 0.05)
        multiplier = max(0.8, min(1.2, multiplier))
        
        return round(multiplier, 3)
    
    def calculate_home_away_factor(self, team_stats: Dict, is_home: bool) -> float:
        """
        Adjust for home/away specific performance.
        Some teams are much stronger at home than away (or vice versa).
        """
        if not team_stats:
            return 1.0
        
        if is_home:
            home_goals_avg = team_stats.get('home_goals_avg', self.default_home_goals)
            overall_goals_avg = team_stats.get('goals_avg', self.default_home_goals)
            
            if overall_goals_avg > 0:
                ratio = home_goals_avg / overall_goals_avg
                # Cap the adjustment
                multiplier = max(0.85, min(1.25, ratio))
                return round(multiplier, 3)
        else:
            away_goals_avg = team_stats.get('away_goals_avg', self.default_away_goals)
            overall_goals_avg = team_stats.get('goals_avg', self.default_away_goals)
            
            if overall_goals_avg > 0:
                ratio = away_goals_avg / overall_goals_avg
                multiplier = max(0.75, min(1.15, ratio))
                return round(multiplier, 3)
        
        return 1.0
    
    def calculate_fatigue_factor(self, days_since_last_match: int) -> float:
        """
        Adjust for fixture congestion/rest.
        
        Optimal rest: 5-7 days = 1.0
        Too little rest: 2-3 days = 0.9
        Too much rest: 10+ days = 0.95 (rustiness)
        """
        if days_since_last_match is None:
            return 1.0
        
        if days_since_last_match <= 2:
            return 0.88  # Very fatigued
        elif days_since_last_match == 3:
            return 0.92
        elif days_since_last_match == 4:
            return 0.96
        elif days_since_last_match <= 7:
            return 1.0  # Optimal
        elif days_since_last_match <= 10:
            return 0.98  # Slight rust
        else:
            return 0.95  # Rusty from long break
    
    def calculate_motivation_factor(self, context: Dict) -> float:
        """
        Adjust for match context and motivation.
        
        Context includes:
        - League position
        - Relegation/title battle
        - Derby match
        - Cup final vs early round
        - End of season with nothing to play for
        """
        if not context:
            return 1.0
        
        multiplier = 1.0
        
        # Relegation battle (fighting for survival)
        if context.get('relegation_battle', False):
            multiplier *= 0.92  # More defensive, fewer goals typically
        
        # Title race (high stakes)
        if context.get('title_race', False):
            multiplier *= 1.05  # More attacking intent
        
        # Derby match (form goes out the window)
        if context.get('is_derby', False):
            multiplier *= 1.08  # Unpredictable, often more goals
        
        # Nothing to play for (mid-table, end of season)
        if context.get('nothing_to_play_for', False):
            multiplier *= 0.95  # Lower intensity
        
        # Cup match (often rotation/different approach)
        if context.get('is_cup', False):
            multiplier *= 0.97
        
        return round(max(0.8, min(1.2, multiplier)), 3)
    
    def calculate_adjusted_xg(
        self,
        base_xg: float,
        form_factor: float,
        h2h_factor: float,
        home_away_factor: float,
        fatigue_factor: float,
        motivation_factor: float
    ) -> float:
        """
        Calculate final adjusted expected goals using weighted factors.
        """
        # Weighted combination of all factors
        combined_multiplier = (
            (form_factor * self.weights['form']) +
            (h2h_factor * self.weights['h2h']) +
            (home_away_factor * self.weights['home_away']) +
            (fatigue_factor * self.weights['fatigue']) +
            (motivation_factor * self.weights['motivation']) +
            (1.0 * self.weights['base'])  # Base weight keeps some stability
        )
        
        adjusted_xg = base_xg * combined_multiplier
        return round(max(0.3, adjusted_xg), 2)  # Minimum 0.3 xG
    
    def calculate_match_probabilities(
        self,
        home_xg: float,
        away_xg: float,
        max_goals: int = 6
    ) -> Dict:
        """
        Calculate all match outcome probabilities using Poisson distribution.
        """
        # Calculate probability matrix for all scorelines
        score_probs = {}
        for home_goals in range(max_goals + 1):
            for away_goals in range(max_goals + 1):
                prob = (
                    self.poisson_probability(home_xg, home_goals) *
                    self.poisson_probability(away_xg, away_goals)
                )
                score_probs[(home_goals, away_goals)] = prob
        
        # Calculate outcome probabilities
        home_win_prob = sum(
            prob for (h, a), prob in score_probs.items() if h > a
        )
        draw_prob = sum(
            prob for (h, a), prob in score_probs.items() if h == a
        )
        away_win_prob = sum(
            prob for (h, a), prob in score_probs.items() if h < a
        )
        
        # Over/Under probabilities
        over_1_5_prob = sum(
            prob for (h, a), prob in score_probs.items() if (h + a) > 1.5
        )
        under_1_5_prob = 1 - over_1_5_prob
        
        over_2_5_prob = sum(
            prob for (h, a), prob in score_probs.items() if (h + a) > 2.5
        )
        under_2_5_prob = 1 - over_2_5_prob
        
        over_3_5_prob = sum(
            prob for (h, a), prob in score_probs.items() if (h + a) > 3.5
        )
        under_3_5_prob = 1 - over_3_5_prob
        
        over_4_5_prob = sum(
            prob for (h, a), prob in score_probs.items() if (h + a) > 4.5
        )
        under_4_5_prob = 1 - over_4_5_prob
        
        # BTTS (Both Teams To Score)
        btts_yes_prob = sum(
            prob for (h, a), prob in score_probs.items() if h > 0 and a > 0
        )
        btts_no_prob = 1 - btts_yes_prob
        
        # Double Chance
        dc_1x_prob = home_win_prob + draw_prob  # Home or Draw
        dc_x2_prob = draw_prob + away_win_prob  # Draw or Away
        dc_12_prob = home_win_prob + away_win_prob  # Home or Away (no draw)
        
        # Combined markets (DC + Under)
        dc_1x_under_4_5_prob = sum(
            prob for (h, a), prob in score_probs.items() 
            if (h >= a) and (h + a) <= 4
        )
        dc_x2_under_4_5_prob = sum(
            prob for (h, a), prob in score_probs.items() 
            if (a >= h) and (h + a) <= 4
        )
        
        # Most likely scorelines
        sorted_scores = sorted(score_probs.items(), key=lambda x: -x[1])[:5]
        likely_scores = [
            {"score": f"{h}-{a}", "probability": round(prob * 100, 1)}
            for (h, a), prob in sorted_scores
        ]
        
        return {
            "expected_goals": {
                "home": home_xg,
                "away": away_xg,
                "total": round(home_xg + away_xg, 2)
            },
            "match_result": {
                "home_win": round(home_win_prob * 100, 1),
                "draw": round(draw_prob * 100, 1),
                "away_win": round(away_win_prob * 100, 1)
            },
            "double_chance": {
                "1X": round(dc_1x_prob * 100, 1),
                "X2": round(dc_x2_prob * 100, 1),
                "12": round(dc_12_prob * 100, 1)
            },
            "over_under": {
                "over_1_5": round(over_1_5_prob * 100, 1),
                "under_1_5": round(under_1_5_prob * 100, 1),
                "over_2_5": round(over_2_5_prob * 100, 1),
                "under_2_5": round(under_2_5_prob * 100, 1),
                "over_3_5": round(over_3_5_prob * 100, 1),
                "under_3_5": round(under_3_5_prob * 100, 1),
                "over_4_5": round(over_4_5_prob * 100, 1),
                "under_4_5": round(under_4_5_prob * 100, 1)
            },
            "btts": {
                "yes": round(btts_yes_prob * 100, 1),
                "no": round(btts_no_prob * 100, 1)
            },
            "combined_markets": {
                "1X_under_4_5": round(dc_1x_under_4_5_prob * 100, 1),
                "X2_under_4_5": round(dc_x2_under_4_5_prob * 100, 1)
            },
            "likely_scores": likely_scores
        }
    
    def calculate_value_rating(
        self,
        calculated_prob: float,
        bookmaker_odds: float
    ) -> Dict:
        """
        Calculate if a bet has value by comparing our probability to bookmaker odds.
        
        Value = (Calculated Probability * Odds) - 1
        Value > 0 means the bet has positive expected value
        """
        if bookmaker_odds <= 1:
            return {"value": 0, "edge": 0, "rating": "No Value"}
        
        # Implied probability from bookmaker odds
        implied_prob = 1 / bookmaker_odds
        
        # Our calculated probability (as decimal)
        our_prob = calculated_prob / 100
        
        # Expected value
        ev = (our_prob * bookmaker_odds) - 1
        
        # Edge (how much better our probability is)
        edge = our_prob - implied_prob
        
        # Value rating
        if ev > 0.15:
            rating = "Excellent Value"
            stars = 5
        elif ev > 0.10:
            rating = "Great Value"
            stars = 4
        elif ev > 0.05:
            rating = "Good Value"
            stars = 3
        elif ev > 0:
            rating = "Slight Value"
            stars = 2
        else:
            rating = "No Value"
            stars = 1
        
        return {
            "expected_value": round(ev * 100, 1),  # As percentage
            "edge": round(edge * 100, 1),  # As percentage
            "implied_prob": round(implied_prob * 100, 1),
            "our_prob": round(our_prob * 100, 1),
            "rating": rating,
            "stars": stars
        }
    
    def analyze_match(
        self,
        home_team: Dict,
        away_team: Dict,
        h2h_data: List[Dict],
        match_context: Dict,
        bookmaker_odds: Dict
    ) -> Dict:
        """
        Complete match analysis using Dynamic Poisson.
        
        Returns comprehensive analysis with probabilities and value ratings.
        """
        logger.info(f"Analyzing: {home_team.get('name')} vs {away_team.get('name')}")
        
        # Extract base expected goals from team statistics
        home_base_xg = home_team.get('goals_avg', self.default_home_goals)
        away_base_xg = away_team.get('goals_avg', self.default_away_goals)
        
        # Also consider opponent's defensive record
        home_attack = home_team.get('goals_avg', 1.5)
        away_defense = away_team.get('goals_conceded_avg', 1.3)
        away_attack = away_team.get('goals_avg', 1.2)
        home_defense = home_team.get('goals_conceded_avg', 1.2)
        
        # Adjusted base xG considering both attack and defense
        home_base_xg = (home_attack + away_defense) / 2
        away_base_xg = (away_attack + home_defense) / 2
        
        # Calculate all dynamic factors for HOME team
        home_form = self.calculate_form_factor(
            home_team.get('recent_matches', []), is_home=True
        )
        home_h2h = self.calculate_h2h_factor(h2h_data, home_team.get('id'))
        home_venue = self.calculate_home_away_factor(home_team, is_home=True)
        home_fatigue = self.calculate_fatigue_factor(
            home_team.get('days_since_last_match')
        )
        home_motivation = self.calculate_motivation_factor(
            match_context.get('home_context', {})
        )
        
        # Calculate all dynamic factors for AWAY team
        away_form = self.calculate_form_factor(
            away_team.get('recent_matches', []), is_home=False
        )
        away_h2h = self.calculate_h2h_factor(h2h_data, away_team.get('id'))
        away_venue = self.calculate_home_away_factor(away_team, is_home=False)
        away_fatigue = self.calculate_fatigue_factor(
            away_team.get('days_since_last_match')
        )
        away_motivation = self.calculate_motivation_factor(
            match_context.get('away_context', {})
        )
        
        # Calculate adjusted expected goals
        home_adjusted_xg = self.calculate_adjusted_xg(
            home_base_xg, home_form, home_h2h, home_venue, 
            home_fatigue, home_motivation
        )
        away_adjusted_xg = self.calculate_adjusted_xg(
            away_base_xg, away_form, away_h2h, away_venue,
            away_fatigue, away_motivation
        )
        
        # Calculate match probabilities
        probabilities = self.calculate_match_probabilities(
            home_adjusted_xg, away_adjusted_xg
        )
        
        # Calculate value ratings for available odds
        value_ratings = {}
        
        # DC 1X + Under 4.5 (our bread and butter market)
        if 'dc_1x_u45' in bookmaker_odds:
            dc_1x_u45_prob = probabilities['combined_markets']['1X_under_4_5']
            value_ratings['dc_1x_u45'] = self.calculate_value_rating(
                dc_1x_u45_prob, bookmaker_odds['dc_1x_u45']
            )
        
        # DC X2 + Under 4.5
        if 'dc_x2_u45' in bookmaker_odds:
            dc_x2_u45_prob = probabilities['combined_markets']['X2_under_4_5']
            value_ratings['dc_x2_u45'] = self.calculate_value_rating(
                dc_x2_u45_prob, bookmaker_odds['dc_x2_u45']
            )
        
        # Over/Under 2.5
        if 'over_2_5' in bookmaker_odds:
            value_ratings['over_2_5'] = self.calculate_value_rating(
                probabilities['over_under']['over_2_5'], bookmaker_odds['over_2_5']
            )
        if 'under_2_5' in bookmaker_odds:
            value_ratings['under_2_5'] = self.calculate_value_rating(
                probabilities['over_under']['under_2_5'], bookmaker_odds['under_2_5']
            )
        
        # Match result
        if 'home_win' in bookmaker_odds:
            value_ratings['home_win'] = self.calculate_value_rating(
                probabilities['match_result']['home_win'], bookmaker_odds['home_win']
            )
        if 'draw' in bookmaker_odds:
            value_ratings['draw'] = self.calculate_value_rating(
                probabilities['match_result']['draw'], bookmaker_odds['draw']
            )
        if 'away_win' in bookmaker_odds:
            value_ratings['away_win'] = self.calculate_value_rating(
                probabilities['match_result']['away_win'], bookmaker_odds['away_win']
            )
        
        # Build analysis breakdown
        analysis_breakdown = {
            "home_team": {
                "base_xg": round(home_base_xg, 2),
                "adjusted_xg": home_adjusted_xg,
                "factors": {
                    "form": {"value": home_form, "impact": "positive" if home_form > 1 else "negative" if home_form < 1 else "neutral"},
                    "h2h": {"value": home_h2h, "impact": "positive" if home_h2h > 1 else "negative" if home_h2h < 1 else "neutral"},
                    "venue": {"value": home_venue, "impact": "positive" if home_venue > 1 else "negative" if home_venue < 1 else "neutral"},
                    "fatigue": {"value": home_fatigue, "impact": "positive" if home_fatigue >= 1 else "negative"},
                    "motivation": {"value": home_motivation, "impact": "positive" if home_motivation > 1 else "negative" if home_motivation < 1 else "neutral"}
                }
            },
            "away_team": {
                "base_xg": round(away_base_xg, 2),
                "adjusted_xg": away_adjusted_xg,
                "factors": {
                    "form": {"value": away_form, "impact": "positive" if away_form > 1 else "negative" if away_form < 1 else "neutral"},
                    "h2h": {"value": away_h2h, "impact": "positive" if away_h2h > 1 else "negative" if away_h2h < 1 else "neutral"},
                    "venue": {"value": away_venue, "impact": "positive" if away_venue > 1 else "negative" if away_venue < 1 else "neutral"},
                    "fatigue": {"value": away_fatigue, "impact": "positive" if away_fatigue >= 1 else "negative"},
                    "motivation": {"value": away_motivation, "impact": "positive" if away_motivation > 1 else "negative" if away_motivation < 1 else "neutral"}
                }
            }
        }
        
        return {
            "probabilities": probabilities,
            "value_ratings": value_ratings,
            "analysis_breakdown": analysis_breakdown,
            "recommendation": self._generate_recommendation(probabilities, value_ratings)
        }
    
    def _generate_recommendation(
        self,
        probabilities: Dict,
        value_ratings: Dict
    ) -> Dict:
        """
        Generate betting recommendation based on analysis.
        """
        best_value = None
        best_ev = -999
        
        for market, rating in value_ratings.items():
            if rating['expected_value'] > best_ev:
                best_ev = rating['expected_value']
                best_value = {
                    "market": market,
                    "rating": rating
                }
        
        # Determine confidence based on probability and value
        dc_1x_u45_prob = probabilities['combined_markets'].get('1X_under_4_5', 0)
        
        if dc_1x_u45_prob >= 75 and best_ev > 5:
            confidence = "Very High"
        elif dc_1x_u45_prob >= 65 and best_ev > 0:
            confidence = "High"
        elif dc_1x_u45_prob >= 55:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        return {
            "best_value_bet": best_value,
            "dc_1x_u45_probability": dc_1x_u45_prob,
            "confidence": confidence,
            "total_expected_goals": probabilities['expected_goals']['total']
        }


# Singleton instance
_poisson_calculator = None

def get_poisson_calculator() -> DynamicPoissonCalculator:
    """Get singleton instance of Dynamic Poisson Calculator"""
    global _poisson_calculator
    if _poisson_calculator is None:
        _poisson_calculator = DynamicPoissonCalculator()
    return _poisson_calculator
