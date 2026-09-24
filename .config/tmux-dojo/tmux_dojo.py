#!/usr/bin/env python3
"""A local shortcut trainer. Practice keys are never executed as tmux commands."""
import argparse
import collections
import dataclasses
import datetime
import json
import os
from pathlib import Path
import random
import select
import shlex
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import termios
import textwrap
import time
import tty

VERSION = 1
HERE = Path(__file__).resolve().parent
STATE = Path(os.environ.get('XDG_STATE_HOME', str(Path.home()/'.local/state'))) / 'tmux-dojo' / 'progress.json'
PALETTE = {'text':'205;214;244', 'dim':'166;173;200', 'cyan':'137;220;235',
           'green':'166;227;161', 'peach':'250;179;135', 'purple':'203;166;247', 'red':'243;139;168'}

@dataclasses.dataclass(frozen=True)
class Card:
    id: str
    group: str
    prompt: str
    routes: tuple
    why: str

def card(id, group, prompt, routes, why):
    return Card(id, group, prompt, tuple(tuple(r) for r in routes), why)

CARDS = [
 card('left','panes','Your shell is in the pane on the LEFT. Move focus there.', [('C-h',),('P','h')], 'h j k l = left, down, up, right. Ctrl moves directly between local panes.'),
 card('down','panes','Move from the agent pane to the pane BELOW.', [('C-j',),('P','j')], 'Ctrl+j moves down. You do not need the window picker to change panes.'),
 card('up','panes','Move from the shell to the pane ABOVE.', [('C-k',),('P','k')], 'Ctrl+k moves up. These are your existing smart tmux/Neovim bindings.'),
 card('right','panes','Move focus to the pane on the RIGHT.', [('C-l',),('P','l')], 'Ctrl+l moves right; the cyan ACTIVE border shows where typing will go.'),
 card('cycle','panes','Cycle to the next pane without opening a picker.', [('C-\\',)], 'Ctrl+backslash cycles panes without the leader.'),
 card('pane1','panes','Jump directly to PANE 1.', [('P','1'),('P','q','1')], 'In your current setup, leader+1/2/3 select panes, not windows.'),
 card('zoom','panes','Temporarily give this pane the whole window.', [('P','z')], 'Leader+z toggles zoom. Use it again to restore your layout.'),
 card('split_side','layout','Create a second pane SIDE BY SIDE.', [('P','\\')], 'Backslash resembles a vertical divider. The real binding preserves the working directory.'),
 card('split_down','layout','Create a new pane BELOW this one.', [('P','-')], 'A dash resembles a horizontal divider.'),
 card('resize','layout','Make this pane wider toward the RIGHT.', [('P','L')], 'Capital H/J/K/L resize. Lowercase h/j/k/l move focus after the leader.'),
 card('next','windows','Go to the NEXT window in this session.', [('P','n')], 'Leader+n is next window. Option+n is next SESSION.'),
 card('previous','windows','Go to the PREVIOUS window in this session.', [('P','C-p')], 'Your leader+p pastes. Previous window is leader+Ctrl+p: this is worth testing against a simpler layout.'),
 card('window6','windows','Jump directly to WINDOW 6.', [('P','6')], 'Leader+4 through 9 select windows. Leader+1 through 3 currently select panes.'),
 card('new','windows','Open a NEW window in the current directory.', [('P','c')], 'c creates a window. Splits create panes inside the current window.'),
 card('picker','windows','Show the familiar window/session TREE picker.', [('P','w')], 'Leader+w remains useful for browsing. Use direct keys for small, familiar moves.'),
 card('fuzzy','sessions','Search all sessions and windows in the FUZZY popup.', [('P','f')], 'Leader+f searches. The real popup lets you type a project name.'),
 card('work','sessions','Jump straight to the WORK session.', [('M-w',)], 'Left Option+w jumps to work. In your iTerm profile, left Option sends Esc+.'),
 card('remotes','sessions','Jump straight to the REMOTES session.', [('M-r',)], 'Left Option+r jumps to remotes.'),
 card('last_session','sessions','Return to the session you were JUST using.', [('M-Tab',),('P','Tab')], 'Option+Tab or leader+Tab toggles the previous SESSION, not the previous window.'),
 card('next_session','sessions','Cycle to the NEXT session.', [('M-n',),('P',')')], 'Option+n changes sessions; leader+n changes windows.'),
 card('copy','tools','Enter copy mode so you can select terminal output.', [('P','v'),('P','[')], 'Then v begins selection and y copies. This trainer stops at entering copy mode.'),
 card('paste','tools','Paste the tmux clipboard buffer.', [('P','p'),('P',']')], 'Both leader+p and leader+] paste today. Keeping only ] would free p for previous window.'),
 card('yazi','tools','Open your colorful Yazi FILE BROWSER.', [('P','y')], 'Leader+y opens Yazi in its own files window. Inside Yazi, q closes it.'),
 card('help','tools','Open the tmux shortcut ACTION MENU.', [('P','?')], 'Leader+? opens which-key. Asking the real menu for help is a useful habit.'),
]
NESTED = [
 card('remote_same','nested','NESTED, same leader: open the CLUSTER window picker.', [('P','P','w')], 'Outer Ctrl+Space + Ctrl+Space sends one Ctrl+Space inward. Then w reaches the cluster.'),
 card('local_nested','nested','NESTED, same leader: open the LOCAL window picker.', [('P','w')], 'One prefix stays local. Two prefixes pass one inward.'),
 card('remote_b','nested','NESTED, remote uses Ctrl+B: open the CLUSTER picker.', [('C-b','w')], 'Your local prefix is Ctrl+Space, so Ctrl+B passes through to a remote using the default prefix.'),
 card('remote_separate','nested','SEPARATE SSH TAB, remote uses Ctrl+Space: open its picker.', [('P','w')], 'No nesting means no doubled prefix. Matching local/remote shortcuts work in separate terminal tabs.'),
]
BY_ID = {c.id:c for c in CARDS+NESTED}

def pretty(route):
    names = {'P':'Ctrl+Space', 'Tab':'Tab', 'Enter':'Enter', 'ESC':'Esc'}
    return ' -> '.join(names.get(k, k.replace('C-','Ctrl+').replace('M-','Option+')) for k in route)

def trial(c):
    if c.id == 'previous': return dataclasses.replace(c, routes=(('P','p'),), why='TRIAL ONLY: leader+p means previous window; paste moves to leader+].')
    if c.id == 'paste': return dataclasses.replace(c, routes=(('P',']'),), why='TRIAL ONLY: use leader+] for paste and reserve p for previous window.')
    return c

def match(tokens, routes):
    tokens=tuple(tokens)
    if tokens in routes: return 'correct'
    if any(r[:len(tokens)] == tokens for r in routes): return 'partial'
    return 'wrong'

def load_state(path=STATE):
    if not path.exists(): return []
    obj=json.loads(path.read_text())
    if not isinstance(obj,dict) or obj.get('version') != VERSION or not isinstance(obj.get('events'),list):
        raise ValueError('Unrecognized progress file: '+str(path))
    return obj['events']

def save_state(events, path=STATE):
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,name=tempfile.mkstemp(prefix='.progress-',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w') as f:
            json.dump({'version':VERSION,'events':events[-2000:]},f,indent=2)
            f.write('\n')
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)

def plan(group, events, rng=random):
    if group == 'compare':
        rounds=[]
        for _ in range(4):
            for key in rng.sample(['previous','paste'],2):
                for profile in rng.sample(['current','trial'],2):
                    c=BY_ID[key]
                    c=trial(c) if profile=='trial' else dataclasses.replace(c,routes=(c.routes[0],))
                    rounds.append((c,profile))
        return rounds
    pool = NESTED if group=='nested' else [c for c in CARDS if group=='daily' or c.group==group]
    weak=collections.Counter()
    for e in events[-100:]:
        if e.get('mode')!='compare': weak[e['card']]+=e.get('misses',0)+2*e.get('hint',False)+2*e.get('awkward',False)
    result=[]
    for _ in range(min(12,len(pool))):
        chosen=rng.choices(pool,weights=[1+min(weak[c.id],8) for c in pool],k=1)[0]
        result.append((chosen,'current')); pool.remove(chosen)
    return result

def report(events):
    practice=[e for e in events if e.get('mode')!='compare']
    lines=[]
    if practice:
        recent=practice[-60:]
        clean=sum(e.get('complete') and not e.get('misses') and not e.get('hint') for e in recent)
        lines.append('Recent practice: %d/%d first-try, no-hint answers.' % (clean,len(recent)))
        grouped=collections.defaultdict(list)
        for e in recent: grouped[e['card']].append(e)
        scores=sorted(grouped,key=lambda k:sum(e.get('misses',0)+2*e.get('hint',False)+2*e.get('awkward',False)+(not e.get('complete')) for e in grouped[k]),reverse=True)
        for key in scores[:5]:
            es=grouped[key]; c=BY_ID.get(key)
            if c:
                lines.append('%-15s %2d tries | %2d mistakes | %2d hints | %2d awkward' % (key,len(es),sum(e.get('misses',0) for e in es),sum(e.get('hint',False) for e in es),sum(e.get('awkward',False) for e in es)))
    else: lines.append('No practice history yet. Start with a daily round.')
    lines += ['', 'A/B experiment: previous window and paste']
    for key in ['previous','paste']:
        bits=[]
        for profile in ['current','trial']:
            es=[e for e in events if e.get('mode')=='compare' and e.get('card')==key and e.get('profile')==profile and e.get('complete')][-20:]
            if es:
                bits.append('%s %.1fs median / %d errors / %d awkward (n=%d)' % (profile,statistics.median(e['seconds'] for e in es),sum(e['misses'] for e in es),sum(e.get('awkward',False) for e in es),len(es)))
            else: bits.append(profile+': no trials')
        lines.append(key+':'); lines.extend('  '+s for s in bits)
    lines += ['', 'Decision guide:',
      'Forgotten but comfortable? Practice it. Repeatedly awkward? Try a remap.',
      'Use several A/B rounds; compare mistakes and awkward flags as well as time.',
      'The trial frees leader+p for previous window; leader+] already pastes today.',
      'Your 1-3=pane / 4-9=window split is another candidate for simplification.',
      'No real shortcuts are changed by the game.']
    return lines

class Terminal:
    def __enter__(self):
        self.fd=sys.stdin.fileno(); self.old=termios.tcgetattr(self.fd)
        tty.setraw(self.fd)
        sys.stdout.write('\x1b[?1049h\x1b[?25l'); sys.stdout.flush()
        return self
    def __exit__(self,*args):
        termios.tcsetattr(self.fd,termios.TCSADRAIN,self.old)
        sys.stdout.write('\x1b[0m\x1b[?25h\x1b[?1049l'); sys.stdout.flush()
    def key(self):
        b=os.read(self.fd,1)
        if not b: raise EOFError()
        if b==b'\x03': raise KeyboardInterrupt()
        if b==b'\x1b':
            if not select.select([self.fd],[],[],.12)[0]: return 'ESC'
            nxt=os.read(self.fd,1)
            if nxt in (b'[',b'O'):
                seq=nxt
                while len(seq)<12 and select.select([self.fd],[],[],.02)[0]:
                    seq+=os.read(self.fd,1)
                    if seq[-1:] in b'ABCDHF~': break
                return {b'[A':'Up',b'[B':'Down',b'[C':'Right',b'[D':'Left'}.get(seq,'Special')
            return 'M-'+('Tab' if nxt==b'\t' else nxt.decode('utf8','replace'))
        n=b[0]
        if n==0: return 'P'
        if n==13: return 'Enter'
        if n==9: return 'Tab'
        if 1<=n<=26: return 'C-'+chr(n+96)
        if n==28: return 'C-\\'
        if n==127: return 'Backspace'
        return b.decode('utf8','replace')
    def draw(self, title, rows):
        width,height=shutil.get_terminal_size((90,30))
        # Leave one cell free to avoid automatic wrap and screen scrolling.
        width=max(12,width-4)
        content=[('TMUX DOJO  /  '+title,'cyan'),('', 'text')]+rows
        rendered=[]
        for text,color in content:
            for line in textwrap.wrap(str(text),width=width,replace_whitespace=False,drop_whitespace=True) or ['']:
                rendered.append('\x1b[38;2;'+PALETTE[color]+'m'+line)
        if len(rendered)>height-1:
            rendered=rendered[:max(1,height-2)]+['\x1b[38;2;'+PALETTE['peach']+'mEnlarge the terminal to see all details.']
        sys.stdout.write('\x1b[48;2;30;30;46m\x1b[2J\x1b[H'+'\r\n'.join(rendered)+'\x1b[0m'); sys.stdout.flush()

class Game:
    def __init__(self, term, events, path=STATE):
        self.t=term; self.events=events; self.path=path
    def persist(self): save_state(self.events,self.path)
    def pages(self,title,lines):
        page=0
        while True:
            size=max(4,shutil.get_terminal_size((90,30)).lines-8)
            chunk=lines[page*size:(page+1)*size]
            self.t.draw(title,[(s,'text') for s in chunk]+[('','text'),('n/p: page  |  q or Esc: menu','dim')])
            k=self.t.key()
            if k in ('q','ESC','Enter'): return
            if k in ('n','Right') and (page+1)*size<len(lines): page+=1
            if k in ('p','Left') and page: page-=1
    def play(self,group):
        rounds=plan(group,self.events); earned=0; streak=0; session=[]
        for index,(c,profile) in enumerate(rounds,1):
            seq=[]; misses=0; hinted=False; last=''; started=time.monotonic()
            while True:
                rows=[('Round %d/%d     XP %d     Streak %d' % (index,len(rounds),earned,streak),'dim'),('', 'text'),
                      (c.prompt,'peach'),('', 'text')]
                if group=='compare':
                    rows += [('A/B '+profile.upper()+'   Target: '+pretty(c.routes[0]),'purple'),('Timing here measures a shown sequence, not recall. Trial is simulated.','dim')]
                elif c.group=='nested': rows += [('Cluster lesson is hypothetical: read the prefix assumptions in the prompt.','purple')]
                else: rows += [('Press the actual shortcut. Leader = Ctrl+Space.','dim')]
                rows += [('', 'text'),('PREFIX' if seq and seq[0]=='P' else 'Ready', 'red' if seq else 'dim'),
                         ('Keys: '+(pretty(seq) if seq else '_'),'cyan')]
                if hinted: rows += [('Hint: '+ '  OR  '.join(pretty(r) for r in c.routes),'green')]
                if last: rows += [(last,'red')]
                rows += [('', 'text'),('? hint  |  Esc skip  |  q end round  |  Ctrl+C quit','dim'),('This practice screen consumes shortcuts; it does not run their commands.','dim')]
                self.t.draw(group.upper(),rows)
                k=self.t.key()
                if not seq and k=='q':
                    self.pages('ROUND ENDED', ['Completed %d of %d prompts. Your completed attempts are saved.' % (len(session),len(rounds))]+report(self.events)); return
                if k=='ESC':
                    complete=False; break
                if not seq and k=='?': hinted=True; continue
                seq.append(k); result=match(seq,c.routes)
                if result=='correct': complete=True; break
                if result=='wrong':
                    other=next((x for x in CARDS if tuple(seq) in x.routes),None)
                    last=('That is '+other.id.replace('_',' ')+'. Try the requested action.' if other and other.id!=c.id else 'Not that combination. Try again, or press ? for a hint.')
                    misses+=1; seq=[]
            elapsed=round(time.monotonic()-started,2)
            points=max(10,100-20*misses-35*hinted) if complete else 0
            earned+=points; streak=streak+1 if complete and not misses and not hinted else 0
            event={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':group,'profile':profile,'card':c.id,'complete':complete,'misses':misses,'hint':hinted,'seconds':elapsed,'awkward':False,'route':pretty(seq) if complete else ''}
            self.events.append(event);session.append(event);self.persist()
            while True:
                self.t.draw('NICE MOVE' if complete else 'LEARNING ROUND',[
                    (('+'+str(points)+' XP  |  '+str(elapsed)+'s') if complete else 'Skipped; no penalty beyond this round.','green'),
                    ('','text'),('Shortcut: '+pretty(c.routes[0]),'cyan'),(c.why,'text'),('', 'text'),
                    ('Awkward to press: '+('YES - flagged for review' if event['awkward'] else 'no'),'peach'),
                    ('a: flag/unflag awkward  |  Enter: next  |  q: finish','dim')])
                k=self.t.key()
                if k=='a': event['awkward']=not event['awkward'];self.persist()
                if k in ('Enter',' '): break
                if k in ('q','ESC'): self.pages('YOUR REVIEW',report(self.events));return
        self.pages('ROUND COMPLETE', ['Earned %d XP across %d prompts.'%(earned,len(session)),'']+report(self.events))
    def menu(self):
        while True:
            self.t.draw('PRACTICE YOUR OWN SHORTCUTS',[
             ('Short rounds. Real keystrokes. Catppuccin colors.','dim'),('', 'text'),
             ('1  Daily mix          12 prompts; favors recent trouble spots','text'),
             ('2  Pane movement      Stop reaching for leader+w for every move','text'),
             ('3  Windows            Next, previous, create, direct jump','text'),
             ('4  Sessions           work / remotes / last / fuzzy picker','text'),
             ('5  Splits & resize    Build muscle memory for the separators','text'),
             ('6  Tools              Yazi, help, copy mode, paste','text'),
             ('7  Cluster lesson     Optional: separate tabs and nested prefixes','purple'),
             ('8  A/B key trial      Test previous-window and paste remapping','peach'),
             ('9  Progress & advice  See mistakes, hints, timing, awkward keys','green'),
             ('0  Key reference      Your current shortcuts','cyan'),('', 'text'),
             ('Try 1 first. Use ? for hints; flag awkward shortcuts with a.','text'),
             ('A/B trials only change the simulator, never your tmux bindings.','dim'),
             ('q: quit   |   Progress saved locally   |   Ctrl+C: quit anytime','dim')])
            k=self.t.key()
            if k in ('q','ESC'): return
            if k in '12345678' and len(k)==1:
                self.play({'1':'daily','2':'panes','3':'windows','4':'sessions','5':'layout','6':'tools','7':'nested','8':'compare'}[k])
            if k=='9': self.pages('PROGRESS & ADVICE',report(self.events))
            if k=='0': self.pages('YOUR KEY REFERENCE',[c.id.replace('_',' ')+': '+ ' OR '.join(pretty(r) for r in c.routes) for c in CARDS]+['','Nested lessons assume the remote prefixes stated in each prompt.'])

def binding_changes():
    snapshot=HERE/'bindings.json'
    if not os.environ.get('TMUX') or not snapshot.exists(): return []
    saved=json.loads(snapshot.read_text()); changes=[]
    for table,keys in saved.items():
        for key,expected in keys.items():
            p=subprocess.run(['tmux','list-keys','-T',table,key],capture_output=True,text=True,timeout=5)
            if p.returncode or p.stdout.strip()!=expected: changes.append(table+' '+key)
    p=subprocess.run(['tmux','show-option','-gv','prefix'],capture_output=True,text=True,timeout=5)
    if p.stdout.strip()!='C-Space': changes.append('prefix (expected Ctrl+Space)')
    return changes

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--play',action='store_true',help=argparse.SUPPRESS)
    p.add_argument('--report',action='store_true',help='Print practice results without starting the game')
    p.add_argument('--check-bindings',action='store_true',help='Check the live server against the saved lesson bindings')
    p.add_argument('--state-file',type=Path,default=STATE,help=argparse.SUPPRESS)
    args=p.parse_args()
    try:
        if args.check_bindings:
            if not os.environ.get('TMUX'): print('Run this check inside your normal tmux session.');return 1
            changed=binding_changes();print('Bindings match the lessons.' if not changed else 'Changed bindings: '+', '.join(changed));return int(bool(changed))
        if args.report:
            print('\n'.join(report(load_state(args.state_file))));return 0
        if os.environ.get('TMUX') and not args.play:
            changed=binding_changes()
            if changed:
                print('Your bindings changed: '+', '.join(changed)+'\nUpdate the trainer before practicing this profile.');return 1
            command=shlex.join([sys.executable,str(Path(__file__).resolve()),'--play','--state-file',str(args.state_file)])
            return subprocess.call(['tmux','display-popup','-E','-w','96%','-h','94%','-T',' Tmux Dojo - practice ','-s','bg=#1e1e2e,fg=#cdd6f4','-S','fg=#89dceb',command])
        if not sys.stdin.isatty() or not sys.stdout.isatty(): print('Start tmux-dojo from an interactive terminal.');return 1
        for sig in (signal.SIGTERM,signal.SIGHUP): signal.signal(sig,lambda *_: (_ for _ in ()).throw(SystemExit(0)))
        with Terminal() as terminal: Game(terminal,load_state(args.state_file),args.state_file).menu()
        return 0
    except (KeyboardInterrupt,EOFError): return 0
    except (OSError,ValueError,subprocess.SubprocessError) as e: print('tmux-dojo: '+str(e),file=sys.stderr);return 1

if __name__=='__main__': sys.exit(main())
