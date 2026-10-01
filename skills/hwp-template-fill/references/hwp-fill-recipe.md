# `.hwp` 양식 채우기 레시피 (rhwp-edit / k-skill-rhwp)

`.hwp`(바이너리)는 ZIP 클론이 안 되므로 **제자리 편집**으로 칸을 채운다. 원본은 그대로 두고 항상 **새 파일로 저장**. 출력도 `.hwp`(입력=출력 철칙). 도구: `k-skill-rhwp`(npx, 설치 불필요).

## 0. 전제·한계
- **HWPX 저장 불가(#196)** → 입력 `.hwp` → 출력 `.hwp`만. (그래서 `.hwp`엔 이 경로가 맞다)
- `set-cell-text` = 셀을 **텍스트**로 채움(셀 안 굵게·글머리표·여러 단락은 제어 약함).
- `replace-all`/`search` = **본문 문단만** 스캔(표 셀·머리말/꼬리말·각주 제외) → 셀은 반드시 `set-cell-text`.
- 베타: 복잡 표·이미지·양식필드 많으면 round-trip 드물게 손실 → 편집 후 `render` 확인.

## 1. 구조 파악 (좌표 뽑기)
```bash
npx --yes k-skill-rhwp info  "양식.hwp"            # sourceFormat·섹션·문단 수·길이
npx --yes k-skill-rhwp list-paragraphs "양식.hwp"  # 문단/표/셀 좌표 확인
```
- 표 셀 좌표 = `--section N --parent-paragraph N --control N --cell N [--cell-paragraph N]`.
- 본문 검색: `npx --yes k-skill-rhwp search "양식.hwp" --query "기존문구"` → 섹션/문단/오프셋.

## 2. 채우기 (항상 --output 새 파일)
```bash
# 본문 문단 텍스트 치환(같은 서식 유지) — 본문만
npx --yes k-skill-rhwp replace-all ./양식.hwp ./out/step1.hwp \
  --query "○○○" --replacement "2026학년도 1학기"

# 표 셀 채우기 — 좌표 지정(셀 텍스트 교체)
npx --yes k-skill-rhwp set-cell-text ./out/step1.hwp ./out/step2.hwp \
  --section 0 --parent-paragraph <paraIdx> --control <ctrlIdx> --cell <cellIdx> \
  --text "물질의 상태 변화"

# 본문 특정 위치에 줄 삽입
npx --yes k-skill-rhwp insert-text ./out/step2.hwp ./out/step3.hwp \
  --section 0 --paragraph 0 --offset 0 --text "..."
```
- 셀을 연속으로 채울 땐 **직전 출력 파일을 다음 입력**으로 체이닝(step1→step2→…).
- 기존 셀 내용 보존하며 덧붙이려면 `set-cell-text --no-replace`.

## 2-0. ★ 편집 전에 반드시 — 무편집 round-trip 손실 검사 (2026-08-13 실측)

**rhwp는 한글이 만든 일부 문서를 무손실로 다시 저장하지 못한다.** 그리고 `getValidationWarnings()`는
0건을 반환하고 `exportHwpVerify()`도 `recovered:true`를 주므로, **rhwp의 자체 검증으로는 못 걸러진다.**
한글에서 열어야 비로소 "파일이 손상되었습니다"가 뜬다.

그래서 **어떤 편집이든 하기 전에, 아무것도 고치지 않고 저장만 해 크기를 비교한다.**
```js
const doc = await loadDocument(src);
const w = writeHwp(doc, tmp);          // 편집 0건
// before === w.bytesWritten 이어야 편집 가능
```
실측: 사용자가 한글에서 **중첩 표(셀 안의 표)** 를 만들어 넣은 파일은
107,008 → 96,256 bytes(**-10%**). 같은 파이프라인이 생성한(중첩 표 없는) 파일은 93,184 → 93,184(**0%**).
즉 손실은 편집 때문이 아니라 **재직렬화 자체**에서 났고, 중첩 표가 유력한 트리거다.

**손실이 0이 아니면 rhwp로 그 파일을 편집하지 마라.** 대안 두 가지:
1. 수정할 문단을 위치와 함께 사용자에게 전달해 **한글에서 직접 붙여넣게** 한다(위험 0).
2. 원본 md에서 파일을 새로 생성한다. 단 사용자가 한글에서 손수 만든 서식(중첩 표·셀 서식)은 재현되지 않는다.

교훈: 사용자가 한글로 손댄 파일은 **그 파일이 서식의 원본**이다. 도구가 그것을 보존하지 못하면
도구를 쓰지 않는 편이 맞다. 백업이 있어도 사용자의 시간은 되돌아오지 않는다.

## 2-1. CLI로는 부족할 때 — Node API 실측 노트 (2026-08-13)

`k-skill-rhwp` CLI의 `set-cell-text`는 **셀당 한 문단**만 다룬다. 강의 원고처럼 한 셀에
수백 줄이 들어가는 양식은 CLI만으로는 못 채운다. Node API를 직접 쓰되 아래 세 가지를 지켜야 한다.

**(a) 표 좌표는 `findNearestControlForward`로 훑는다.** `list-paragraphs`는 문단 길이만 주고
표 위치를 알려주지 않는다.
```js
const hit = JSON.parse(doc.findNearestControlForward(sec, para, charPos));
// → {type:"table", sec, para, ci, charPos}  ci가 control 인덱스
const dim = JSON.parse(doc.getTableDimensions(sec, hit.para, hit.ci));
// → {rowCount, colCount, cellCount}   ※ ok 필드가 없다. ok를 기대하면 표를 통째로 놓친다
```

**(b) `getTextInCell`은 offset·count가 필수다.** 빼면 조용히 빈 문자열을 준다(에러가 아니다).
```js
const len = doc.getCellParagraphLength(s, para, ci, cell, cellPara);
const txt = len > 0 ? doc.getTextInCell(s, para, ci, cell, cellPara, 0, len) : "";
```

**(c) 줄바꿈은 `\n`이 아니라 문단 분리로 만든다.** `insertTextInCell`에 `\n`을 넣으면
문단이 나뉘지 않고 **리터럴 문자로 한 문단에 눌려 담긴다**(스킬 본문의 cram 게이트가 잡는 그 현상).
```js
// 기존 내용 비우고 → 필요한 문단 수만큼 split → 한 줄씩 삽입
while (doc.getCellParagraphCount(s, para, ci, cell) < lines.length) {
  const last = doc.getCellParagraphCount(s, para, ci, cell) - 1;
  doc.splitParagraphInCell(s, para, ci, cell, last,
    doc.getCellParagraphLength(s, para, ci, cell, last));
}
lines.forEach((t, i) => t && doc.insertTextInCell(s, para, ci, cell, i, 0, t));
doc.reflowLinesegs();   // 마지막에 1회. 안 하면 한글에서 줄이 눌린 채 열린다
```
본문 문단도 같은 방식이다 — `splitParagraph(sec, para, offset)` / `insertParagraph(sec, para)`.
**본문 구간을 여러 곳 고칠 땐 뒤에서부터(bottom-up)** 해야 앞 구간 편집이 뒤 인덱스를 밀지 않는다.

검증은 (1) `getSourceFormat()`이 `hwp`인지 (2) 슬롯별 기대 문자열이 실제 셀에 있는지
(3) 셀 문단에 리터럴 개행이 0건인지 (4) `renderPageSvg`의 글자 `x` 최대값이 페이지 폭 이내인지
— 네 가지를 스크립트로 돌린다.

## 3. Node API로 다칸 반복 (셀이 많을 때)
좌표·내용 매핑 표(STEP 2의 MD↔셀 맵)를 배열로 두고 순회한다.
```js
const { setCellText, getDocumentInfo } = require("k-skill-rhwp");
const fills = [   // {parentParagraph, control, cell, text}
  { parentParagraph: 3, control: 0, cell: 1, text: "물질의 상태 변화" },
  { parentParagraph: 3, control: 0, cell: 5, text: "3차시" },
  // ...양식 맵 전체
];
let cur = "양식.hwp";
for (const [i, f] of fills.entries()) {
  const out = `./out/fill_${i}.hwp`;
  await setCellText({ input: cur, output: out, section: 0,
    parentParagraph: f.parentParagraph, control: f.control, cell: f.cell, text: f.text });
  cur = out;
}
console.log(await getDocumentInfo(cur));   // 검증
```
- WASM은 첫 호출 1회 초기화. 한국어는 UTF-8 그대로. 좌표 범위 벗어나면 `구역 인덱스 범위 초과` 에러 → `info`로 좌표 재확인.

## 4. 검증
```bash
npx --yes k-skill-rhwp info ./out/최종.hwp                 # 섹션/문단/길이 변화가 의도대로
npx --yes k-skill-rhwp render ./out/최종.hwp --page 0 --format html   # 또는 svg → 육안
```
- `ok:true`·`bytesWritten` 확인. 채운 칸이 다 들어갔는지 render/info로 점검.
- **페이지 넘김·셀 안 리치서식은 한글에서 최종 육안.**

## 5. 셀 리치서식이 꼭 필요할 때
`set-cell-text`로는 굵게/글머리표/여러 단락 제어가 약함 →
- (a) 텍스트만 채우고 **서식은 한글에서 마무리**, 또는
- (b) 사용자 동의하에 한글에서 `.hwpx`로 저장 → `hwpx-format-clone`(OWPML run으로 리치서식) → 다시 `.hwp`로 저장. (입력=출력 철칙이 바뀌므로 동의 필요)
