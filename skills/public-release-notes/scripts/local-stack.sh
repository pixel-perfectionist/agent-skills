#!/usr/bin/env bash
# Local copy of Decipher for Release Note screenshots.
#
#   local-stack.sh up   <worktree>   clone the dev DB, migrate it with the
#                                    worktree's code, prepare the synthetic
#                                    tenant, start backend :8002 + frontend :3300
#   local-stack.sh down <worktree>   stop both, drop the clone, delete the profile
#
# Needs: Homebrew postgresql@16 + redis running, the shared backend .venv and
# .env in ~/decipher/backend, and a local-operator env file at
# $RELEASE_NOTES_ENV (default ~/.config/decipher-release-notes/env.local) holding
# DEV_LOGIN_* for the LOCAL backend. Values are never printed.
set -euo pipefail

cmd="${1:?up|down}"
wt="$(cd "${2:?worktree path}" && pwd)"
repo="${DECIPHER_REPO:-$HOME/decipher}"
db="${RELEASE_NOTES_DB:-decipher_dev_rn}"
env_src="${RELEASE_NOTES_ENV:-$HOME/.config/decipher-release-notes/env.local}"
tenant_id="${RELEASE_NOTES_TENANT_ID:-3}"
operator="${RELEASE_NOTES_OPERATOR:-local-operator@decipher.test}"
run="$wt/.release-notes-stack"
db_url="postgres://$(whoami)@127.0.0.1:5432/$db"

stop() {
  for name in backend frontend; do
    if [ -f "$run/$name.pid" ]; then
      kill "$(cat "$run/$name.pid")" 2>/dev/null || true
      rm -f "$run/$name.pid"
    fi
  done
  # uv and npx run the real servers as children; free the ports either way.
  for port in 8002 3300; do
    lsof -ti "tcp:$port" -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null || true
  done
}

if [ "$cmd" = down ]; then
  stop
  dropdb -h 127.0.0.1 --if-exists "$db"
  rm -rf "$run"
  echo "stack down: servers stopped, $db dropped"
  exit 0
fi

[ -f "$env_src" ] || { echo "missing $env_src (local-operator env)" >&2; exit 1; }
mkdir -p "$run"

# Backend: the worktree's code on the shared venv and env.
ln -sfn "$repo/backend/.venv" "$wt/backend/.venv"
ln -sfn "$repo/backend/.env" "$wt/backend/.env"

# Frontend: a real install; Homebrew pnpm 12 rewrites the lockfile.
(cd "$wt/frontend" && CI=true npx -y pnpm@10.6.5 install --frozen-lockfile --prefer-offline >/dev/null)

# Production-like env: no feature flags, no analytics, local ports.
grep -vE '^(NEXT_PUBLIC_[A-Z_]*(OBLIGATION|CONFIGURATION_FROM|FLAG|PROTOTYPE|ENABLE)[A-Z_]*|OBLIGATION_[A-Z_]+|[A-Z_]*_PROTOTYPE_[A-Z_]*|[A-Z_]*_FIXTURES|NEXT_PUBLIC_EW_[A-Z_]+|VERCEL_OIDC_TOKEN|API_BASE_URL|NEXT_PUBLIC_WS_URL|NEXT_PUBLIC_BASE_URL|DEPLOY_ENVIRONMENT|E2E_[A-Z_]+)=' \
  "$env_src" > "$wt/frontend/.env.local"
printf 'API_BASE_URL=http://127.0.0.1:8002\nNEXT_PUBLIC_WS_URL=ws://127.0.0.1:8002\nNEXT_PUBLIC_BASE_URL=http://127.0.0.1:3300\n' >> "$wt/frontend/.env.local"
chmod 600 "$wt/frontend/.env.local"

# Database: a clone, never the shared DB.
dropdb -h 127.0.0.1 --if-exists "$db"
createdb -h 127.0.0.1 -T decipher_dev "$db"
(cd "$wt/backend" && DATABASE_URL="$db_url" uv run --no-sync python manage.py migrate --noinput >/dev/null)

# The synthetic tenant: the operator administers it, and it is open for work.
(cd "$wt/backend" && DATABASE_URL="$db_url" uv run --no-sync python manage.py shell -c "
from django.contrib.auth import get_user_model
from apps.accounts.models import Membership
from apps.companies.models import Company
u = get_user_model().objects.get(email='$operator')
src = Membership.objects.filter(user=u).first().groups.first()
G = type(src)
g, _ = G.objects.get_or_create(company_id=$tenant_id, code='rn_admin', defaults=dict(name='Administrators', description='', type=src.type))
g.permissions.set(src.permissions.all()); g.experiences.set(src.experiences.all())
m, _ = Membership.objects.get_or_create(user=u, company_id=$tenant_id, defaults=dict(is_active=True))
m.groups.add(g); m.active_group = g; m.is_active = True; m.save()
Company.objects.filter(id=$tenant_id).update(setup_status='ready')
print('clone prepared: operator administers tenant', $tenant_id)
" 2>/dev/null | tail -1)

# exec, so the recorded pid is the server itself and no wrapper shell keeps
# this script's output open.
(cd "$wt/backend" && DATABASE_URL="$db_url" exec uv run --no-sync python manage.py runserver 127.0.0.1:8002 --noreload) \
  < /dev/null > "$run/backend.log" 2>&1 &
echo $! > "$run/backend.pid"
(cd "$wt/frontend" && exec npx next dev -H 127.0.0.1 --port 3300) \
  < /dev/null > "$run/frontend.log" 2>&1 &
echo $! > "$run/frontend.pid"

for _ in $(seq 1 90); do
  b=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8002/api/v1/ || true)
  f=$(curl -s -o /dev/null -w '%{http_code}' --max-time 60 http://127.0.0.1:3300/ || true)
  if [ "$b" = 401 ] && [ "$f" = 200 ]; then
    echo "stack up: backend :8002, frontend :3300, db $db"
    exit 0
  fi
  sleep 2
done
echo "stack did not come up; see $run/*.log" >&2
stop
exit 1
