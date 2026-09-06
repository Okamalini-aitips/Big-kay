# OkaMoney AI Tips — Product Requirements

## Overview
Full-stack **web app** (pivoted from mobile to bypass app-store fees):
- **Frontend**: Vite + React (web-frontend/, port 3000)
- **Backend**: FastAPI (backend/server.py, port 8001, all routes prefixed `/api`)
- **DB**: MongoDB (motor async)
- Soccer betting tips app using combinatorial parlay/pick generation.

## Core Features
- JWT email/password auth (auth_service.py) gating premium daily picks.
- Coin wallet micro-transaction system (coin_wallet.py) — packages, purchase, spend, daily-free.
- WhatsApp premium subscription verification (whatsapp_subscription.py) + admin verify.
- History tracking (history_tracker.py).
- Admin daily ticket generators (whatsapp_tickets_generator.py): build-a-bet, mixed-parlay, big-odds, mega-odds.
- Core logic in stats_analyzer.py (~4.8k lines — DO NOT rewrite; migrate/preserve as-is).

## Status (as of this fork)
- App fully functional in this workspace. Backend healthy, Vite frontend serving.
- Full test pass: 34/34 backend endpoints, all frontend flows (auth, nav, admin pages).

## Known Blockers / Mocked
- **API-Sports live data is MOCKED** (account suspended). Awaiting user renewal to switch to live data.
- **Payfast** integration pending — needs live deployment URL to obtain keys.
- **Deployment**: user wants to deploy from this workspace via Emergent Publish/Deploy button.

## Fork Fixes Applied
- Vite blocked new preview host after fork → added `allowedHosts: true` in web-frontend/vite.config.js.

## Key Endpoints
Auth: /api/auth/register|login|me|check
Games/Picks: /api/games, /api/picks, /api/sgp, /api/mixed-parlay, /api/dc-under, /api/dc-over, /api/accumulators, /api/markets
Wallet: /api/wallet/balance|packages|purchase|spend|check-daily-free|use-daily-free|transactions
WhatsApp: /api/whatsapp/status|purchase|subscriptions, /api/admin/whatsapp/*
Admin tickets: /api/admin/whatsapp-tickets(+/build-a-bet,/mixed-parlay,/big-odds,/mega-odds)
Ticket Machine: /api/ticket-machine/options|generate

## DB Schema
- users: {email, password_hash, name, is_active, is_admin, created_at, updated_at}
- coin_wallets: {user_id, balance, expires_at, total_purchased, total_spent}
- coin_transactions: {user_id, type, amount, price, previous_balance, new_balance}
- whatsapp_subscriptions: {receipt_id, user_id, amount, status, verified, valid_until}

## Results Tracker (added)
- Real per-market performance tracking (services/results_tracker.py, `pick_results` collection).
- Deterministic daily snapshots (games top 30 + WhatsApp tickets) stored as 'pending'.
- Settlement: admin manual (POST /api/admin/results/settle), auto via API-Sports later, or admin DEMO simulate (POST /api/admin/results/simulate, flagged 'simulated').
- Public: GET /api/results/recent?days=3 (capped at 3 days) — used by the /games "Results" tab.
- Admin (key=ADMIN_SECRET_KEY): GET /api/admin/results/stats?days=7|14|30|0(all), /api/admin/results/pending — page at /admin/results.
- Tips now display ODDS (e.g. "@ 1.85") in the tip modal and results view; confidence % also shown.
- WhatsApp daily tickets are included in tracking.
