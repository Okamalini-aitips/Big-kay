"""Results tracking service for ROI and Hit Rate calculations"""
import logging
import uuid
import random
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from enum import Enum

from services import okamoney_engine as engine

logger = logging.getLogger(__name__)

PUBLIC_DAYS = 3  # users can view results up to 3 days back


class PickResult(str, Enum):
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    VOID = "void"
    HALF_WON = "half_won"
    HALF_LOST = "half_lost"


class ResultsTracker:
    """Track pick results and calculate statistics"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.pick_results
        
    async def record_result(self, pick_id: str, result: PickResult, 
                           pick_data: Dict = None) -> Dict:
        """
        Record the result of a pick
        
        Args:
            pick_id: Unique identifier for the pick
            result: The outcome (won/lost/void/etc.)
            pick_data: Optional full pick data to store
        """
        now = datetime.utcnow()
        
        # Check if result already exists
        existing = await self.collection.find_one({"pick_id": pick_id})
        
        if existing:
            # Update existing result
            update_data = {
                "result": result.value,
                "updated_at": now
            }
            await self.collection.update_one(
                {"pick_id": pick_id},
                {"$set": update_data}
            )
            logger.info(f"Updated result for pick {pick_id}: {result.value}")
        else:
            # Create new result record
            record = {
                "pick_id": pick_id,
                "result": result.value,
                "created_at": now,
                "updated_at": now,
                "settled_at": now if result != PickResult.PENDING else None
            }
            
            # Include pick data if provided
            if pick_data:
                record["pick_data"] = {
                    "match": pick_data.get("match", {}),
                    "market": pick_data.get("market", {}),
                    "confidence": pick_data.get("confidence"),
                    "probability": pick_data.get("probability"),
                    "stars": pick_data.get("stars"),
                    "analysis": pick_data.get("analysis")
                }
            
            await self.collection.insert_one(record)
            logger.info(f"Recorded new result for pick {pick_id}: {result.value}")
        
        return {"pick_id": pick_id, "result": result.value, "timestamp": now.isoformat()}
    
    async def get_pick_result(self, pick_id: str) -> Optional[Dict]:
        """Get the result for a specific pick"""
        result = await self.collection.find_one({"pick_id": pick_id})
        if result:
            result["_id"] = str(result["_id"])
        return result
    
    async def get_statistics(self, days: int = 30, market_type: str = None) -> Dict:
        """
        Calculate comprehensive statistics
        
        Args:
            days: Number of days to include (0 = all time)
            market_type: Filter by specific market type
        """
        # Build query
        query = {"result": {"$ne": PickResult.PENDING.value}}
        
        if days > 0:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query["created_at"] = {"$gte": cutoff}
        
        if market_type:
            query["pick_data.market.type"] = market_type
        
        # Get all settled results
        results = await self.collection.find(query).to_list(length=None)
        
        if not results:
            return self._empty_stats()
        
        # Calculate statistics
        total = len(results)
        won = len([r for r in results if r["result"] == PickResult.WON.value])
        lost = len([r for r in results if r["result"] == PickResult.LOST.value])
        void = len([r for r in results if r["result"] == PickResult.VOID.value])
        half_won = len([r for r in results if r["result"] == PickResult.HALF_WON.value])
        half_lost = len([r for r in results if r["result"] == PickResult.HALF_LOST.value])
        
        # Settled = non-void results
        settled = total - void
        
        # Hit rate calculation
        hit_rate = (won / settled * 100) if settled > 0 else 0
        
        # ROI calculation (assuming flat 1 unit stake)
        total_staked = settled  # 1 unit per pick
        total_returns = 0
        
        for r in results:
            if r["result"] == PickResult.WON.value:
                odds = r.get("pick_data", {}).get("market", {}).get("odds", 1.0)
                total_returns += odds
            elif r["result"] == PickResult.HALF_WON.value:
                odds = r.get("pick_data", {}).get("market", {}).get("odds", 1.0)
                total_returns += (1 + (odds - 1) / 2)  # Half win returns
            elif r["result"] == PickResult.HALF_LOST.value:
                total_returns += 0.5  # Half stake returned
            elif r["result"] == PickResult.VOID.value:
                pass  # Stake returned, not counted
            # Lost = 0 returns
        
        profit = total_returns - total_staked
        roi = (profit / total_staked * 100) if total_staked > 0 else 0
        
        # Calculate streaks
        streaks = self._calculate_streaks(results)
        
        # Calculate by confidence level
        by_confidence = await self._stats_by_confidence(query)
        
        # Calculate by market type
        by_market = await self._stats_by_market(days)
        
        return {
            "period_days": days if days > 0 else "all_time",
            "total_picks": total,
            "settled": settled,
            "won": won,
            "lost": lost,
            "void": void,
            "half_won": half_won,
            "half_lost": half_lost,
            "hit_rate": round(hit_rate, 1),
            "roi": round(roi, 1),
            "profit_units": round(profit, 2),
            "total_staked": total_staked,
            "total_returns": round(total_returns, 2),
            "current_streak": streaks["current"],
            "best_streak": streaks["best_win"],
            "worst_streak": streaks["worst_loss"],
            "by_confidence": by_confidence,
            "by_market": by_market,
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _empty_stats(self) -> Dict:
        """Return empty statistics structure"""
        return {
            "period_days": 0,
            "total_picks": 0,
            "settled": 0,
            "won": 0,
            "lost": 0,
            "void": 0,
            "half_won": 0,
            "half_lost": 0,
            "hit_rate": 0,
            "roi": 0,
            "profit_units": 0,
            "total_staked": 0,
            "total_returns": 0,
            "current_streak": {"type": "none", "count": 0},
            "best_streak": 0,
            "worst_streak": 0,
            "by_confidence": {},
            "by_market": {},
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def _calculate_streaks(self, results: List[Dict]) -> Dict:
        """Calculate win/loss streaks"""
        # Sort by settled_at or created_at
        sorted_results = sorted(
            results, 
            key=lambda x: x.get("settled_at") or x.get("created_at"),
            reverse=True
        )
        
        # Current streak
        current_type = None
        current_count = 0
        
        for r in sorted_results:
            result = r["result"]
            if result in [PickResult.VOID.value]:
                continue
            
            is_win = result in [PickResult.WON.value, PickResult.HALF_WON.value]
            
            if current_type is None:
                current_type = "win" if is_win else "loss"
                current_count = 1
            elif (is_win and current_type == "win") or (not is_win and current_type == "loss"):
                current_count += 1
            else:
                break
        
        # Best win streak and worst loss streak
        best_win = 0
        worst_loss = 0
        temp_win = 0
        temp_loss = 0
        
        for r in sorted_results:
            result = r["result"]
            if result in [PickResult.VOID.value]:
                continue
            
            is_win = result in [PickResult.WON.value, PickResult.HALF_WON.value]
            
            if is_win:
                temp_win += 1
                temp_loss = 0
                best_win = max(best_win, temp_win)
            else:
                temp_loss += 1
                temp_win = 0
                worst_loss = max(worst_loss, temp_loss)
        
        return {
            "current": {"type": current_type or "none", "count": current_count},
            "best_win": best_win,
            "worst_loss": worst_loss
        }
    
    async def _stats_by_confidence(self, base_query: Dict) -> Dict:
        """Calculate statistics grouped by confidence level"""
        pipeline = [
            {"$match": base_query},
            {"$group": {
                "_id": "$pick_data.confidence",
                "total": {"$sum": 1},
                "won": {"$sum": {"$cond": [{"$eq": ["$result", "won"]}, 1, 0]}},
                "lost": {"$sum": {"$cond": [{"$eq": ["$result", "lost"]}, 1, 0]}}
            }}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=None)
        
        stats = {}
        for r in results:
            confidence = r["_id"] or "Unknown"
            total = r["total"]
            won = r["won"]
            hit_rate = (won / total * 100) if total > 0 else 0
            stats[confidence] = {
                "total": total,
                "won": won,
                "lost": r["lost"],
                "hit_rate": round(hit_rate, 1)
            }
        
        return stats
    
    async def _stats_by_market(self, days: int) -> Dict:
        """Calculate statistics grouped by market type"""
        query = {"result": {"$ne": PickResult.PENDING.value}}
        
        if days > 0:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query["created_at"] = {"$gte": cutoff}
        
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": "$pick_data.market.type",
                "total": {"$sum": 1},
                "won": {"$sum": {"$cond": [{"$eq": ["$result", "won"]}, 1, 0]}},
                "lost": {"$sum": {"$cond": [{"$eq": ["$result", "lost"]}, 1, 0]}},
                "avg_odds": {"$avg": "$pick_data.market.odds"}
            }}
        ]
        
        results = await self.collection.aggregate(pipeline).to_list(length=None)
        
        stats = {}
        for r in results:
            market = r["_id"] or "Unknown"
            total = r["total"]
            won = r["won"]
            hit_rate = (won / total * 100) if total > 0 else 0
            
            # Calculate ROI for this market
            avg_odds = r.get("avg_odds", 1.5)
            expected_returns = won * avg_odds
            roi = ((expected_returns - total) / total * 100) if total > 0 else 0
            
            stats[market] = {
                "total": total,
                "won": won,
                "lost": r["lost"],
                "hit_rate": round(hit_rate, 1),
                "avg_odds": round(avg_odds, 2),
                "roi": round(roi, 1)
            }
        
        return stats
    
    async def get_history(self, limit: int = 50, offset: int = 0, 
                         result_filter: str = None) -> List[Dict]:
        """
        Get historical picks with results
        
        Args:
            limit: Maximum number of results
            offset: Pagination offset
            result_filter: Filter by result type (won/lost/void/pending)
        """
        query = {}
        
        if result_filter:
            query["result"] = result_filter
        
        cursor = self.collection.find(query)\
            .sort("created_at", -1)\
            .skip(offset)\
            .limit(limit)
        
        results = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for r in results:
            r["_id"] = str(r["_id"])
        
        return results
    
    async def get_pending_picks(self) -> List[Dict]:
        """Get all picks that are still pending"""
        query = {"result": PickResult.PENDING.value}
        results = await self.collection.find(query)\
            .sort("created_at", -1)\
            .to_list(length=100)
        
        for r in results:
            r["_id"] = str(r["_id"])
        
        return results
    
    async def bulk_record_results(self, results: List[Dict]) -> Dict:
        """
        Record multiple results at once
        
        Args:
            results: List of {"pick_id": str, "result": str, "pick_data": dict}
        """
        recorded = 0
        errors = []
        
        for item in results:
            try:
                result_enum = PickResult(item["result"])
                await self.record_result(
                    pick_id=item["pick_id"],
                    result=result_enum,
                    pick_data=item.get("pick_data")
                )
                recorded += 1
            except Exception as e:
                errors.append({"pick_id": item.get("pick_id"), "error": str(e)})
        
        return {
            "recorded": recorded,
            "errors": errors,
            "total": len(results)
        }

    # ========================================================================
    # DAILY SNAPSHOT + PUBLIC (3-DAY) VIEW  — added for real per-market tracking
    # ========================================================================
    async def ensure_snapshot(self, date_str: str, games_count: int = 30) -> None:
        """Idempotently store a date's engine tips (games + WhatsApp tickets) as PENDING picks.
        Deterministic: the engine pool is seeded by the date, so any past day can be rebuilt."""
        marker = await self.collection.find_one({"date": date_str})
        if marker:
            return
        try:
            pool = engine.generate_engine_games(60, seed=int(date_str.replace('-', '')))
        except Exception as e:
            logger.error(f"snapshot pool error {date_str}: {e}")
            return
        created = datetime.strptime(date_str, '%Y-%m-%d')
        docs = []

        for g in pool[:games_count]:
            for t in g['tips'][:2]:  # daily tips capped at 2 per game
                docs.append(self._snap_doc(date_str, created, 'games', None, g['home'],
                                           g['away'], g['league'], t))

        for name, res in [
            ('Build A Bet', engine.build_same_game_ticket(pool, 1.90, 3.40, (2, 3), set())),
            ('Mixed Parlay', engine.build_cross_game_ticket(pool, 3.50, 5.50, (3, 4), set())),
            ('Big Odds', engine.build_cross_game_ticket(pool, 8.00, 25.00, (5, 12), set())),
            ('Mega Odds', engine.build_cross_game_ticket(pool, 27.00, 50.00, (8, 15), set())),
        ]:
            if not res:
                continue
            if name == 'Build A Bet':
                game, tips, _ = res
                for t in tips:
                    docs.append(self._snap_doc(date_str, created, 'whatsapp', name,
                                               game['home'], game['away'], game['league'], t))
            else:
                sel, _ = res
                for item in sel:
                    gg, t = item['game'], item['tip']
                    docs.append(self._snap_doc(date_str, created, 'whatsapp', name,
                                               gg['home'], gg['away'], gg['league'], t))
        if docs:
            await self.collection.insert_many(docs)
            logger.info(f"📸 Snapshot {date_str}: {len(docs)} pending picks")

    def _snap_doc(self, date_str, created, surface, ticket_name, home, away, league, t):
        return {
            "pick_id": str(uuid.uuid4()),
            "result": PickResult.PENDING.value,
            "created_at": created,
            "updated_at": created,
            "settled_at": None,
            "date": date_str,
            "surface": surface,
            "ticket_name": ticket_name,
            "pick_data": {
                "match": {"home": home, "away": away, "league": league},
                "market": {"type": t['market'], "selection": t['selection'], "odds": t['odds']},
                "confidence": t['confidence'],
                "probability": t['probability'],
            },
        }

    async def get_public_recent(self, days: int = PUBLIC_DAYS) -> Dict:
        """PUBLIC: last N (<=3) completed days, grouped by game and WhatsApp ticket."""
        days = min(max(days, 1), PUBLIC_DAYS)
        out = []
        for i in range(1, days + 1):
            d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            await self.ensure_snapshot(d)
            out.append(await self._day_view(d))
        return {"days": out, "max_days": PUBLIC_DAYS}

    async def _day_view(self, date_str: str) -> Dict:
        picks = await self.collection.find({"date": date_str}, {"_id": 0}).to_list(length=None)
        games, whatsapp = {}, {}
        won = lost = pending = 0
        for p in picks:
            r = p["result"]
            if r == "won":
                won += 1
            elif r == "lost":
                lost += 1
            elif r == "pending":
                pending += 1
            pd = p.get("pick_data", {})
            m, mk = pd.get("match", {}), pd.get("market", {})
            tip = {"market": mk.get("type"), "selection": mk.get("selection"),
                   "odds": mk.get("odds"), "confidence": pd.get("confidence"),
                   "probability": pd.get("probability"), "result": r}
            if p.get("surface") == "games":
                key = f"{m.get('home')} vs {m.get('away')}"
                games.setdefault(key, {"home": m.get("home"), "away": m.get("away"),
                                       "league": m.get("league"), "tips": []})
                games[key]["tips"].append(tip)
            else:
                nm = p.get("ticket_name") or "Ticket"
                tip.update({"home": m.get("home"), "away": m.get("away"), "league": m.get("league")})
                whatsapp.setdefault(nm, {"name": nm, "legs": []})
                whatsapp[nm]["legs"].append(tip)
        settled = won + lost
        return {
            "date": date_str,
            "summary": {"won": won, "lost": lost, "pending": pending, "settled": settled,
                        "hit_rate": round(won / settled * 100, 1) if settled else None},
            "games": list(games.values()),
            "whatsapp": list(whatsapp.values()),
        }

    async def get_admin_stats(self, days: int = 30) -> Dict:
        """ADMIN: ensure the window is snapshotted, then return full statistics (incl. by_market)."""
        window = days if days and days > 0 else 30
        for i in range(1, window + 1):
            await self.ensure_snapshot((datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'))
        return await self.get_statistics(days=days)

    async def get_day_picks(self, date_str: str) -> List[Dict]:
        """ADMIN: flat list of a day's picks for settlement."""
        await self.ensure_snapshot(date_str)
        picks = await self.collection.find({"date": date_str}, {"_id": 0}).to_list(length=None)
        out = []
        for p in picks:
            pd = p.get("pick_data", {})
            m, mk = pd.get("match", {}), pd.get("market", {})
            out.append({"pick_id": p["pick_id"], "surface": p.get("surface"),
                        "ticket_name": p.get("ticket_name"),
                        "home": m.get("home"), "away": m.get("away"), "league": m.get("league"),
                        "market": mk.get("type"), "selection": mk.get("selection"),
                        "odds": mk.get("odds"), "result": p["result"]})
        return out

    async def settle(self, date_str: str, results: Dict[str, str], mode: str = 'manual') -> int:
        now = datetime.utcnow()
        n = 0
        for pick_id, res in results.items():
            if res not in ("won", "lost", "void"):
                continue
            r = await self.collection.update_one(
                {"pick_id": pick_id, "date": date_str},
                {"$set": {"result": res, "settlement_mode": mode, "settled_at": now, "updated_at": now}})
            n += r.modified_count
        return n

    async def simulate_settle(self, date_str: str) -> int:
        """DEMO ONLY: grade a date's pending picks by their probability (flagged 'simulated')."""
        await self.ensure_snapshot(date_str)
        picks = await self.collection.find(
            {"date": date_str, "result": PickResult.PENDING.value}).to_list(length=None)
        now = datetime.utcnow()
        n = 0
        for p in picks:
            prob = p.get("pick_data", {}).get("probability", 60)
            res = PickResult.WON.value if random.random() * 100 < prob else PickResult.LOST.value
            await self.collection.update_one({"_id": p["_id"]}, {"$set": {
                "result": res, "settlement_mode": "simulated", "settled_at": now, "updated_at": now}})
            n += 1
        return n


PUBLIC_DAYS_ALIAS = PUBLIC_DAYS
_results_tracker_singleton = None


def get_results_tracker(db=None):
    global _results_tracker_singleton
    if _results_tracker_singleton is None and db is not None:
        _results_tracker_singleton = ResultsTracker(db)
    return _results_tracker_singleton

