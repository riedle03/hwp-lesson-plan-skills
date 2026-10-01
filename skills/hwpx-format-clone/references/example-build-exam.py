# -*- coding: utf-8 -*-
"""
2026-1중간 출제원안 HWPX를 '서식 틀'로 클론하여, 본문만 너에게로로그인 20문항으로
외과적 치환한다. 헤더 표/스타일/단 설정/푸터는 템플릿 원본을 그대로 보존.
"""
import zipfile, re, os
from xml.sax.saxutils import escape as _esc
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, '2026-1중간(출제원안_공통국어1_1학년).hwpx')
SRCMD    = os.path.join(ROOT, '너에게로로그인_통합시험지_20문항.md')
OUT      = os.path.join(ROOT, '너에게로로그인_2026-1기말_출제원안.hwpx')

zin = zipfile.ZipFile(TEMPLATE)
sec = zin.read('Contents/section0.xml').decode('utf-8')

# ---------- 0) 마크다운 텍스트 정리(escape 해제) ----------
def clean(t):
    t = t.replace('\\*\\*', '＊＊').replace('\\*', '＊')
    t = t.replace('\\[', '[').replace('\\]', ']').replace('\\!', '!')
    return t

def esc(t):
    return _esc(clean(t))

# ---------- 1) 보기(<보 기>) 단일셀 테두리표 몰드 추출 ----------
_i = sec.find('기쁨 뒤에 슬픔')
_ts = sec.rfind('<hp:tbl', 0, _i)
_te = sec.find('</hp:tbl>', _i) + len('</hp:tbl>')
BOX = sec[_ts:_te]
_sub_open_end = BOX.find('>', BOX.find('<hp:subList')) + 1
_sub_close = BOX.find('</hp:subList>')
BOX_HEAD = BOX[:_sub_open_end]   # <hp:tbl ...> ... <hp:subList ...>
BOX_TAIL = BOX[_sub_close:]      # </hp:subList><hp:cellAddr/>...</hp:tbl>

# ---------- 1b) 정식 <보기> 장식 프레임 몰드 추출(상단 "보기" 노치 헤더 포함) ----------
# 템플릿의 겹받침 보기 = 5x5 장식 프레임(둥근 테두리 + 상단 중앙 "보기" 노치) 안에
# 내용 표가 중첩된 구조. 내부 내용 표를 감싼 문단을 제거해 HEAD/TAIL 몰드만 남기고,
# 산문 문단을 그 자리에 끼워 넣어 동일한 <보기> 박스를 만든다.
def _tbl_end(s, ts):
    depth = 0; p = ts
    while True:
        no = s.find('<hp:tbl', p + 1); nc = s.find('</hp:tbl>', p + 1)
        if nc == -1:
            return -1
        if no != -1 and no < nc:
            depth += 1; p = no
        else:
            if depth == 0:
                return nc + len('</hp:tbl>')
            depth -= 1; p = nc
_bi = sec.find('겹받침(자음군)')
_bts = sec.rfind('<hp:tbl', 0, _bi)
_FRAME = sec[_bts:_tbl_end(sec, _bts)]
_nest = _FRAME.find('<hp:tbl', 5)                  # 프레임 안의 내용 표
_nest_e = _tbl_end(_FRAME, _nest)
_btc = _FRAME.rfind('<hp:tc', 0, _nest)            # 내용 표를 품은 본문 셀
_sl_open = _FRAME.find('<hp:subList', _btc)
_sl_start = _FRAME.find('>', _sl_open) + 1         # 본문 셀 subList 내용 시작
_sl_close = _FRAME.find('</hp:subList>', _nest_e)  # 본문 셀 subList 닫기(중첩표 종료 후)
BOGI_HEAD = _FRAME[:_sl_start]    # 프레임 + 본문셀 + subList 열기 (템플릿 인트로/그리드 제거)
BOGI_TAIL = _FRAME[_sl_close:]    # </hp:subList> + 본문셀 닫기 + 프레임 닫기

# ---------- 2) OWPML 조각 생성기 ----------
LSEG = ('<hp:linesegarray><hp:lineseg textpos="0" vertpos="0" vertsize="1000" '
        'textheight="1000" baseline="850" spacing="600" horzpos="0" horzsize="29000" '
        'flags="393216"/></hp:linesegarray>')

# 표 id 중복 방지(문서 내 유일 id 발급)
_tblid = [1000]
def _newid():
    _tblid[0] += 1
    return str(_tblid[0])
def _uid(xml):
    """표 조각의 첫 <hp:tbl id="..."> 값을 유일 id로 교체."""
    return re.sub(r'(<hp:tbl id=")\d+', lambda m: m.group(1) + _newid(), xml, count=1)

# ----- 줄바꿈(linesegarray) 공통 유틸 -----
# 단일 lineseg만 넣으면 긴 텍스트가 1줄로 욱여넣어져 렌더된다(비-reflow 뷰어).
# 글자 디스플레이 폭으로 줄을 나눠 줄마다 lineseg를 생성하고, 줄 수를 함께 돌려준다.
def _disp_w(c):
    return 2 if ord(c) > 0x2000 else 1   # 한글·전각·원문자 = 2, ASCII·공백 = 1

def _wrap_starts(text, limit):
    starts = [0]; w = 0
    for idx, c in enumerate(text):
        cw = _disp_w(c)
        if w + cw > limit and idx > starts[-1]:
            starts.append(idx); w = 0
        w += cw
    return starts

def _flow_lseg(text, limit, vstep, horzsize, horzpos=0):
    """본문(지문·보기) 문단용 다줄 linesegarray + 줄 수."""
    starts = _wrap_starts(text, limit)
    segs = ''.join(
        f'<hp:lineseg textpos="{tp}" vertpos="{j*vstep}" vertsize="1148" textheight="1148" '
        f'baseline="975" spacing="600" horzpos="{horzpos}" horzsize="{horzsize}" '
        f'flags="{"393216" if j == 0 else "1441792"}"/>'
        for j, tp in enumerate(starts))
    return '<hp:linesegarray>' + segs + '</hp:linesegarray>', len(starts)

# md엔 밑줄 기능이 없으므로 <u>...</u> 관례로 밑줄 span을 표기한다.
# 지문 마커(㉠㉡㉢·ⓐⓑⓒ 등)가 가리키는 구간을 <u>로 감싸면 charPr31(밑줄)로 출력 →
# 학생이 마커가 어디까지인지 알 수 있다. 마커 기호 자체는 <u> 밖(밑줄 없음).
def _clean_u(text):
    return re.sub(r'</?u>', '', text)

def _runs(text, ncp='30', ucp='31'):
    """<u>…</u>는 ucp(밑줄), 나머지는 ncp 글자속성 run으로 분할."""
    out = []
    for seg in re.split(r'(<u>.*?</u>)', text):
        if not seg:
            continue
        if seg.startswith('<u>'):
            out.append(f'<hp:run charPrIDRef="{ucp}"><hp:t>{esc(seg[3:-4])}</hp:t></hp:run>')
        else:
            out.append(f'<hp:run charPrIDRef="{ncp}"><hp:t>{esc(seg)}</hp:t></hp:run>')
    return ''.join(out)

def P(parapr, runs):
    """runs: list of (charPrIDRef, text)"""
    body = ''.join(f'<hp:run charPrIDRef="{c}"><hp:t>{esc(t)}</hp:t></hp:run>' for c, t in runs)
    return (f'<hp:p id="0" paraPrIDRef="{parapr}" styleIDRef="0" pageBreak="0" '
            f'columnBreak="0" merged="0">{body}{LSEG}</hp:p>')

def group(label, rest, first):
    par = '11' if first else '9'
    return P(par, [('15', label), ('8', rest)])

def passage(text):
    return P('1', [('30', text)])

def choice(text):
    return P('26', [('8', text)])

def pagecont():
    return P('8', [('35', '---뒷장에 계속---')])

def endmark():
    return P('14', [('47', '-끝-')])

_NEG = ['않은', '않는', '없는', '아닌']
def qstem(line):
    m = re.match(r'^(\d+)\.\s*(.*)$', line)
    num, rest = m.group(1), m.group(2)
    text = '. ' + rest
    runs = [('15', num)]
    for tok in _NEG:
        idx = text.rfind(tok)
        if idx != -1:
            runs += [('8', text[:idx]), ('32', tok), ('8', text[idx+len(tok):])]
            break
    else:
        runs += [('8', text)]
    # P() escapes each run text; build manually to keep multi-run
    body = ''.join(f'<hp:run charPrIDRef="{c}"><hp:t>{esc(t)}</hp:t></hp:run>' for c, t in runs)
    return (f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" '
            f'columnBreak="0" merged="0">{body}{LSEG}</hp:p>')

# 보기 박스: 선택지가 딸린 정식 <보기> 전용. 템플릿의 장식 프레임(상단 중앙 "보기"
# 노치 헤더 + 둥근 테두리)을 그대로 복제하고, 본문 셀의 내용 표 자리에 산문 문단만
# 끼워 넣는다. 단순 읽기 참조 지문은 헤더 없는 passagebox를 쓴다.
def boxpara(lines):
    content = ''.join(
        f'<hp:p id="0" paraPrIDRef="29" styleIDRef="0" pageBreak="0" columnBreak="0" '
        f'merged="0">{_runs(l)}{_flow_lseg(_clean_u(l), 47, 1722, 28040)[0]}</hp:p>'
        for l in lines)
    box = _uid(BOGI_HEAD + content + BOGI_TAIL)
    return (f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" '
            f'merged="0"><hp:run charPrIDRef="8">{box}<hp:t/></hp:run>{LSEG}</hp:p>')

# 지문 박스: 보기 박스와 동일한 테두리표(borderFill3/4)이되 내부 문단을
# 지문 스타일(paraPr1/charPr30)로 채운다. 템플릿의 산문 지문 조판과 동일.
def passagebox(lines):
    parts = []
    tot = 0
    for l in lines:
        lseg, n = _flow_lseg(_clean_u(l), 47, 2050, 28000)   # 지문: 180% 줄간(≈2050), 줄당 ~47폭
        tot += n
        parts.append(
            f'<hp:p id="0" paraPrIDRef="1" styleIDRef="0" pageBreak="0" columnBreak="0" '
            f'merged="0">{_runs(l)}{lseg}</hp:p>')
    box = BOX_HEAD + ''.join(parts) + BOX_TAIL
    h = str(tot * 2050 + len(lines) * 150 + 1400)
    box = re.sub(r'(<hp:sz width="\d+" widthRelTo="ABSOLUTE" height=")\d+', r'\g<1>'+h, box, count=1)
    box = re.sub(r'(<hp:cellSz width="\d+" height=")\d+', r'\g<1>'+h, box, count=1)
    # 지문 표는 '글자처럼 취급' 해제(treatAsChar=0) + 본문이 위아래로 흐르도록(TOP_AND_BOTTOM)
    # + 쪽 경계에서 셀을 나눔(pageBreak=CELL)으로 긴 지문이 페이지 밖으로 나가지 않게 한다.
    # 템플릿 산문 지문 조판과 동일. (보기 박스 몰드의 인라인 속성을 덮어씀)
    box = box.replace('treatAsChar="1"', 'treatAsChar="0"', 1)
    box = box.replace('textWrap="SQUARE"', 'textWrap="TOP_AND_BOTTOM"', 1)
    box = box.replace('pageBreak="NONE"', 'pageBreak="CELL"', 1)
    box = _uid(box)
    return (f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" '
            f'merged="0"><hp:run charPrIDRef="8">{box}<hp:t/></hp:run>{LSEG}</hp:p>')

# 선택지 표: N행1열, 표 테두리 borderFill5 / 셀 borderFill7, 셀=paraPr26/charPr8.
# 템플릿의 선택지 조판(rowCnt=5 colCnt=1)과 동일 구조. (treatAsChar=1 인라인)
def _disp_w(ch):
    # 디스플레이 폭: 한글·전각·원문자·전각기호 = 2, 그 외(ASCII·공백) = 1
    return 2 if ord(ch) > 0x2000 else 1

def _cell_lseg(text):
    """선택지 텍스트를 셀 폭(약 56 디스플레이폭/줄)으로 줄 분할 → (linesegarray, 줄수).
    템플릿 선택지 셀이 항상 lineseg 2개였던 것과 달리, 길이에 맞춰 동적으로 생성해
    긴 선택지가 1줄로 욱여넣어지는 문제(셀 높이·lineseg 부족)를 해소한다."""
    starts = [0]; w = 0
    for idx, c in enumerate(text):
        cw = _disp_w(c)
        if w + cw > 56 and idx > starts[-1]:
            starts.append(idx); w = 0
        w += cw
    segs = ''.join(
        f'<hp:lineseg textpos="{tp}" vertpos="{j*1432}" vertsize="1100" textheight="1100" '
        f'baseline="935" spacing="332" horzpos="500" horzsize="28764" '
        f'flags="{"393216" if j == 0 else "1441792"}"/>'
        for j, tp in enumerate(starts))
    return '<hp:linesegarray>' + segs + '</hp:linesegarray>', len(starts)

def choicetable(choices, answer=None):
    trs = ''
    total = 0
    for i, ch in enumerate(choices):
        lseg, nlines = _cell_lseg(ch)
        ch_h = 2232 + (nlines - 1) * 1432   # 줄당 1432, 1줄=2232(상하 여백 포함)
        total += ch_h
        if answer and ch[:1] == answer:
            # 정답 선택지: 번호+공백에 노란 형광펜(출제원안 정답 표시, 템플릿과 동일)
            t = (f'<hp:markpenBegin color="#FFFF00"/>{esc(ch[:2])}'
                 f'<hp:markpenEnd/>{esc(ch[2:])}')
        else:
            t = esc(ch)
        trs += (
            '<hp:tr><hp:tc name="" header="0" hasMargin="1" protect="0" editable="0" '
            'dirty="0" borderFillIDRef="7"><hp:subList id="" textDirection="HORIZONTAL" '
            'lineWrap="BREAK" vertAlign="CENTER" linkListIDRef="0" linkListNextIDRef="0" '
            'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
            f'<hp:p id="0" paraPrIDRef="26" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="8"><hp:t>{t}</hp:t></hp:run>{lseg}</hp:p>'
            f'</hp:subList><hp:cellAddr colAddr="0" rowAddr="{i}"/>'
            '<hp:cellSpan colSpan="1" rowSpan="1"/>'
            f'<hp:cellSz width="29548" height="{ch_h}"/>'
            '<hp:cellMargin left="141" right="141" top="566" bottom="566"/></hp:tc></hp:tr>')
    n = len(choices); H = total
    tbl = (
        f'<hp:tbl id="{_newid()}" zOrder="4" numberingType="TABLE" textWrap="SQUARE" '
        'textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" pageBreak="CELL" repeatHeader="1" '
        f'rowCnt="{n}" colCnt="1" cellSpacing="0" borderFillIDRef="5" noAdjust="0">'
        f'<hp:sz width="29548" widthRelTo="ABSOLUTE" height="{H}" heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" '
        'holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="PARA" vertAlign="TOP" horzAlign="LEFT" '
        'vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="141" right="141" top="141" bottom="141"/>'
        f'<hp:inMargin left="141" right="141" top="141" bottom="141"/>{trs}</hp:tbl>')
    return (f'<hp:p id="0" paraPrIDRef="10" styleIDRef="0" pageBreak="0" columnBreak="0" '
            f'merged="0"><hp:run charPrIDRef="8">{tbl}<hp:t/></hp:run>{LSEG}</hp:p>')

# ---------- 3) 본문 마크다운 파싱 ----------
md = open(SRCMD, encoding='utf-8').read()
cut = md.find('# [교사용]')
body_md = md[:cut] if cut != -1 else md
lines = body_md.splitlines()

# [교사용] 정답표에서 문항별 정답을 읽어 출제원안 정답 형광펜에 사용(단일 출처)
ans_pairs = re.findall(r'\|\s*(\d+)\s*\|\s*([①②③④⑤])\s*\|', md[cut:] if cut != -1 else '')
ans_list = [a for _, a in sorted(ans_pairs, key=lambda x: int(x[0]))]
ans_iter = iter(ans_list)

# ---------- 본문 페이지네이션: 쪽 넘김 안내를 '본문'에 삽입(꼬리말 아님) ----------
# 양면 인쇄 규칙: 홀수쪽 하단 ---뒷면에 계속---, 짝수쪽 하단 ---뒷장에 계속---.
# 한글이 페이지를 재배치하지 못하도록, 쪽이 찰 때 안내 문단 + '강제 쪽 나누기'(다음
# 요소 pageBreak="1")를 본문에 넣어 페이지 경계를 결정한다. B4 2단: 한 쪽(2단) 용량
# ≈ 180000 hwpunit. 보수적으로 CAP를 잡아 내용이 페이지를 넘쳐 마커가 밀리는 것을 방지.
# 한 쪽(B4 2단) 실용량 ≈ 179000 hwpunit. 높이 모델은 한글 스타일 지표(지문 180% 줄간
# =2050, 선택지 셀 2232+1432, 보기 프레임 등)에 맞춰 추정 → 한글 페이지네이션에 근사.
# rhwp 렌더는 단일-lineseg 문단을 1줄로 cram하여 한글과 달라 페이지 검증엔 부적합.
# 여유 마진(~19%)을 둬 모델 오차가 있어도 세그먼트가 한글 1쪽을 넘지 않게 한다.
PAGE_CAP = 145000
def _nlines(text, limit):
    return max(1, len(_wrap_starts(_clean_u(text), limit)))
def _passage_h(ls):
    return sum(_nlines(l, 47) for l in ls) * 2050 + len(ls) * 150 + 1400
def _bogi_h(ls):
    return (1 + sum(_nlines(l, 47) for l in ls)) * 1722 + len(ls) * 150 + 4200
def _choice_h(chs):
    return sum(2232 + (_nlines(c, 56) - 1) * 1432 for c in chs)
def _stem_h(text):
    return _nlines(text, 56) * 1700 + 350
GROUP_H = 2700

start = next(k for k, l in enumerate(lines) if l.strip().startswith('【'))
out = []
gcount = 0
cum = 0          # 현재 쪽 누적 높이
page = 1         # 현재 쪽 번호(1-base)
pend_group = [None]   # 대기 중 지문군 헤더 (group과 지문을 한 덩어리로 배치)
pbuf = []        # 지문 줄 누적
qparts = []      # 현재 문항 조각 [(xml, h)…] (발문+보기+선택지)
cbuf = []        # 현재 문항 선택지 누적

def _pagebreak():
    """현재 쪽 하단에 안내 문단(본문)을 넣고 다음 요소를 새 쪽에서 시작(센티넬)."""
    global cum, page
    txt = '---뒷면에 계속---' if page % 2 == 1 else '---뒷장에 계속---'
    out.append(P('8', [('35', txt)]))      # paraPr8=CENTER, charPr35
    out.append('<<PB>>')
    cum = 0; page += 1

def _emit_unit(parts):
    """parts(=[(xml,h)…])를 한 덩어리로 배치. 현재 쪽에 안 들어가면 먼저 쪽을 넘긴다
    (덩어리가 쪽 경계를 가로지르지 않게 → 모든 쪽 경계가 안내 위치와 일치)."""
    global cum
    if not parts:
        return
    uh = sum(h for _, h in parts)
    if cum > 0 and cum + uh > PAGE_CAP:
        _pagebreak()
    for xml, _ in parts:
        out.append(xml)
    cum += uh

def _finish_choices():
    if cbuf:
        qparts.append((choicetable(cbuf[:], next(ans_iter, None)), _choice_h(cbuf)))
        cbuf.clear()

def flush_q():
    _finish_choices()
    _emit_unit(qparts); qparts.clear()

def flush_opener():
    """지문군 헤더 + 지문 박스를 한 덩어리로 배치."""
    parts = []
    if pend_group[0] is not None:
        parts.append(pend_group[0]); pend_group[0] = None
    if pbuf:
        parts.append((passagebox(pbuf[:]), _passage_h(pbuf))); pbuf.clear()
    _emit_unit(parts)

k = start
while k < len(lines):
    s = lines[k].strip()
    if not s:
        k += 1; continue
    if s.startswith('【'):                     # 새 지문 세트
        flush_q()                             # 이전 세트 마지막 문항 마무리
        flush_opener()                        # (대개 no-op) 잔여 오프너 배치
        gcount += 1
        m = re.match(r'(【[^】]*】)(.*)', s)
        pend_group[0] = (group(m.group(1), m.group(2), first=(gcount == 1)), GROUP_H)
    elif s == '-끝-':
        flush_q(); flush_opener(); out.append(endmark()); break
    elif s[0] in '①②③④⑤':
        cbuf.append(s)                         # 선택지 누적(현재 문항)
    elif re.match(r'^\d+\.\s', s) and '점]' in s:
        flush_q()                             # 이전 문항 마무리
        flush_opener()                        # 세트 오프너(헤더+지문) 먼저 배치
        qparts.append((qstem(s), _stem_h(s)))
    elif s in ('<보 기>', '<보기>'):
        _finish_choices()
        box = []; k += 1
        while k < len(lines) and lines[k].strip():
            box.append(lines[k].strip()); k += 1
        qparts.append((boxpara(box), _bogi_h(box))); continue
    elif re.match(r'^-{2,}.*계속.*-{2,}$', s):
        pass                                   # md의 기존 계속 마커 무시(자동 삽입으로 대체)
    else:                                      # 지문 본문(blockquote '>' 포함)
        pbuf.append(s.lstrip('> ').strip() if s.startswith('>') else s)
    k += 1
flush_q(); flush_opener()

# 센티넬 <<PB>> → 바로 다음 요소의 첫 문단 pageBreak="1"(강제 쪽 나누기)
_final = []
_pb = False
for _it in out:
    if _it == '<<PB>>':
        _pb = True; continue
    if _pb:
        _it = _it.replace('pageBreak="0"', 'pageBreak="1"', 1)
        _pb = False
    _final.append(_it)
MYBODY = ''.join(_final)
print('본문 쪽 넘김 안내 삽입: %d개(추정 %d쪽)' % (MYBODY.count('계속---'), page))
n_choicetbl = MYBODY.count('borderFillIDRef="5"')
n_passagebox = MYBODY.count('paraPrIDRef="1"')
print('생성 문단/박스 수:', len(out), '| 지문군:', gcount,
      '| 선택지표:', n_choicetbl, '| 지문문단(박스내):', n_passagebox)

# ---------- 4) 본문 영역 치환 + 헤더 메타 수정 ----------
omr = sec.find('OMR')
body_start = sec.find('</hp:p>', omr) + len('</hp:p>')
endpos = sec.find('-끝-')
body_end = sec.find('</hp:p>', endpos) + len('</hp:p>')

head = sec[:body_start]
tail = sec[body_end:]

assert '1학기 중간고사' in head
head = head.replace('1학기 중간고사', '1학기 기말고사')
n_date = head.count('2026년 5월 6일 2교시')
head = head.replace('2026년 5월 6일 2교시', '2026년 7월 6일 2교시')
head = head.replace('총 31문항', '총 20문항')
head = head.replace('～31번', '～20번').replace('~31번', '~20번').replace('1번～31', '1번～20')
print('날짜 치환:', n_date, '| 기말 반영:', '1학기 기말고사' in head)

new_sec = head + MYBODY + tail

# ---------- 5) XML well-formed 검증 ----------
ET.fromstring(new_sec)   # 예외 없으면 통과
print('XML well-formed OK | section0 len', len(new_sec))

# ---------- 6) masterpage(러닝헤더) 중간→기말 ----------
patched = {'Contents/section0.xml': new_sec.encode('utf-8')}
try:
    mp = zin.read('Contents/masterpage0.xml').decode('utf-8')
    if '중간고사' in mp:
        mp = mp.replace('중간고사', '기말고사')
        patched['Contents/masterpage0.xml'] = mp.encode('utf-8')
        print('masterpage 러닝헤더 기말 반영')
except KeyError:
    pass
try:
    pv = zin.read('Preview/PrvText.txt').decode('utf-8')
    pv = pv.replace('중간고사', '기말고사').replace('2026년 5월 6일', '2026년 7월 6일')
    patched['Preview/PrvText.txt'] = pv.encode('utf-8')
except KeyError:
    pass

# ---------- 7) 클론 ZIP 작성(나머지 엔트리 보존) ----------
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
    # mimetype은 비압축 STORED로 먼저
    info = zin.getinfo('mimetype')
    zout.writestr(info, zin.read('mimetype'), compress_type=zipfile.ZIP_STORED)
    for n in zin.namelist():
        if n == 'mimetype':
            continue
        data = patched.get(n, zin.read(n))
        zout.writestr(n, data)
print('WROTE', OUT, os.path.getsize(OUT), 'bytes')
