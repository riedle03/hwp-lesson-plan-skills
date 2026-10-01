# HWPX 형식 차원 체크리스트 (40+ 항목)

매번 "한 번에 못 가져오고 꼭 놓치는" 항목들의 박제. STEP 1에서 **전부 조사**, STEP 3에서 **전부 PASS/FAIL 점검**. 각 항목은 "왜 놓치면 문제인지 + 어떻게 측정/수정하는지"를 담는다.

---

## A. 생성 방식 (가장 큰 함정)
- [ ] **A1. 클론 방식인가?** markdownToHwpx·새 문서 생성이 아니라 템플릿 ZIP을 열어 `section0.xml` 본문만 치환했는가. (FAIL 시: 헤더표·테두리·단 전부 사라짐)
- [ ] **A2. header.xml 바이트 동일?** md5(template) == md5(output). (폰트·줄간격·테두리 정의 보존 증명)
- [ ] **A3. content.hpf 바이트 동일?**
- [ ] **A4. mimetype을 ZIP_STORED로 먼저 기록**했는가(압축 금지).
- [ ] **A5. 나머지 ZIP 엔트리 모두 보존**(이미지·설정 등).

## B. 스타일 ID 일치 (요소별로 템플릿과 동일하게)
- [ ] **B1. 사용한 모든 paraPrIDRef가 header.xml에 정의**되어 있는가.
- [ ] **B2. 사용한 모든 charPrIDRef가 정의**되어 있는가.
- [ ] **B3. 요소 유형별 스타일이 템플릿과 동일**한가 — 제목/지문군 헤더(첫·이후 다를 수 있음)/발문(번호·본문·부정어 강조)/선택지/지문/저작권/끝표시. (템플릿에서 같은 유형의 표/문단을 찾아 그 ID를 그대로 써라)
- [ ] **B4. 폰트·크기·줄간격이 정의에서 동일**(header.xml 바이트 동일이면 자동 보장; ID만 맞으면 됨).

## C. 표(table) 조판 — 평문 문단으로 떨구지 마라
- [ ] **C1. 표여야 할 것을 표로** 만들었는가. 선택지·지문·보기 등이 템플릿에서 표면 출력도 표여야 한다. (FAIL 빈발: 선택지를 `<hp:p>` 평문으로 출력)
- [ ] **C2. 표 속성 일치**: `rowCnt/colCnt`, `borderFillIDRef`(표)·셀 `borderFillIDRef`, `cellSpacing`, `outMargin/inMargin`, `cellMargin`.
- [ ] **C3. treatAsChar(글자처럼 취급)**: 인라인 표는 `"1"`(SQUARE), 본문 위아래로 흐르는 박스(지문 등)는 `"0"`(TOP_AND_BOTTOM). 템플릿 각 표의 값을 그대로. (FAIL 시: 지문 박스가 다음 내용과 겹침)
- [ ] **C4. textWrap**: SQUARE / TOP_AND_BOTTOM 등 템플릿대로.
- [ ] **C5. pageBreak**: 긴 표(지문)는 `"CELL"`(쪽 경계에서 셀 나눔 → 페이지 밖 이탈 방지). 짧은 표는 템플릿대로(`TABLE`/`NONE`). (FAIL 시: 긴 지문이 페이지 밖으로 나감)
- [ ] **C6. 표 id 유일성**: 몰드를 재사용하면 `<hp:tbl id="...">`가 중복된다 → 매 표마다 유일 id로 치환. (중복 시 한글이 오작동 가능)
- [ ] **C7. 표를 문단으로 감싸기**: `<hp:p ...><hp:run ...><hp:tbl>…</hp:tbl><hp:t/></hp:run>{lineseg}</hp:p>` 형태로 본문에 배치.

## D. 셀·문단 내부 줄바꿈 (★ 한글은 linesegarray를 재계산하지 않는다 — 반복 버그)
> **거짓 통념 폐기**: "한글은 열 때 본문 문단·자동확장 셀을 reflow하고, 고정높이 셀만 cram된다"는 **틀렸다**. 한글은 저장된 `<hp:linesegarray>`를 **그대로 신뢰**하며 줄 레이아웃을 재계산하지 **않는다**. 따라서 **모든 종류의 문단·셀**(본문·자동확장·고정높이 무관)에서, 한 줄을 넘는 텍스트에 `<hp:lineseg>`가 1개뿐이면 한글에서도 **한 줄로 cram되어 셀/페이지 폭을 넘쳐 깨진다**. rhwp render도 한글과 동일하게 동작하므로 이를 오라클로 탐지할 수 있다.
- [ ] **D1. 채운 모든 문단의 다줄 처리(예외 없음)**: 텍스트의 글자 디스플레이 폭(한글·전각·원문자=2, ASCII·공백=1)으로 줄 수를 계산해 **줄마다 `<hp:lineseg>`를 재생성**한다. 한 줄 용량 = `horzsize / (vertsize/2)` (≈ 한글 글자폭 1em). 한 줄에 들어가면 그대로 두되, 넘으면 반드시 분할. (FAIL 빈발: 채운 셀의 긴 문장이 1줄로 겹쳐 페이지 밖으로 흘러나감 — 사용자가 "글자 많은데 한 줄로 압축됐다"고 보고하는 바로 그 증상)
- [ ] **D1b. horzsize는 셀 기하에서 계산(★ stored 값 불신)**: `horzsize = cellSz.width − cellMargin.left − cellMargin.right − 문단 horzpos`. 채우기 도구가 모든 셀에 **컬럼 폭과 무관한 일괄 horzsize**(예: 40000)를 박아둘 수 있다 → narrow 컬럼에서 한 줄에 과다 글자 → 셀/페이지 넘침. 이때는 줄바꿈뿐 아니라 **horzsize 자체를 셀 폭으로 교정**해야 한다. (검증: lineseg horzsize ≈ cellSz.width − 좌우 margin 인가)
- [ ] **D2. lineseg 파라미터**: 첫 줄 `flags=393216`(0x60000), 이후 줄 `flags=1441792`(0x160000), `vertpos=vertpos0+줄×step`(`step = vertsize + spacing`), `textpos=줄 시작 글자 index`, `horzsize=D1b로 계산한 셀 폭`. vsize·baseline·spacing·horzpos는 원래 lineseg 승계. → 레시피 §4 `wrap_starts`/`lineseg` 생성기 사용.
- [ ] **D3. 셀·표 높이 보정**: 줄 수가 늘면 enclosing `<hp:tc>`의 `<hp:cellSz height>`를 `+ (줄수-1)*step` 만큼 키우고, enclosing `<hp:tbl>`의 `<hp:sz height>`도 같은 양만큼 키운다. (한글이 셀 높이를 재계산해 줄 가능성도 있으나, 저장값을 신뢰하는 경우 텍스트가 셀 하단에서 잘리는 것을 막기 위해 명시적으로 키운다.)
- [ ] **D4. 검증**: 채운 문단 중 "디스플레이 폭 > horzsize 한 줄 용량 && lineseg 1개"가 **0건**(레시피 §8 스니펫). rhwp render→SVG 글자 x좌표 max ≤ 페이지/셀 텍스트 폭.

## E. 박스 종류 구분 (지문 vs 보기 vs 노치 프레임)
- [ ] **E1. 지문 박스 = 헤더 없는 테두리표**(borderFill 본문용), 내부 지문 스타일 문단.
- [ ] **E2. 정식 `<보기>` = 장식 노치 프레임**: 상단 테두리에 "보기"가 끼인 둥근 박스. 템플릿의 노치 프레임 표를 **그대로 몰드 복제**하고 본문 셀 `<hp:subList>` 내용(템플릿 인트로+그리드)만 새 내용으로 치환. **단순 "보 기" 텍스트 한 줄 추가는 오답** — 표 구조 헤더여야 한다. (분할 주의: subList 시작에서 자르지 않고 첫 `<hp:p>`에서 자르면 템플릿 인트로 텍스트가 잔존)
- [ ] **E3. 보기 vs plain칸 구분 규칙(★사용자 실측 기준)**: 판별 기준은 "박스 **내부에 답지가 고르거나 배열하는 항목**(㈎㈏㈐·㉠㉡㉢㉣ 등)이 있는가".
  - **있으면 → 정식 `<보기>` 노치 헤더 박스**(boxpara). 예: 배열형(㈎~㈑ 순서), 짝짓기형(㈎~㈐), 묶음형(㉠~㉣ 중 고르기). 발문이 보기를 직접 호명("<보기>의 ㈎~㈑를…").
  - **없으면(참고 자료·관점·비평·토론 지문·조건문 등 그냥 읽고 적용하는 글) → 라벨 '없는' plain 테두리 칸**(refbox; "보기"란 말 금지). **이때 발문도 "다음 글을/다음을 참고하여/다음 토론에서"로 받는다 — "`<보기>`를/의"라고 쓰면 라벨 없는 박스와 어긋나니 같이 고친다.**
  - ⚠️ **흔한 버그**: 배열형·묶음형의 ㈎㈑·㉠㉣를 `<보기>`로 안 묶으면 빌드가 지문 버퍼로 처리해 **선택지 '뒤'에** 떨어져 배치되고 라벨도 없다. `<보기>`로 묶어야 발문 바로 다음(선택지 앞)에 정상 배치된다.
  - 구현: 노치=boxpara(BOGI 몰드), plain=refbox(BOX 단일셀 몰드·paraPr29·treatAsChar=1·`_ref_h` 높이). md 마커는 `<보 기>` / `<자료>`로 구분.
- [ ] **E4. 박스 내부 문단 스타일**(paraPr/charPr)이 템플릿 박스와 동일.

## F. 강조·표시 장치
- [ ] **F1. 밑줄(±볼드) span**: md엔 밑줄이 없으니 `<u>…</u>` 관례 → 밑줄 charPr(템플릿에서 underline=BOTTOM인 charPr; 보통 본문 charPr+밑줄 변형)로, 나머지는 일반 charPr로 run 분할. 지문 마커(㉠㉡·ⓐⓑ)가 가리키는 **구간 전체**를 `<u>`로(마커 기호는 밖). (FAIL 시: 마커만 있고 밑줄 없어 학생이 범위 모름)
  - **볼드 동시 적용**(가독성 요청 시): 본문 charPr에 `<hh:underline type="BOTTOM".../>`+`<hh:bold/>`를 더한 새 charPr를 만들어 ucp로 쓴다. **height(폰트 크기)는 본문 charPr 그대로 유지** — 밑줄만/볼드만 바꾸고 크기는 건드리지 말 것.
- [ ] **F1b. ⚠️ 새 charPr는 리스트 '맨 끝'(위치==id)에 추가**: header.xml `<hh:charProperties>`에 charPr를 새로 만들면 **반드시 `</hh:charProperties>` 직전**에 붙이고 `itemCnt`를 +1, id는 직전 최대+1. **중간 삽입 금지**(예: charPr31 바로 뒤). 한글은 `charPrIDRef`를 **위치 인덱스**로 해석하므로 id를 위치와 어긋나게 끼우면 `charPrIDRef="N"`이 **위치 N의 엉뚱한 charPr**(예: height 800 무장식)를 가리켜 한글에서 **8pt·밑줄/볼드 소실**로 렌더된다(실측 버그). 가드: `_ids==list(range(itemCnt))` assert. (rhwp 렌더는 id 속성으로 찾아 정상이라 PNG로는 못 잡음 → 한글 육안 또는 위 assert 필수)
- [ ] **F2. 정답 표시(출제원안)**: 정답 선택지 번호에 형광펜 `<hp:markpenBegin color="#FFFF00"/>번호 <hp:markpenEnd/>`. 정답은 [교사용] 정답표 등 단일 출처에서 읽어 매칭.
- [ ] **F3. 부정어 강조**: 발문의 '않은/없는/아닌' 등을 강조 charPr로.
- [ ] **F4. 기타 템플릿 고유 강조**(굵게·색·markpen 흰색 등) 누락 없는지.

## G. 페이지·쪽 넘김
- [ ] **G1. 페이지 기하 반영**: 용지 크기(예 B4 72852×103180)·여백·단 수. 용량 = 2단×단높이.
- [ ] **G2. 쪽 넘김 안내(양면 인쇄)**: 홀수쪽 `---뒷면에 계속---`, 짝수쪽 `---뒷장에 계속---`(중앙정렬). **본문에 넣음**(꼬리말 아님). 동적 페이지라 위치를 모르므로 **요소 높이 누적 추적 + keep-together(문항·세트 덩어리 유지) + 강제 쪽나누기(`pageBreak="1"`)**. (FAIL: 안내 누락 / 표가 쪽 중간에서 미표시 분할)
- [ ] **G3. keep-together**: 문항(발문+보기+선택지)·세트오프너(지문군+지문)를 덩어리로, 현재 쪽에 안 들어가면 통째로 넘김.
- [ ] **G4. CAP 마진**: 실용량보다 ~15~20% 보수적으로(높이 추정 오차로 한글에서 1쪽 초과 안 되게). **최종 위치는 한글 육안 확인 필요**(rhwp 검증 불가).
- [ ] **G5. 끝 표시**: 마지막 `-끝-` 문단(템플릿 스타일). 마지막 쪽엔 계속 안내 없음.

## H. 메타·머리말·꼬리말
- [ ] **H1. head 메타 치환**: 제목(중간↔기말 등)·날짜·문항수·범위 — head 영역 문자열 치환.
- [ ] **H2. masterpage(러닝헤더) 치환**·**Preview/PrvText 치환**.
- [ ] **H3. 꼬리말(저작권 등) 보존**(건드리지 않음).
- [ ] **H4. 본문 치환 경계 정확**(※안내 직후 ~ -끝- 등, 머리말/꼬리말 보존).

## I. 검증
- [ ] **I1. well-formed**: `ET.fromstring(section0.xml)` 예외 없음.
- [ ] **I2. 카운트 일치**: 표 수·문항 수·선택지 수·정답표 행·밑줄 run·형광펜 = 기대값.
- [ ] **I3. 배점/내용 보존**: 배점 합계 등 수치가 원안과 일치.
- [ ] **I4. 독립 파서 라운드트립**: `npx --yes k-skill-rhwp info <file>`로 @rhwp/core가 정상 파싱(hwpx 입력 OK).
- [ ] **I5. 렌더 육안**: `k-skill-rhwp render <file> --page N --format svg`(stdout) → `sharp(svg,{density:150}).png()` 래스터화(node_modules의 sharp 사용) → PNG 직접 열기. **표/박스/단 조판·밑줄·형광펜·줄바꿈은 확인 가능**(rhwp는 한글과 동일하게 linesegarray를 따른다 — single-lineseg cram도 한글과 똑같이 재현하므로 **줄바꿈 깨짐 탐지의 오라클**). **페이지 넘김 위치만 불가**.
- [ ] **I6. 줄바꿈 cram 자동검증(★)**: render SVG의 모든 `<text>` 글자 x좌표를 추출 → 어떤 글자도 **페이지 텍스트 폭(SVG width)·셀 텍스트 폭을 넘지 않아야** PASS. 한 행(y)에 글자가 페이지 폭 밖(예: maxx ≫ pageWidth)으로 뻗으면 그 문단은 single-lineseg cram 상태(레시피 §8). + 정적 검사: "디스플레이 폭 > horzsize/(vertsize/2) && lineseg 1개" 문단 0건.
- [ ] **I7. 한글 최종 육안**: 페이지 넘김 위치·형광펜 색·노치 헤더는 **사용자가 한글에서** 확인(headless 한계). 줄바꿈·셀폭은 I5/I6로 이미 검증됨.

---

## 측정 스니펫 (Python, 템플릿 분석용)
```python
import zipfile, re, hashlib
z = zipfile.ZipFile('template.hwpx')
sec = z.read('Contents/section0.xml').decode('utf-8')
# 표 종류 열거
for m in re.finditer(r'<hp:tbl\b[^>]*>', sec):
    a = m.group(0)
    nxt = re.sub(r'<[^>]+>', '', sec[m.end():m.end()+400]).strip()[:30]
    g = lambda k: (re.search(k+r'="(\w+)"', a) or [None, '?'])[1]
    print(g('rowCnt'), g('colCnt'), 'bf='+g('borderFillIDRef'),
          'tac='+g('treatAsChar'), g('textWrap'), 'pb='+g('pageBreak'), '|', nxt)
# 스타일 정의(밑줄 charPr 찾기)
hdr = z.read('Contents/header.xml').decode('utf-8')
for m in re.finditer(r'<hh:charPr id="(\d+)".*?</hh:charPr>', hdr, re.S):
    ul = '밑줄' if '<hh:underline' in m.group(0) and 'NONE' not in (re.search(r'underline[^>]*type="(\w+)"', m.group(0)) or ['','NONE'])[1] else ''
    print('charPr', m.group(1), ul)
# 페이지 기하
print(re.search(r'<hp:pagePr[^>]*>', sec).group(0))
print(re.search(r'<hp:margin[^>]*>', sec).group(0))
print((re.search(r'<hp:colPr[^>]*>', sec) or ['?'])[0] if re.search(r'<hp:colPr[^>]*>', sec) else '단정보 없음')
```
