# Test Credentials for OkaMoney AI Tips

## Test User Account
- **Email**: test@example.com
- **Password**: testpassword123
- **Name**: Test User

## Admin Pages (No Auth Required Currently)
- `/admin/cards` - Admin cards page
- `/admin/verify` - WhatsApp receipt verification
- `/admin/whatsapp-tickets` - Daily tickets generator
- `/admin/results` - Results analytics + settlement (requires admin key)

## Admin Key (for results analytics & settlement)
- **ADMIN_SECRET_KEY**: `okamoney_admin_2024` (env `ADMIN_SECRET_KEY`, default)
- Used as `?key=okamoney_admin_2024` on `/api/admin/results/*` endpoints and the `/admin/results` page.

## Notes
- Users can also continue as "guest" without logging in
- Guest users use MOCK_USER_ID for wallet/subscriptions
- Logged-in users have their data stored in MongoDB
