# OWPML 추출·치환·생성기 레시피 (범용)

템플릿에 맞춰 앵커·스타일 ID·치수만 바꾸면 어떤 양식에도 적용되는 코드 패턴. 완성 예시는 `references/example-build-exam.py`(정기고사 출제원안). 아래는 그 일반화.

## 0. 클론 골격
```python
import zipfile, re, os
from xml.sax.saxutils import escape as _esc
import xml.etree.ElementTree as ET

TEMPLATE, OUT = 'template.hwpx', 'output.hwpx'
zin = zipfile.ZipFile(TEMPLATE)
sec = zin.read('Contents/section0.xml').decode('utf-8')

def esc(t): return _esc(t)   # 필요 시 markdown escape 해제 추가

# ... 몰드 추출 + 본문 생성(MYBODY) ...

# 본문 경계 치환(예: ※안내 직후 ~ -끝-)
body_start = sec.find('</hp:p>', sec.find('OMR')) + len('</hp:p>')
body_end   = sec.find('</hp:p>', sec.find('-끝-')) + len('</hp:p>')
head, tail = sec[:body_start], sec[body_end:]
head = head.replace('1학기 중간고사', '1학기 기말고사')  # 메타 치환(템플릿마다 조정)
new_sec = head + MYBODY + tail
ET.fromstring(new_sec)   # well-formed 검증

# 기타 엔트리 메타 치환
patched = {'Contents/section0.xml': new_sec.encode('utf-8')}
for n in ('Contents/masterpage0.xml', 'Preview/PrvText.txt'):
    try:
        t = zin.read(n).decode('utf-8').replace('중간고사', '기말고사')
        patched[n] = t.encode('utf-8')
    except KeyError: pass

with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
    zout.writestr(zin.getinfo('mimetype'), zin.read('mimetype'), compress_type=zipfile.ZIP_STORED)
    for n in zin.namelist():
        if n != 'mimetype':
            zout.writestr(n, patched.get(n, zin.read(n)))
```

## 1. 표 id 유일화
```python
_tid = [1000]
def _newid():
    _tid[0] += 1; return str(_tid[0])
def _uid(xml):   # 표 조각 첫 <hp:tbl id="..."> 유일화
    return re.sub(r'(<hp:tbl id=")\d+', lambda m: m.group(1)+_newid(), xml, count=1)
```

## 2. 중첩 표 경계 찾기(보기 노치 프레임 등)
```python
def tbl_end(s, ts):           # ts=<hp:tbl 시작, 중첩 고려한 </hp:tbl> 끝 반환
    depth, p = 0, ts
    while True:
        no, nc = s.find('<hp:tbl', p+1), s.find('</hp:tbl>', p+1)
        if nc == -1: return -1
        if no != -1 and no < nc: depth += 1; p = no
        else:
            if depth == 0: return nc + len('</hp:tbl>')
            depth -= 1; p = nc
```

## 3. 장식 박스 몰드(예: <보기> 노치 프레임) — 본문 셀 subList만 치환
```python
i = sec.find('앵커텍스트')           # 그 양식의 보기 박스 안 텍스트
frame = sec[sec.rfind('<hp:tbl', 0, i):tbl_end(sec, sec.rfind('<hp:tbl', 0, i))]
nest = frame.find('<hp:tbl', 5)      # 프레임 안의 내용 표
nest_e = tbl_end(frame, nest)
btc = frame.rfind('<hp:tc', 0, nest)             # 내용 표를 품은 본문 셀
sl_start = frame.find('>', frame.find('<hp:subList', btc)) + 1   # ★ subList 내용 시작에서 자른다
sl_close = frame.find('</hp:subList>', nest_e)                   #   (첫 <hp:p>에서 자르면 인트로 잔존!)
HEAD, TAIL = frame[:sl_start], frame[sl_close:]
def make_box(content_paras):
    return _uid(HEAD + content_paras + TAIL)
```

## 4. 줄바꿈 lineseg 생성기 (★ 모든 텍스트 주입에 필수 — 한글 cram 방지)
> 한글은 `<hp:linesegarray>`를 **재계산하지 않고 그대로 신뢰**한다. 기존 셀에 텍스트를 채우든 새 표를 만들든, **한 줄을 넘는 모든 문단**은 이 생성기로 줄마다 `<hp:lineseg>`를 만들어야 한다. single-lineseg를 남기면 한글·rhwp 모두 한 줄로 cram되어 셀/페이지 폭을 넘쳐 깨진다("글자 많은데 한 줄로 압축" 증상). 한 줄 용량 ≈ `horzsize / (vertsize/2)` (한글 글자폭 1em). **★ horzsize는 저장된 lineseg 값을 믿지 말고 enclosing 셀 기하에서 계산하라**: `horzsize = cellSz.width − cellMargin.left − cellMargin.right − 문단 horzpos`. (자주 나는 함정: 채우기 도구가 모든 셀에 **컬럼 폭과 무관한 일괄 horzsize**(예: 40000)를 박아두면, narrow 컬럼 텍스트가 한 줄에 너무 많이 들어가 셀/페이지를 넘친다 — 단순 줄바꿈만으론 못 고치고 horzsize 자체를 셀 폭으로 교정해야 한다.) vsize·baseline·spacing·horzpos는 원래 lineseg에서 승계, `step = vertsize + spacing`. 줄 수가 늘면 §5처럼 `<hp:cellSz height>`·`<hp:tbl><hp:sz height>`를 `+(줄수-1)*step` 키운다.
```python
def disp_w(c): return 2 if ord(c) > 0x2000 else 1     # 한글·전각·원문자=2
def wrap_starts(text, limit):                          # limit=줄당 디스플레이폭
    st, w = [0], 0
    for i, c in enumerate(text):
        cw = disp_w(c)
        if w + cw > limit and i > st[-1]: st.append(i); w = 0
        w += cw
    return st
def lineseg(text, limit, step, vsize, baseline, spacing, horzpos, horzsize):
    st = wrap_starts(text, limit)
    segs = ''.join(
        f'<hp:lineseg textpos="{tp}" vertpos="{j*step}" vertsize="{vsize}" textheight="{vsize}" '
        f'baseline="{baseline}" spacing="{spacing}" horzpos="{horzpos}" horzsize="{horzsize}" '
        f'flags="{"393216" if j==0 else "1441792"}"/>' for j, tp in enumerate(st))
    return '<hp:linesegarray>'+segs+'</hp:linesegarray>', len(st)
# 파라미터(step/vsize/baseline/spacing/horzsize)는 템플릿의 같은 유형 셀에서 실측해 그대로.
```

## 5. N행1열 표 생성기(예: 선택지) — 줄수 반영 셀높이
```python
def rowcol_table(cells, tbl_bf, cell_bf, parapr, charpr, width, limit, lineh1=2232, step=1432,
                 answer=None):
    trs, total = '', 0
    for i, txt in enumerate(cells):
        lseg, n = lineseg(txt, limit, step=step, vsize=1100, baseline=935, spacing=332,
                          horzpos=500, horzsize=width-784)
        h = lineh1 + (n-1)*step; total += h
        t = (f'<hp:markpenBegin color="#FFFF00"/>{esc(txt[:2])}<hp:markpenEnd/>{esc(txt[2:])}'
             if answer and txt[:1]==answer else esc(txt))     # 정답 형광펜
        trs += (f'<hp:tr><hp:tc borderFillIDRef="{cell_bf}"><hp:subList vertAlign="CENTER" lineWrap="BREAK">'
                f'<hp:p paraPrIDRef="{parapr}"><hp:run charPrIDRef="{charpr}"><hp:t>{t}</hp:t></hp:run>{lseg}</hp:p>'
                f'</hp:subList><hp:cellAddr colAddr="0" rowAddr="{i}"/><hp:cellSpan colSpan="1" rowSpan="1"/>'
                f'<hp:cellSz width="{width}" height="{h}"/><hp:cellMargin left="141" right="141" top="566" bottom="566"/></hp:tc></hp:tr>')
    tbl = (f'<hp:tbl id="{_newid()}" numberingType="TABLE" textWrap="SQUARE" pageBreak="CELL" repeatHeader="1" '
           f'rowCnt="{len(cells)}" colCnt="1" cellSpacing="0" borderFillIDRef="{tbl_bf}">'
           f'<hp:sz width="{width}" widthRelTo="ABSOLUTE" height="{total}" heightRelTo="ABSOLUTE"/>'
           f'<hp:pos treatAsChar="1" .../>...{trs}</hp:tbl>')   # 속성은 템플릿 표에서 복사
    return f'<hp:p paraPrIDRef="10"><hp:run charPrIDRef="8">{tbl}<hp:t/></hp:run>{LSEG}</hp:p>'
# ※ tc/tbl의 생략된 속성(name/header/protect/pos 등)은 템플릿 표 속성 문자열을 그대로 복사할 것.
```

## 6. 밑줄 run 분할(<u>…</u> → 밑줄 charPr)
```python
def runs(text, ncp, ucp):       # ncp=일반 charPr, ucp=밑줄 charPr
    out = []
    for seg in re.split(r'(<u>.*?</u>)', text):
        if not seg: continue
        if seg.startswith('<u>'):
            out.append(f'<hp:run charPrIDRef="{ucp}"><hp:t>{esc(seg[3:-4])}</hp:t></hp:run>')
        else:
            out.append(f'<hp:run charPrIDRef="{ncp}"><hp:t>{esc(seg)}</hp:t></hp:run>')
    return ''.join(out)
# 줄나눔 길이 계산은 re.sub(r'</?u>','',text)로 태그 제거 후 수행.
```

### 6b. 밑줄+볼드 charPr 신설(가독성 마커) — ⚠️ 반드시 리스트 맨 끝에 추가
```python
# 본문 밑줄 charPr(예: id=31 = 본문 charPr30 + underline BOTTOM)를 복제 +<hh:bold/> → 새 id.
# 핵심: header.xml charPr는 '위치==id'로 참조된다(한글). 중간 삽입 금지, 맨 끝에만 추가.
import xml.etree.ElementTree as ET
hdr = zin.read('Contents/header.xml').decode('utf-8')
maxid = max(int(x) for x in re.findall(r'<hh:charPr id="(\d+)"', hdr))   # 예: 52
newid = maxid + 1                                                        # 53
src = re.search(r'<hh:charPr id="31".*?</hh:charPr>', hdr, re.S).group(0)
new = src.replace('id="31"', f'id="{newid}"', 1).replace('<hh:underline', '<hh:bold/><hh:underline', 1)
hdr = hdr.replace('</hh:charProperties>', new + '</hh:charProperties>', 1)   # ← 맨 끝!
hdr = re.sub(r'(<hh:charProperties itemCnt=")(\d+)(")',
             lambda m: m.group(1)+str(int(m.group(2))+1)+m.group(3), hdr, 1)
ET.fromstring(hdr)
ids = [int(x) for x in re.findall(r'<hh:charPr id="(\d+)"', hdr)]
assert ids == list(range(newid+1)), 'charPr id!=position 깨짐 → 한글 8pt 버그'   # 가드
patched['Contents/header.xml'] = hdr.encode('utf-8')
# 그다음 runs(text, ncp, ucp=newid)로 <u>span을 밑줄+볼드로. height(크기)는 본문 그대로 유지됨.
```
- bold/underline 자식 순서는 `<hh:bold/><hh:underline .../>`(offset 뒤) — 한글 네이티브와 동일하므로 순서 자체는 무해하나, **위치==id가 진짜 원인**. 중간 삽입 시 한글이 마커를 8pt·밑줄/볼드 소실로 렌더(rhwp PNG로는 못 잡힘).

## 7. 본문 인라인 페이지네이션(쪽 넘김 안내)
```python
# CAP=한 쪽 용량(2단×단높이)보다 ~15~20% 보수적. 요소를 (xml,height) 단위로 모아 keep-together.
cum, page, out = 0, 1, []
def pagebreak():                # 현재 쪽 하단 안내 + 다음 요소 강제 새 쪽
    global cum, page
    txt = '---뒷면에 계속---' if page % 2 == 1 else '---뒷장에 계속---'   # 홀=뒷면, 짝=뒷장
    out.append(center_para(txt)); out.append('<<PB>>'); cum = 0; page += 1
def emit_unit(parts):           # parts=[(xml,h)…] 한 덩어리(문항/세트오프너)
    global cum
    uh = sum(h for _, h in parts)
    if cum > 0 and cum + uh > CAP: pagebreak()
    for xml, _ in parts: out.append(xml)
    cum += uh
# 마지막에 <<PB>> 센티넬 → 다음 요소 첫 문단 pageBreak="0"→"1"로 치환.
# ★ 페이지 경계 최종 위치는 한글 육안 확인(rhwp는 cram해서 검증 불가).
```

## 8. 검증
```python
ET.fromstring(new_sec)                                  # well-formed
import hashlib
for n in ('Contents/header.xml','Contents/content.hpf'):
    assert hashlib.md5(zin.read(n)).hexdigest() == hashlib.md5(zout_read(n)).hexdigest()
# 카운트: 표 수, 문항/선택지/정답/밑줄 run, 표 id 유일성

# ★ 줄바꿈 cram 정적 검사: "디스플레이폭 > 한 줄 용량인데 lineseg 1개" 문단 0건이어야 PASS
def _dispw(c): return 2 if ord(c) > 0x2000 else 1
def cram_paras(section_xml):
    bad = []
    for p in re.findall(r'<hp:p\b.*?</hp:p>', section_xml, re.S):
        segs = re.findall(r'<hp:lineseg\b[^>]*/?>', p)
        if len(segs) != 1: continue
        t = re.sub('<[^>]+>', '', ''.join(re.findall(r'<hp:t>(.*?)</hp:t>', p, re.S)))
        if not t.strip(): continue
        s = segs[0]; gi = lambda n: int((re.search(n+r'="(\d+)"', s) or [0,'0'])[1])
        hz, vz = gi('horzsize'), gi('vertsize')
        if hz and vz and sum(_dispw(c) for c in t) > hz/(vz/2):
            bad.append(t[:30])
    return bad
assert not cram_paras(new_sec), ('CRAM: single-lineseg 긴 문단 발견 → §4로 재생성', cram_paras(new_sec))

# 렌더 + cram 오라클(rhwp는 한글과 동일하게 linesegarray를 따름):
#   npx --yes k-skill-rhwp render out.hwpx --format svg > p.svg
#   → 모든 <text x=..> 글자의 max x가 <svg width>(페이지 텍스트폭) 이내인지 검사. 넘으면 그 행이 cram.
#   → sharp(svg,{density:150}).png().toFile('p.png')로 표/박스/단/밑줄/형광펜·줄바꿈 육안.
#   → 쪽 넘김 위치만 한글에서.
```

## 단위(HWPUNIT) 메모
- 1pt = 100 HWPUNIT, 1inch = 7200, 1mm ≈ 283.46.
- 예: B4 = 72852×103180(257×364mm). charPr 11.48pt → 폭/높이 ≈ 1148.
- 줄간격은 paraPr의 lineSpacing PERCENT(예 180%) → step ≈ 글자높이×배율.
