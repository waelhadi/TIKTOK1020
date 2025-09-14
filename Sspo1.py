_N='utf-8-sig'
_M='retries'
_L='times_ms'
_K='ignore'
_J='printed'
_I='consec_fail'
_H=None
_G='fail'
_F='total'
_E='ok'
_D='strength'
_C=1.
_B=.0
_A=True
import os,re,time,hashlib,threading,queue,random
from collections import deque,defaultdict
GREEN='\x1b[92m'
RED='\x1b[91m'
CYAN='\x1b[96m'
YELLOW='\x1b[93m'
MAG='\x1b[95m'
BLUE='\x1b[94m'
WHITE='\x1b[97m'
RESET='\x1b[0m'
BOLD='\x1b[1m'
DIM='\x1b[2m'
def _ansi256(idx):return f"[38;5;{idx}m"
def _hash32(s):
	A=2166136261
	for B in s:A^=ord(B);A=A*16777619&4294967295
	return A
def _rgb_to_256_index(r,g,b):r=max(0,min(5,r));g=max(0,min(5,g));b=max(0,min(5,b));return 16+36*r+6*g+b
def color_for_session(sid):
	if not sid:return WHITE
	A=_hash32(sid);C=2+A%4;B=2+(A>>3)%4;D=2+(A>>7)%4
	if A>>11&1:C,B=B,C
	if A>>13&1:B,D=D,B
	E=_rgb_to_256_index(C,B,D);return _ansi256(E)
SHOW_BANNER=_A
SHOW_SESSION_HEADER=_A
SHOW_DASHBOARD=_A
DASHBOARD_MAX_ROWS=16
PRINT_EVERY_STATUS=15
SLOW_MODE=_A
SLOW_TARGET_QPS=.45
SLOW_SLEEP_BETWEEN_IDS=.4
CONFIRM_SUCCESS_TIMES=2
CONFIRM_GAP=.25
RETRY_BACKOFF_BASE=.7
RETRY_BACKOFF_FACTOR=2.3
RETRY_JITTER_MAX=.35
RETRY_BACKOFF_CAP=45.
RESTART_WHEN_DONE=_A
LOOP_PAUSE_BETWEEN=_B
MAX_WORKERS_CAP=128
def load_ids(file_primary='3.txr',file_fallback='3.txt'):
	C=file_primary;D=C if os.path.isfile(C)else file_fallback
	if not os.path.isfile(D):return[]
	E,F=[],set()
	with open(D,'r',encoding=_N,errors=_K)as H:
		for I in H:
			A=I.strip()
			if not A:continue
			G=re.search('(\\d{8,})',A);B=G.group(1)if G else A
			if B not in F:F.add(B);E.append(B)
	return E
def load_sessions(path='1.txt'):
	if not os.path.isfile(path):return[]
	B=[]
	with open(path,'r',encoding=_N,errors=_K)as E:
		for F in E:
			A=F.strip()
			if not A or A.startswith('#'):continue
			B.append(A)
	C,D=[],set()
	for A in B:
		if A not in D:D.add(A);C.append(A)
	return C
def _full(s):return s or''
def strength_color(score):
	A=score
	if A is _H:return MAG
	if A>=80:return GREEN+BOLD
	if A>=60:return YELLOW+BOLD
	if A>=40:return CYAN
	return RED+BOLD
def compute_strength(ok,fail,times_ms,retries_used,consec_fail):B=retries_used;A=times_ms;C=ok+fail;D=ok/C if C else _B;E=sum(A)/len(A)if A else _B;F=sum(B)/len(B)if B else _B;G=_C-min(max((E/1e3-.4)/(1.2-.4),_B),_C);H=_C-min(F/2.,_C);I=.65*G+.35*H;J=_C-min(consec_fail/1e1,_C);K=1e2*(.6*D+.25*I+.15*J);return round(max(_B,min(K,1e2)),1)
processed_ok_global=set()
attempts_by_id=defaultdict(int)
grand_total=0
state_lock=threading.Lock()
rl_lock=threading.Lock()
_last_call_ts=_B
_min_interval=_C/max(SLOW_TARGET_QPS,.0001)
stats={}
def ensure_stat(sid):
	if sid not in stats:stats[sid]={_E:0,_G:0,_F:0,'cycles':0,_L:deque(maxlen=300),_M:deque(maxlen=300),_I:0,_D:_H,_J:0}
def print_dashboard():
	if not SHOW_DASHBOARD or not stats:return
	print();print(BOLD+MAG+'Live per-session summary:'+RESET);D=f"{BOLD}{CYAN}{'Session':<32}{RESET} | {YELLOW}{'Total':>6}{RESET} | {GREEN}{'OK':>5}{RESET} | {RED}{'NG':>5}{RESET} | {BLUE}{'%OK':>4}{RESET} | {BOLD}{'Strength':>8}{RESET}";print(D);print('-'*len(D));B=sorted(stats.items(),key=lambda kv:kv[1][_F],reverse=_A)
	if len(B)>DASHBOARD_MAX_ROWS:B=B[:DASHBOARD_MAX_ROWS]
	for(E,A)in B:G=color_for_session(E);C,F,H=A[_F],A[_E],A[_G];I=F*1e2/C if C else _B;J=strength_color(A[_D]);K=f"{A[_D]:.1f}"if A[_D]is not _H else'--';L=f"{G}{_full(E)}{RESET}";print(f"{L:<32} | {YELLOW}{C:>6}{RESET} | {GREEN}{F:>5}{RESET} | {RED}{H:>5}{RESET} | {BLUE}{I:>3.0f}%{RESET} | {J}{K:>8}{RESET}")
	print()
def sig(values):
	A=hashlib.sha1()
	for B in values:A.update(B.encode('utf-8',_K));A.update(b'\x00')
	return A.hexdigest()
def _rl_wait():
	if not SLOW_MODE:return
	global _last_call_ts
	with rl_lock:
		B=time.perf_counter();A=_last_call_ts+_min_interval-B
		if A>0:time.sleep(A)
		_last_call_ts=time.perf_counter()
def worker(sessionid,work_q,all_ids_set):
	I=work_q;H=False;C=sessionid;global grand_total;ensure_stat(C);A=stats[C];J=color_for_session(C);G=f"{J}{_full(C)}{RESET}"
	if SHOW_SESSION_HEADER:print(f"{J}{BOLD}Worker started for session:{RESET} {G}")
	while _A:
		try:B=I.get(timeout=.5)
		except queue.Empty:
			with state_lock:M=processed_ok_global==all_ids_set
			if M:break
			else:continue
		D=0;K=0
		while D<CONFIRM_SUCCESS_TIMES:
			_rl_wait();N=time.perf_counter();E=H
			try:O=afr(B,C);E=O is not H
			except Exception:E=H
			L=(time.perf_counter()-N)*1e3
			with state_lock:
				grand_total+=1;A[_F]+=1;A[_L].append(L)
				if E:D+=1;attempts_by_id[B]+=1;A[_E]+=1;A[_I]=0
				else:D=0;attempts_by_id[B]+=1;A[_M].append(attempts_by_id[B]-1);A[_G]+=1;A[_I]+=1
				A[_D]=compute_strength(A[_E],A[_G],A[_L],A[_M],A[_I]);A[_J]=A.get(_J,0)+1
				if A[_J]%PRINT_EVERY_STATUS==0:P=strength_color(A[_D]);Q=A[_E]*1e2/A[_F]if A[_F]else _B;print(f"{G} | {GREEN}OK:{A[_E]}{RESET} {RED}NG:{A[_G]}{RESET} | {BLUE}{Q:>3.0f}%{RESET} | Strength:{P}{A[_D]if A[_D]is not _H else'--'}{RESET} | Last latency:{L:>4.0f}ms | Global total:{YELLOW}{grand_total}{RESET} | ID:{B}")
			if E:
				if D<CONFIRM_SUCCESS_TIMES and CONFIRM_GAP>0:time.sleep(CONFIRM_GAP)
			else:K+=1;F=RETRY_BACKOFF_BASE*RETRY_BACKOFF_FACTOR**(K-1);F=min(F,RETRY_BACKOFF_CAP);F+=random.uniform(_B,RETRY_JITTER_MAX);time.sleep(F)
		with state_lock:processed_ok_global.add(B)
		if SLOW_MODE and SLOW_SLEEP_BETWEEN_IDS>0:time.sleep(SLOW_SLEEP_BETWEEN_IDS)
		I.task_done()
	if SHOW_SESSION_HEADER:print(f"{GREEN}Worker finished for session:{RESET} {G}")
if __name__=='__main__':
	if SHOW_BANNER:mode_txt='SAFE-SLOW (sequential, strict order, double-confirm)'if SLOW_MODE else'Parallel (load-balanced)';print(f"{CYAN}{BOLD}Run mode:{RESET} {MAG}{mode_txt}{RESET}");print(f"{CYAN}Impossible to skip — strict retries, double-confirm per video.{RESET}")
	while _A:
		sessions=load_sessions('1.txt')
		if not sessions:print(f"{YELLOW}No sessions found in 1.txt — add them (one per line).{RESET}",end='\r');time.sleep(_C);continue
		file_ids=load_ids('3.txr','3.txt')
		if not file_ids:print(f"{YELLOW}No IDs found in 3.txr/3.txt — add IDs to the file.{RESET}",end='\r');time.sleep(_C);continue
		all_ids_set=set(file_ids);work_q=queue.Queue()
		with state_lock:
			todo_now=[A for A in file_ids if A not in processed_ok_global]
			if not todo_now and RESTART_WHEN_DONE:processed_ok_global.clear();attempts_by_id.clear();todo_now=list(file_ids)
		for v in todo_now:work_q.put(v)
		workers_count=1 if SLOW_MODE else min(len(sessions),MAX_WORKERS_CAP);threads=[]
		for i in range(workers_count):sid=sessions[i%len(sessions)];ensure_stat(sid);t=threading.Thread(target=worker,args=(sid,work_q,all_ids_set),daemon=_A);threads.append(t);t.start()
		while _A:
			try:
				work_q.join()
				with state_lock:all_done=processed_ok_global==all_ids_set
				if all_done:break
				else:time.sleep(.2)
			except KeyboardInterrupt:print(f"\n{RED}Stopped by user.{RESET}");break
		for t in threads:t.join(timeout=.1)
		with state_lock:okn=len(processed_ok_global&all_ids_set);ttl=len(all_ids_set)
		print(f"\n{BOLD}Round summary (double-confirm):{RESET} {GREEN}OK (videos fully confirmed):{okn}{RESET} | {YELLOW}Total:{ttl}{RESET}");print_dashboard()
		if RESTART_WHEN_DONE:time.sleep(LOOP_PAUSE_BETWEEN);continue
		else:break
