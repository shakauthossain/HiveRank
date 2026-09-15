# HiveRank UI mock

Static HTML mock for the HiveRank redesign. Open in a browser — no build step.

## Files

| File | What |
|------|------|
| [index.html](./index.html) | Public landing — Full Audit / SEO / Speed + Sign in |
| [login.html](./login.html) | Sign-in + demo role shortcuts |
| [dashboard.html](./dashboard.html) | Logged-in shell: Audits · Snapshots · Bulk |
| [dashboard.html?role=admin#access](./dashboard.html?role=admin#access) | Superadmin Access (users + permissions) |
| [access.html](./access.html) | Shortcut → admin Access view |
| [styles.css](./styles.css) | Tokens from `BRAND.md` |

## How to view

```bash
# from repo root
xdg-open mock/hiverank/index.html
# or serve locally
npx --yes serve mock/hiverank -p 5179
```

## Demo path

1. Landing → pick mode → Analyze (goes to login in mock)  
2. Sign in → **Enter as operator** → Audits / Snapshots / Bulk  
3. Or **Enter as superadmin** → Access tab → edit permissions / add user  

Tokens: Outfit + Plus Jakarta Sans, Hive Blue `#1158E5`, paper canvas.
