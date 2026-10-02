#!/usr/bin/env python3
"""PreToolUse guard for the scheduled Decipher Release Notes routine.

Register it as a PreToolUse hook with matcher "*" in the Decipher checkout's
.claude/settings.local.json (see SKILL.md). It does nothing in ordinary
sessions. In a session started by the scheduled task "decipher-release-notes",
recognised by the <scheduled-task> tag the desktop app writes at the top of the
transcript, it denies these calls in every permission mode, bypass included:

  - merging, approving, closing or editing pull requests, and every other
    mutating GitHub call. Only read verbs and `gh pr create --head
    docs/release-notes-<slug>` are allowed;
  - pushing anything but a docs/release-notes-<slug> branch to origin, forced
    pushes, and branches whose diff against origin/main leaves the Release
    Notes paths;
  - git writes outside the routine's own worktree
    (.claude/worktrees/rn-<slug>; other sessions keep theirs there);
  - file writes outside that worktree and the session temp directory;
  - reading or printing secrets (.env files, the Keychain, gh or Vercel tokens);
  - network calls to anything but the local stack, MCP and web tools,
    questions to a user who is not there, and package installs;
  - database writes anywhere but the clone decipher_dev_rn.

It is a guard rail for an agent that reads untrusted PR text, not a sandbox:
text checks cannot see everything a process does. It fails closed inside the
routine and never touches other sessions.

Set RN_GUARD_FORCE=1 to apply the checks to any session (tests).
"""
import glob
import json
import os
import re
import shlex
import subprocess
import sys

HOME = os.path.expanduser('~')
REPO = os.path.realpath(os.environ.get('DECIPHER_REPO', os.path.join(HOME, 'decipher')))
WORKTREES = os.path.join(REPO, '.claude', 'worktrees')
WORKTREE_PREFIXES = ('rn-', 'release-notes-')  # other sessions keep their own worktrees beside these
SKILL_SCRIPTS = os.path.dirname(os.path.realpath(__file__))
TEMP_ROOTS = [os.path.realpath('/tmp/claude-%d' % os.getuid())]
if os.environ.get('TMPDIR'):
    TEMP_ROOTS.append(os.path.realpath(os.environ['TMPDIR']))
DEVICES = {'/dev/null', '/dev/stdout', '/dev/stderr', '/dev/tty'}

TASK_MARKER = '<scheduled-task name=\\"decipher-release-notes\\"'
BRANCH_RE = re.compile(r'^docs/release-notes-[a-z0-9][a-z0-9-]*$')
SCOPE = ('frontend/content/release-notes/', 'frontend/public/marketing/release-notes/')
CLONE_DB = 'decipher_dev_rn'
SECRET_PATH = re.compile(
    r'(^|/)\.env(?!\.example)($|[./])|(^|/)env\.local$|\.netrc$|(^|/)\.ssh(/|$)|\.pgpass$'
    r'|/Keychains(/|$)|(^|/)\.config/(gh|vercel)(/|$)|(^|/)\.vercel(/|$)|\.git-credentials$'
    r'|(^|/)\.aws(/|$)|(^|/)\.npmrc$'
)
WRITE_SQL = re.compile(
    r'\b(drop|delete|update|truncate|alter|insert|create|grant|revoke|copy|vacuum|reindex)\b', re.I
)

# Patterns checked against the whole command text, here-doc bodies and quoted
# strings included, and against the source of scripts the routine runs.
SEP = r'[\s\'",\[\]]+'
CRITICAL = [
    (r'\bgh' + SEP + r'(?:(?:-R|--repo)[\s=]\S+\s+)?pr' + SEP
     + r'(merge|review|close|reopen|ready|edit|comment|lock|unlock)\b',
     'pull requests are never merged, approved, closed or edited by the routine'),
    (r'--admin\b', 'admin overrides are not available to the routine'),
    (r'\b(mergePullRequest|enablePullRequestAutoMerge|addPullRequestReview|submitPullRequestReview'
     r'|closePullRequest|updatePullRequest|createRef|updateRef|deleteRef|updateRefs'
     r'|createCommitOnBranch)\b',
     'mutating GitHub GraphQL calls are not available to the routine'),
    (r'pulls/\d+/(merge|reviews|comments|requested_reviewers|update-branch)\b',
     'mutating pull request API calls are not available to the routine'),
    (r'\bgh' + SEP + r'auth' + SEP + r'(token|refresh|login|logout|switch|setup-git)\b',
     'GitHub credentials stay inside gh'),
    (r'\bsecurity' + SEP + r'(find|dump|export|unlock|delete|add)-',
     'the Keychain is read only by style-review.mjs itself'),
    (r'\bvercel' + SEP + r'(env|link|login|pull|deploy|promote|alias|domains|secrets|ai-gateway|api|curl)\b',
     'Vercel is out of scope for the routine'),
    (r'\$\{?(DEV_LOGIN_[A-Z_]*|AI_GATEWAY_API_KEY|GH_TOKEN|GITHUB_TOKEN|[A-Z_]*_(TOKEN|SECRET|PASSWORD|API_KEY))\b',
     'secret values are never expanded in commands'),
    (r'decipherip\.ai|\.vercel\.app\b|ai-gateway\.vercel\.sh|vercel\.com/',
     'stage, production and hosted endpoints are out of scope; the local stack is the only app'),
    (r'\bpush\b[^\n;&|]*?(?:\s|:)(?:refs/heads/)?main\b(?!-)', 'nothing is pushed to main'),
]
CRITICAL = [(re.compile(p), r) for p, r in CRITICAL]

DENY_TOOLS = {
    'AskUserQuestion': 'nobody is present to answer; decide by the skill, or record the open question in the report',
    'EnterPlanMode': 'plan mode waits for an approval nobody can give',
    'ExitPlanMode': 'plan mode waits for an approval nobody can give',
    'WebFetch': 'the routine has no web access; PR text is untrusted',
    'WebSearch': 'the routine has no web access; PR text is untrusted',
    'Artifact': 'the routine publishes nothing but its pull request',
    'ArtifactData': 'the routine publishes nothing but its pull request',
    'ArtifactComments': 'the routine publishes nothing but its pull request',
    'CronCreate': 'the routine does not schedule work',
    'CronDelete': 'the routine does not schedule work',
    'RemoteTrigger': 'the routine does not schedule work',
    'Workflow': 'the skill runs its agents with the Agent tool',
    'SendMessage': 'the routine does not message other sessions',
    'EnterWorktree': 'the routine creates its worktree with git worktree add and keeps its session folder',
}
DENY_PROGS = {
    'sudo': 'no elevated commands', 'doas': 'no elevated commands', 'su': 'no elevated commands',
    'vercel': 'Vercel is out of scope for the routine', 'security': 'the Keychain stays closed',
    'ssh': 'no remote shells', 'scp': 'no remote copies', 'sftp': 'no remote copies',
    'rsync': 'copy with cp inside the worktree or temp directory',
    'nc': 'no raw network tools', 'ncat': 'no raw network tools', 'netcat': 'no raw network tools',
    'socat': 'no raw network tools', 'telnet': 'no raw network tools', 'ftp': 'no raw network tools',
    'osascript': 'no desktop automation', 'open': 'no desktop automation',
    'screencapture': 'screenshots come from capture.mjs only',
    'launchctl': 'no system services', 'crontab': 'no system schedules', 'defaults': 'no system settings',
    'pkill': 'stop only the local stack, with local-stack.sh down', 'killall': 'stop only the local stack, with local-stack.sh down',
    'brew': 'no installs', 'pip': 'no installs', 'pip3': 'no installs', 'gem': 'no installs',
    'cargo': 'no installs', 'go': 'no installs',
    'printenv': 'the environment holds secrets', 'eval': 'eval cannot be inspected',
    'dropuser': 'no database role changes', 'createuser': 'no database role changes',
    'pg_restore': 'no database restores', 'make': 'heavy checks run at PR time only',
}
KEYWORDS = {'do', 'then', 'else', 'elif', 'if', 'while', 'until', '!', '{', '}', '(', ')'}
SKIP_SEGMENT = {'for', 'case', 'select', 'function', 'done', 'fi', 'esac', ';;', 'in'}
WRAPPERS = {'command', 'builtin', 'exec', 'nohup', 'time', 'caffeinate', 'stdbuf'}
SHELLS = {'bash', 'sh', 'zsh', 'dash', 'ksh'}
INTERPRETERS = {'python', 'python3', 'node', 'perl', 'ruby', 'deno', 'bun', 'php'}
SECRET_READERS = {
    'cat', 'head', 'tail', 'less', 'more', 'bat', 'grep', 'egrep', 'fgrep', 'rg', 'ag', 'sed', 'awk',
    'gawk', 'cut', 'sort', 'uniq', 'strings', 'xxd', 'od', 'hexdump', 'base64', 'cp', 'mv', 'ln',
    'curl', 'wget', 'jq', 'yq', 'nl', 'diff', 'cmp', 'comm', 'paste', 'python', 'python3', 'node',
    'perl', 'ruby', 'tee', 'pbcopy', 'zip', 'tar', 'gzip', 'column', 'fold', 'rev', 'tac', 'look',
}
ASSIGN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')


class Deny(Exception):
    pass


def deny(reason):
    raise Deny(reason)


# ---------------------------------------------------------------- detection

def is_routine(payload):
    if os.environ.get('RN_GUARD_FORCE') == '1':
        return True
    path = payload.get('transcript_path') or ''
    session = payload.get('session_id') or ''
    candidates = []
    if path:
        candidates.append(path)
        if '/subagents/' in path:
            candidates.append(path.split('/subagents/')[0] + '.jsonl')
        if session:
            candidates.append(os.path.join(os.path.dirname(path), session + '.jsonl'))
    for candidate in candidates:
        try:
            with open(candidate, 'r', encoding='utf-8', errors='replace') as f:
                for _ in range(12):
                    line = f.readline()
                    if not line:
                        break
                    if TASK_MARKER in line:
                        return True
        except OSError:
            pass
    return False


# ---------------------------------------------------------------- paths

def under(path, root):
    return path == root or path.startswith(root.rstrip('/') + '/')


def expand(token, env):
    def sub(m):
        name = m.group(1) or m.group(2)
        return env.get(name, m.group(0))
    token = re.sub(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)', sub, token)
    if token == '~' or token.startswith('~/'):
        token = HOME + token[1:]
    return token


def resolve(path, base):
    if not os.path.isabs(path):
        if base is None:
            return None
        path = os.path.join(base, path)
    return os.path.realpath(path)


def routine_worktree(real):
    """True for .claude/worktrees/rn-<slug> (or release-notes-<slug>) and paths inside it."""
    if real is None or not under(real, WORKTREES) or real == WORKTREES:
        return False
    return real[len(WORKTREES):].strip('/').split('/')[0].startswith(WORKTREE_PREFIXES)


def writable(real):
    if real in DEVICES:
        return True
    if any(under(real, root) for root in TEMP_ROOTS):
        return True
    if routine_worktree(real):
        inner = '/'.join(real[len(WORKTREES):].strip('/').split('/')[1:])
        if inner in ('.git',) or inner.startswith('.git/'):
            return False
        if inner.startswith(('.githooks/', '.github/', '.husky/', 'backend/.venv')) or inner == 'backend/.env':
            return False  # hooks run on commit; .venv and .env are links to the shared checkout
        if inner.startswith('.claude/') and inner != '.claude/.pre-pr-audit-state.json':
            return False
        return True
    return False


def check_write_target(target, cur, env):
    path = expand(target, env)
    if '$' in path or '`' in path:
        deny('write targets need literal paths, not %s' % target)
    globbed = re.search(r'[*?\[]', path)
    if globbed:
        path = os.path.dirname(path[:globbed.start()]) or '.'
    real = resolve(path, cur)
    if real is None:
        deny('relative write target %s after a cd the guard cannot follow; use an absolute path' % target)
    if not writable(real):
        deny('writes stay inside the routine worktree and its temp directory, not %s' % real)


def check_write_path(path, cwd):
    real = resolve(os.path.expanduser(path), cwd)
    if real is None or not writable(real):
        deny('files are written only inside .claude/worktrees/rn-<slug>/ and the session temp directory, not %s' % path)


# ---------------------------------------------------------------- shell text

def raw_scan(text):
    for pattern, reason in CRITICAL:
        if pattern.search(text):
            deny(reason)


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
SHELL_FEED = re.compile(r'\b(bash|sh|zsh|dash|ksh|source)\b[^|;&]*<<|<<[^\n]*\|\s*(bash|sh|zsh)\b')


def split_heredocs(cmd):
    """The command without here-doc bodies, and (opener line, body) pairs."""
    lines = cmd.split('\n')
    kept, bodies, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        kept.append(line)
        i += 1
        for m in HEREDOC.finditer(line):
            if line[max(0, m.start() - 1):m.start()] == '<':
                continue  # here-string
            body = []
            while i < len(lines) and lines[i].strip() != m.group(2):
                body.append(lines[i])
                i += 1
            i += 1
            bodies.append((line, '\n'.join(body)))
    return '\n'.join(kept), bodies


def read_quoted(s, i, closer):
    """Index just past the matching closer, honouring quotes and nesting."""
    depth, q, n = 1, None, len(s)
    while i < n:
        c = s[i]
        if q:
            if c == '\\' and q == '"':
                i += 2
                continue
            if c == q:
                q = None
        elif c == '\\':
            i += 2
            continue
        elif c in '"\'':
            q = c
        elif closer == ')' and c == '(':
            depth += 1
        elif c == closer:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def split_segments(s):
    """Simple commands, split on ; && || | & newlines and subshell parens."""
    segs, cur, q, i, n = [], [], None, 0, len(s)

    def flush():
        text = ''.join(cur).strip()
        if text:
            segs.append(text)
        del cur[:]

    while i < n:
        c = s[i]
        if q:
            cur.append(c)
            if c == '\\' and q == '"' and i + 1 < n:
                cur.append(s[i + 1])
                i += 2
                continue
            if c == q:
                q = None
            i += 1
            continue
        if c == '\\' and i + 1 < n:
            cur.append(s[i:i + 2])
            i += 2
            continue
        if c in '"\'':
            q = c
            cur.append(c)
            i += 1
            continue
        if c in '$<>' and i + 1 < n and s[i + 1] == '(':
            end = read_quoted(s, i + 2, ')')
            cur.append(s[i:end])
            i = end
            continue
        if c == '`':
            end = read_quoted(s, i + 1, '`')
            cur.append(s[i:end])
            i = end
            continue
        if s.startswith('&&', i) or s.startswith('||', i):
            flush()
            i += 2
            continue
        if c in ';\n|()':
            flush()
            i += 1
            continue
        if c == '&':
            prev = s[i - 1] if i else ''
            nxt = s[i + 1] if i + 1 < n else ''
            if prev in '<>' or nxt == '>':
                cur.append(c)
                i += 1
                continue
            flush()
            i += 1
            continue
        cur.append(c)
        i += 1
    flush()
    return segs


def substitutions(seg):
    """Bodies of $(...), <(...), >(...) and `...` inside one segment."""
    found, q, i, n = [], None, 0, len(seg)
    while i < n:
        c = seg[i]
        if q == "'":
            if c == "'":
                q = None
            i += 1
            continue
        if c == '\\':
            i += 2
            continue
        if c == "'" and q is None:
            q = "'"
            i += 1
            continue
        if c == '"':
            q = None if q == '"' else '"'
            i += 1
            continue
        if c in '$<>' and seg.startswith('(', i + 1):
            end = read_quoted(seg, i + 2, ')')
            found.append(seg[i + 2:end - 1])
            i = end
            continue
        if c == '`':
            end = read_quoted(seg, i + 1, '`')
            found.append(seg[i + 1:end - 1])
            i = end
            continue
        i += 1
    return found


def word_end(s, j):
    q, n = None, len(s)
    while j < n:
        c = s[j]
        if q:
            if c == q:
                q = None
        elif c in '"\'':
            q = c
        elif c.isspace() or c in ';&|<>()':
            break
        j += 1
    return j


def extract_redirects(seg):
    """The segment without redirections, and [(kind, target)] for each one."""
    out, reds, q, i, n = [], [], None, 0, len(seg)
    while i < n:
        c = seg[i]
        if q:
            out.append(c)
            if c == '\\' and q == '"' and i + 1 < n:
                out.append(seg[i + 1])
                i += 2
                continue
            if c == q:
                q = None
            i += 1
            continue
        if c == '\\' and i + 1 < n:
            out.append(seg[i:i + 2])
            i += 2
            continue
        if c in '"\'':
            q = c
            out.append(c)
            i += 1
            continue
        if c in '$<>' and i + 1 < n and seg[i + 1] == '(':
            end = read_quoted(seg, i + 2, ')')
            out.append(seg[i:end])
            i = end
            continue
        if c in '<>':
            if seg.startswith('<<', i):
                j = i + 2
                while j < n and seg[j] in '<-':
                    j += 1
                while j < n and seg[j] == ' ':
                    j += 1
                i = word_end(seg, j)
                continue
            # an fd number or & written right before the operator belongs to it
            k = len(out)
            while k and (out[k - 1].isdigit() or out[k - 1] == '&'):
                k -= 1
            if k == 0 or out[k - 1].isspace():
                del out[k:]
            kind = 'out' if c == '>' else 'in'
            j = i + 1
            if j < n and seg[j] in '>|':
                j += 1
            if j < n and seg[j] == '&':
                j += 1
                while j < n and seg[j] == ' ':
                    j += 1
                i = word_end(seg, j)
                continue  # fd duplication
            while j < n and seg[j] == ' ':
                j += 1
            end = word_end(seg, j)
            word = seg[j:end]
            try:
                word = ' '.join(shlex.split(word))
            except ValueError:
                pass
            reds.append((kind, word))
            i = end
            continue
        out.append(c)
        i += 1
    return ''.join(out), reds


def tokens(text):
    try:
        return shlex.split(text, posix=True)
    except ValueError:
        return text.split()


def positional(args, with_value=()):
    """Arguments that are not options, skipping the values of options that take one."""
    out, skip = [], False
    for a in args:
        if skip:
            skip = False
            continue
        if a == '--':
            continue
        if a.startswith('-') and a != '-':
            if a in with_value:
                skip = True
            continue
        out.append(a)
    return out


def option_value(args, names):
    for i, a in enumerate(args):
        for name in names:
            if a == name and i + 1 < len(args):
                return args[i + 1]
            if name.startswith('--') and a.startswith(name + '='):
                return a[len(name) + 1:]
    return None


# ---------------------------------------------------------------- command checks

def check_command(cmd, cwd, depth=0, env=None):
    if depth > 5:
        deny('command nesting too deep to inspect')
    raw_scan(cmd)
    env = dict(env or {'HOME': HOME, 'USER': os.environ.get('USER', '')})
    text, bodies = split_heredocs(cmd)
    cur = cwd
    for seg in split_segments(text):
        for inner in substitutions(seg):
            check_command(inner, cur, depth + 1, env)
        cur = check_segment(seg, cur, env, depth, cmd)
    for opener, body in bodies:
        if SHELL_FEED.search(opener):
            check_command(body, cwd, depth + 1, env)


def check_segment(seg, cur, env, depth, whole):
    text, reds = extract_redirects(seg)
    for kind, target in reds:
        if kind == 'out':
            check_write_target(target, cur, env)
        elif SECRET_PATH.search(expand(target, env)):
            deny('secrets stay unread (%s)' % target)
    return check_argv(tokens(text), cur, env, depth, whole)


def check_argv(argv, cur, env, depth, whole):
    argv = list(argv)
    while argv:
        head = argv[0]
        if head in KEYWORDS:
            argv.pop(0)
            continue
        if head in SKIP_SEGMENT:
            return cur
        if ASSIGN.match(head):
            assigns = []
            while argv and ASSIGN.match(argv[0]):
                assigns.append(argv.pop(0))
            if not argv:
                for a in assigns:
                    k, v = a.split('=', 1)
                    env[k] = expand(v, env)
                return cur
            continue
        prog = os.path.basename(head)
        if prog in WRAPPERS:
            argv = argv[1:]
            while argv and argv[0].startswith('-'):  # the wrapper's own options
                argv.pop(0)
            continue
        if prog in ('timeout', 'gtimeout'):
            rest = argv[1:]
            while rest and rest[0].startswith('-'):
                if rest[0] in ('-s', '-k', '--signal', '--kill-after'):
                    rest.pop(0)
                rest.pop(0)
            argv = rest[1:]  # drop the duration, keep the command verbatim
            continue
        if prog == 'env':
            rest = argv[1:]
            while rest and (rest[0].startswith('-') or ASSIGN.match(rest[0])):
                if rest[0] in ('-u', '--unset'):
                    rest.pop(0)
                rest.pop(0)
            if not rest:
                deny('env without a command prints the environment, which holds secrets')
            argv = rest
            continue
        break
    if not argv:
        return cur
    prog = os.path.basename(argv[0])
    args = argv[1:]

    if prog in DENY_PROGS:
        deny('%s: %s' % (prog, DENY_PROGS[prog]))
    if prog in ('cd', 'pushd'):
        if not args or args[0] == '~':
            return HOME
        target = expand(args[-1], env)
        if '$' in target or target == '-':
            return None
        return resolve(target, cur)
    if prog == 'popd':
        return None
    if prog in ('export', 'declare', 'typeset'):
        if not args or any(a in ('-p', '-x') for a in args):
            deny('%s would print the environment, which holds secrets' % prog)
        for a in args:
            if ASSIGN.match(a):
                k, v = a.split('=', 1)
                env[k] = expand(v, env)
        return cur
    if prog == 'set' and not args:
        deny('set without arguments prints the environment, which holds secrets')

    if prog in SECRET_READERS:
        for a in args:
            if SECRET_PATH.search(expand(a, env)):
                deny('secrets stay unread (%s)' % a)

    if prog == 'gh':
        check_gh(args)
    elif prog == 'git':
        check_git(args, cur, env)
    elif prog in ('curl', 'wget', 'http', 'https', 'xh'):
        check_http(prog, args, cur, env)
    elif prog in ('npx', 'bunx'):
        check_npx(args)
    elif prog in ('pnpm', 'npm', 'yarn'):
        check_package_manager(prog, args)
    elif prog == 'uv':
        check_uv(args, cur, env, depth, whole)
    elif prog in SHELLS or prog in ('source', '.'):
        check_shell(prog, args, cur, env, depth)
    elif prog in INTERPRETERS:
        check_interpreter(prog, args, cur, env, whole)
    elif prog == 'psql':
        if CLONE_DB not in whole and (WRITE_SQL.search(whole) or option_value(args, ('-f', '--file'))):
            deny('database writes go only to the clone %s' % CLONE_DB)
    elif prog in ('dropdb', 'createdb'):
        names = positional(args, ('-h', '-p', '-U', '-T', '-O', '-E', '-D', '-l', '--host', '--port',
                                  '--username', '--template', '--owner', '--encoding', '--tablespace',
                                  '--locale', '--maintenance-db'))
        if names[:1] != [CLONE_DB]:
            deny('%s works only on the clone %s' % (prog, CLONE_DB))
    elif prog == 'redis-cli':
        if positional(args, ('-h', '-p', '-n', '-a')) not in ([], ['ping']):
            deny('redis-cli is limited to ping')
    elif prog == 'kill':
        if any(a in ('-1', '0') for a in args):
            deny('kill only named processes of the local stack')
    elif prog == 'xargs':
        sub = positional(args, ('-I', '-i', '-n', '-P', '-L', '-d', '-E', '-s', '-J', '-R'))
        if sub and os.path.basename(sub[0]) == 'kill':
            if not re.search(r'tcp:(8002|3300)\b|\.release-notes-stack', whole):
                deny('kill only the local stack (ports 8002 and 3300)')
        elif sub:
            check_argv(sub, cur, env, depth, whole)
    elif prog == 'find':
        check_find(args, cur, env, depth, whole)
    elif prog == 'manage.py' or (args and args[0].endswith('manage.py') and prog in INTERPRETERS):
        check_manage(args, whole)

    for target in write_targets(prog, args):
        check_write_target(target, cur, env)
    return cur


def write_targets(prog, args):
    if prog in ('cp', 'mv', 'ln', 'install', 'ditto'):
        explicit = option_value(args, ('-t', '--target-directory'))
        if explicit:
            return [explicit]
        return positional(args, ('-m', '-o', '-g', '-S', '--suffix', '--mode'))[-1:]
    if prog in ('tee', 'touch', 'mkdir', 'rmdir', 'rm', 'unlink', 'shred', 'srm'):
        return positional(args, ('-m', '--mode'))
    if prog == 'truncate':
        return positional(args, ('-s', '--size', '-r', '--reference'))
    if prog in ('chmod', 'chown', 'chgrp', 'chflags'):
        return positional(args)[1:]
    if prog in ('sed', 'perl', 'ruby') and any(a.startswith('-i') or a == '--in-place' for a in args):
        if prog == 'sed' and '-i' in args:
            k = args.index('-i')
            args = args[:k + 1] + args[k + 2:]  # BSD sed: -i takes its backup suffix ('') as a separate argument
        files = [a for a in positional(args, ('-e', '--expression', '-f', '--file')) if a]
        has_script = any(a in ('-e', '--expression', '-f', '--file') for a in args)
        return files if has_script else files[1:]
    if prog == 'dd':
        return [a[3:] for a in args if a.startswith('of=')]
    if prog in ('tar', 'bsdtar') and args and 'x' in args[0].lstrip('-'):
        return [option_value(args, ('-C', '--directory')) or '.']
    if prog == 'unzip':
        return [option_value(args, ('-d',)) or '.']
    if prog == 'sips':
        out = option_value(args, ('--out', '-o'))
        if out:
            return [out]
        if all(a in ('-g', '--getProperty', '-1', '--oneLine') or not a.startswith('-') for a in args):
            return []
        return [a for a in positional(args) if re.search(r'\.(png|jpe?g|gif|webp|tiff?|heic)$', a, re.I)]
    if prog == 'patch':
        return positional(args, ('-p', '-d', '-i', '-o'))
    return []


def check_gh(args):
    clean, i = [], 0
    while i < len(args):
        a = args[i]
        if a in ('-R', '--repo'):
            if i + 1 < len(args) and args[i + 1] != 'DecipherIP/decipher':
                deny('gh works only on DecipherIP/decipher')
            i += 2
            continue
        if a.startswith('--repo='):
            if a != '--repo=DecipherIP/decipher':
                deny('gh works only on DecipherIP/decipher')
            i += 1
            continue
        clean.append(a)
        i += 1
    if not clean or clean[0] in ('--version', 'version', 'help', '--help', '-h') or '--help' in clean:
        return
    sub = clean[0]
    verb = clean[1] if len(clean) > 1 else ''
    read_verbs = {
        'auth': {'status'},
        'pr': {'list', 'view', 'diff', 'checks', 'status'},
        'issue': {'list', 'view', 'status'},
        'run': {'list', 'view'},
        'release': {'list', 'view'},
        'label': {'list'},
        'repo': {'view'},
        'workflow': {'list', 'view'},
        'project': {'list', 'view', 'item-list', 'field-list'},
        'ruleset': {'list', 'view', 'check'},
    }
    if sub == 'search' or verb in read_verbs.get(sub, ()):
        return
    if sub == 'pr' and verb == 'create':
        check_pr_create(clean[2:])
        return
    if sub == 'api':
        check_gh_api(clean[1:])
        return
    deny('gh %s %s is not available to the routine; it may read and open one pull request' % (sub, verb))


def check_gh_api(args):
    method = None
    for i, a in enumerate(args):
        if a in ('-X', '--method') and i + 1 < len(args):
            method = args[i + 1]
        elif a.startswith('--method='):
            method = a.split('=', 1)[1]
        elif a.startswith('-X') and len(a) > 2:
            method = a[2:]
        if a in ('-f', '-F', '--field', '--raw-field', '--input') or re.match(r'^(-[fF].|--(raw-)?field=|--input=)', a):
            deny('gh api with fields sends a write request; the routine only reads')
    if method and method.upper() != 'GET':
        deny('gh api %s is a write request; the routine only reads' % method)
    endpoint = positional(args, ('-H', '--header', '-q', '--jq', '-t', '--template', '--cache',
                                 '-p', '--preview', '--hostname', '-X', '--method'))
    if endpoint[:1] == ['graphql']:
        deny('gh api graphql is not available to the routine')


def check_pr_create(args):
    head = option_value(args, ('--head', '-H'))
    base = option_value(args, ('--base', '-B'))
    if not head:
        deny('gh pr create needs --head docs/release-notes-<slug>')
    if not BRANCH_RE.match(head):
        deny('pull requests come only from docs/release-notes-<slug> branches, not %s' % head)
    if base not in (None, 'main'):
        deny('pull requests target main only')
    if any(a in ('-w', '--web') for a in args):
        deny('no browser from the routine')
    rev = 'refs/heads/' + head
    if subprocess.run(['git', '-C', REPO, 'rev-parse', '--verify', '--quiet', rev],
                      capture_output=True, timeout=5).returncode != 0:
        rev = 'refs/remotes/origin/' + head
    check_scope(rev, REPO)


def check_scope(rev, where):
    r = subprocess.run(['git', '-C', where, 'diff', '--name-only', 'origin/main...' + rev],
                       capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        deny('cannot compare %s with origin/main; fetch origin and retry' % rev)
    outside = [f for f in r.stdout.splitlines() if f and not f.startswith(SCOPE)]
    if outside:
        deny('the branch changes files outside the Release Notes paths: %s' % ', '.join(outside[:5]))


GIT_READ = {
    'status', 'log', 'show', 'diff', 'ls-tree', 'ls-files', 'ls-remote', 'rev-parse', 'rev-list',
    'merge-base', 'cat-file', 'grep', 'blame', 'shortlog', 'describe', 'for-each-ref', 'show-ref',
    'name-rev', 'whatchanged', 'count-objects', 'check-ignore', 'check-attr', 'var', 'help',
    'version', 'cherry', 'range-diff', 'diff-tree', 'diff-index', 'diff-files', 'show-branch',
    'archive', 'fetch',
}
GIT_WORKTREE_WRITE = {
    'add', 'commit', 'rm', 'mv', 'restore', 'checkout', 'switch', 'reset', 'clean', 'stash',
    'rebase', 'merge', 'cherry-pick', 'revert', 'am', 'apply', 'notes', 'update-index',
    'sparse-checkout', 'mergetool', 'bisect', 'rerere',
}


def check_git(args, cur, env):
    a = list(args)
    repo_dir = cur
    while a and a[0].startswith('-'):
        t = a.pop(0)
        if t == '-C' and a:
            target = expand(a.pop(0), env)
            repo_dir = None if '$' in target else resolve(target, cur)
        elif t.startswith('-c') or t.startswith('--git-dir') or t.startswith('--work-tree') \
                or t.startswith('--exec-path') or t == '--config-env':
            deny('git %s overrides are not available to the routine' % t)
        elif t in ('--version', '--help'):
            return
    if not a:
        return
    sub, rest = a[0], a[1:]
    in_worktree = routine_worktree(repo_dir)

    if sub == 'fetch' and any(r.startswith('--upload-pack') for r in rest):
        deny('git fetch --upload-pack is not available')
    if sub in GIT_READ:
        return
    if sub == 'reflog' and (not rest or rest[0] in ('show', 'list')):
        return
    if sub == 'branch':
        writes = {'-d', '-D', '--delete', '-m', '-M', '--move', '-c', '-C', '--copy', '-f', '--force',
                  '-u', '--set-upstream-to', '--unset-upstream', '--edit-description'}
        if any(r in writes or r.startswith('--set-upstream-to=') for r in rest):
            deny('git branch changes are not available; work on docs/release-notes-<slug> in a worktree')
        names = positional(rest, ('--format', '--sort', '--contains', '--no-contains', '--merged',
                                  '--no-merged', '--points-at', '--color', '--column'))
        listing = any(r in ('--list', '-l', '-a', '--all', '-r', '--remotes', '--show-current', '-v', '-vv')
                      for r in rest)
        if names and not listing and not BRANCH_RE.match(names[0]):
            deny('new branches are named docs/release-notes-<slug>')
        return
    if sub == 'remote':
        if rest and rest[0] not in ('-v', '--verbose', 'show', 'get-url'):
            deny('git remote changes are not available')
        return
    if sub == 'config':
        if not any(r in ('--get', '--get-all', '--get-regexp', '--list', '-l', '--show-origin') for r in rest):
            deny('git config writes are not available')
        return
    if sub == 'stash' and rest[:1] in (['list'], ['show']):
        return
    if sub == 'worktree':
        verb = rest[0] if rest else 'list'
        if verb in ('list', 'prune'):
            return
        if verb == 'add':
            branch = option_value(rest[1:], ('-b', '-B'))
            if branch and not BRANCH_RE.match(branch):
                deny('worktree branches are named docs/release-notes-<slug>')
            paths = positional(rest[1:], ('-b', '-B', '--reason'))
        elif verb in ('remove', 'move', 'lock', 'unlock', 'repair'):
            paths = positional(rest[1:], ('--reason',))
        else:
            deny('git worktree %s is not available' % verb)
        if not paths:
            deny('name the worktree path under .claude/worktrees/')
        for p in paths[:1] if verb == 'add' else paths:
            real = resolve(expand(p, env), cur)
            if not routine_worktree(real):
                deny('the routine worktree is %s/rn-<slug>' % WORKTREES)
        return
    if sub == 'push':
        check_push(rest, repo_dir)
        return
    if sub in GIT_WORKTREE_WRITE:
        if not in_worktree:
            deny('git %s runs only inside .claude/worktrees/rn-<slug>, never in the shared checkout or another session\'s worktree' % sub)
        if sub == 'commit' and any(r in ('--no-verify', '-n') for r in rest):
            deny('commits keep their hooks; the content guard runs in pre-commit')
        if sub in ('checkout', 'switch'):
            branch = option_value(rest, ('-b', '-B', '-c', '-C'))
            if branch and not BRANCH_RE.match(branch):
                deny('branches are named docs/release-notes-<slug>')
        return
    deny('git %s is not available to the routine' % sub)


def check_push(rest, repo_dir):
    for f in rest:
        if f.startswith('-') and f not in ('-u', '--set-upstream', '-q', '--quiet', '-v', '--verbose',
                                           '--porcelain', '--progress', '--no-progress'):
            deny('git push %s is not available to the routine' % f)
    pos = [r for r in rest if not r.startswith('-')]
    if not pos or pos[0] != 'origin':
        deny('push to origin with an explicit refspec: git push -u origin docs/release-notes-<slug>')
    refs = pos[1:]
    if not refs:
        deny('name the branch: git push -u origin docs/release-notes-<slug>')
    for ref in refs:
        if ref.startswith('+'):
            deny('forced pushes are not available')
        src, _, dst = ref.partition(':')
        dst = dst or src
        if not src or not dst:
            deny('deleting remote branches is not available')
        if not BRANCH_RE.match(re.sub(r'^refs/heads/', '', dst)):
            deny('only docs/release-notes-<slug> branches are pushed, not %s' % dst)
        where = repo_dir if src == 'HEAD' else REPO
        if where is None:
            deny('push from a directory the guard can follow')
        check_scope(src, where)


def check_http(prog, args, cur, env):
    for a in args:
        url = expand(a, env)
        if '://' in url or re.match(r'^[\w.-]+\.(com|net|org|io|ai|sh|app|dev|co|cloud)(/|:|$)', url):
            host = re.sub(r'^[a-z]+://', '', url).split('/')[0].split('@')[-1].rsplit(':', 1)[0]
            if host not in ('127.0.0.1', 'localhost', '[::1]', '0.0.0.0'):
                deny('%s reaches only the local stack, not %s' % (prog, host))
    out = option_value(args, ('-o', '--output', '-O', '--output-document'))
    if out and out not in ('-',):
        check_write_target(out, cur, env)


def check_npx(args):
    if option_value(args, ('-p', '--package')):
        deny('npx --package is not available')
    pos = positional(args)
    if not pos:
        return
    pkg, rest = pos[0], pos[1:]
    if pkg == 'pnpm@10.6.5':
        if rest[:1] and rest[0] not in ('install', 'i', 'run', 'exec', 'test', 'typecheck', 'lint', 'list', 'ls', 'why'):
            deny('pnpm %s changes dependencies' % rest[0])
        if rest[:1] in (['install'], ['i']) and len(rest) > 1:
            deny('installing new packages is not available')
        return
    if pkg in ('next', 'prettier', 'eslint', 'tsc'):
        return
    deny('npx %s would download and run a package; only pnpm@10.6.5, next, prettier, eslint and tsc are available' % pkg)


def check_package_manager(prog, args):
    pos = positional(args, ('--filter', '-F', '-C', '--dir', '--prefix'))
    sub = pos[0] if pos else ''
    if any(a in ('-g', '--global') for a in args):
        deny('global installs are not available')
    if sub in ('add', 'remove', 'rm', 'uninstall', 'un', 'update', 'up', 'upgrade', 'publish', 'dlx',
               'link', 'unlink', 'login', 'logout', 'adduser', 'token', 'owner', 'access', 'config',
               'set', 'self-update', 'env', 'pack'):
        deny('%s %s is not available to the routine' % (prog, sub))
    if sub in ('install', 'i', 'ci'):
        if len(pos) > 1:
            deny('installing new packages is not available')
        if prog == 'pnpm':
            deny('the Homebrew pnpm rewrites the lockfile; use npx -y pnpm@10.6.5 install --frozen-lockfile')


def check_uv(args, cur, env, depth, whole):
    pos = positional(args, ('--with', '--python', '-p', '--project', '--directory', '--env-file'))
    sub = pos[0] if pos else ''
    if sub in ('', '--version', 'version', 'help'):
        return
    if sub != 'run':
        deny('uv %s changes the shared environment' % sub)
    i = args.index('run') + 1
    while i < len(args) and args[i].startswith('-'):
        if args[i] in ('--with', '--python', '-p', '--project', '--directory', '--env-file'):
            i += 1
        i += 1
    check_argv(args[i:], cur, env, depth, whole)


def trusted(real):
    """The skill's scripts, installed packages, and repository files as committed."""
    if under(real, SKILL_SCRIPTS) or '/node_modules/' in real:
        return True
    if not under(real, REPO):
        return False
    top = subprocess.run(['git', '-C', os.path.dirname(real), 'rev-parse', '--show-toplevel'],
                         capture_output=True, text=True, timeout=5).stdout.strip()
    if not top:
        return False
    rel = os.path.relpath(real, os.path.realpath(top))
    tracked = subprocess.run(['git', '-C', top, 'ls-files', '--error-unmatch', '--', rel],
                             capture_output=True, timeout=5).returncode == 0
    pristine = subprocess.run(['git', '-C', top, 'diff', '--quiet', 'HEAD', '--', rel],
                              capture_output=True, timeout=5).returncode == 0
    return tracked and pristine


def script_source(path, cur, env):
    real = resolve(expand(path, env), cur)
    if real is None or '$' in path and '$' in expand(path, env):
        deny('run scripts by literal path, not %s' % path)
    files = sorted(glob.glob(real)) if re.search(r'[*?\[]', real) else [real]
    sources = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8', errors='replace') as fh:
                sources.append((os.path.realpath(f), fh.read(2000000)))
        except OSError:
            pass
    return sources


def check_shell(prog, args, cur, env, depth):
    code = option_value(args, ('-c',))
    if code is not None:
        check_command(code, cur, depth + 1, env)
        return
    pos = positional(args, ('-o', '+o', '-O', '+O'))
    if not pos:
        return
    script = pos[0]
    if prog in ('source', '.') and re.search(r'(^|/)\.env\.local$', script):
        return
    for real, source in script_source(script, cur, env):
        if under(real, SKILL_SCRIPTS):
            if os.path.basename(real) == 'local-stack.sh':
                wt = pos[2] if len(pos) > 2 else None
                wt_real = resolve(expand(wt, env), cur) if wt else None
                if not routine_worktree(wt_real):
                    deny('local-stack.sh runs only on .claude/worktrees/rn-<slug>')
            continue
        if not trusted(real):
            check_command(source, os.path.dirname(real), depth + 1, env)


def check_interpreter(prog, args, cur, env, whole):
    module = option_value(args, ('-m',))
    if module and module.split('.')[0] in ('pip', 'venv', 'ensurepip', 'http', 'smtplib', 'ftplib'):
        deny('%s -m %s is not available to the routine' % (prog, module))
    code = option_value(args, ('-c', '-e', '--eval', '-p', '--print'))
    if code is not None:
        # inline code was read by raw_scan; code loaded with "$(cat file)" is read here
        m = re.match(r'^\$\(cat\s+(\S+)\)$', code.strip())
        if m:
            for real, source in script_source(m.group(1).strip('"\''), cur, env):
                if not trusted(real):
                    raw_scan(source)
        return
    pos = positional(args, ('-W', '-X', '--input-type', '-r', '--require', '--import', '--loader',
                            '--test-name-pattern', '--test-reporter', '--conditions', '-C'))
    if not pos or pos[0] == '-':
        return
    if os.path.basename(pos[0]) == 'manage.py':
        check_manage(pos[1:], whole)
        return
    for real, source in script_source(pos[0], cur, env):
        if not trusted(real):
            raw_scan(source)


def check_manage(args, whole):
    if CLONE_DB not in whole:
        deny('manage.py runs only against the clone (DATABASE_URL=.../%s)' % CLONE_DB)
    pos = positional(args)
    if pos and pos[0] in ('flush', 'sqlflush', 'reset_db', 'dbshell', 'createsuperuser', 'changepassword'):
        deny('manage.py %s is not available to the routine' % pos[0])


def check_find(args, cur, env, depth, whole):
    roots = []
    for a in args:
        if a.startswith('-') or a in ('(', ')', '!'):
            break
        roots.append(a)
    if '-delete' in args:
        for r in roots or ['.']:
            check_write_target(r, cur, env)
    for i, a in enumerate(args):
        if a in ('-exec', '-execdir', '-ok', '-okdir'):
            sub = []
            for b in args[i + 1:]:
                if b in (';', '+', '\\;'):
                    break
                sub.append(b)
            check_argv([s for s in sub if s != '{}'], cur, env, depth, whole)
            if sub and '{}' in sub and write_targets(os.path.basename(sub[0]), sub[1:] or ['{}']):
                for r in roots or ['.']:
                    check_write_target(r, cur, env)


# ---------------------------------------------------------------- tools

def check_tool(payload):
    tool = payload.get('tool_name') or ''
    data = payload.get('tool_input') or {}
    cwd = payload.get('cwd') or REPO
    if tool.startswith('mcp__'):
        deny('MCP tools are not available to the routine (%s)' % tool)
    if tool in DENY_TOOLS:
        deny(DENY_TOOLS[tool])
    if tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        check_write_path(data.get('file_path') or data.get('notebook_path') or '', cwd)
    elif tool in ('Read', 'Grep', 'Glob'):
        for key in ('file_path', 'path', 'glob', 'pattern' if tool == 'Glob' else ''):
            value = data.get(key) if key else None
            if value and SECRET_PATH.search(value):
                deny('secrets stay unread (%s)' % value)
    elif tool == 'Bash':
        check_command(data.get('command') or '', cwd)


def main():
    try:
        payload = json.loads(sys.stdin.read() or '{}')
    except ValueError:
        return 0
    if not is_routine(payload):
        return 0
    try:
        check_tool(payload)
        return 0
    except Deny as stop:
        reason = str(stop)
    except Exception as error:  # fail closed inside the routine
        reason = 'the guard could not inspect this call (%s: %s)' % (type(error).__name__, error)
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': 'Release Notes routine guard: %s. Do not retry or work around it; '
                                    'record it in the run report.' % reason,
    }}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
