# Smart Spice LIB Editor

Python과 Tkinter로 만든 Smart Spice `.lib` 모델 파일 편집 GUI 도구입니다.

---

## 주요 기능

- **트리 기반 탐색** — `.LIB` 블록, `.MODEL` 항목, `.PARAM` 변수를 사이드바 트리로 한눈에 파악
- **인라인 셀 편집** — 파라미터 테이블의 셀을 더블클릭하여 이름과 값을 즉시 수정
- **파라미터 추가 / 삭제** — 모델 또는 PARAM 섹션에 새 파라미터를 추가하고, 확인 후 삭제
- **변수(PARAM) 지원** — 파라미터 값을 변수 이름으로 연결하면, 전역 `.PARAM` 선언이 자동으로 추가됨
- **수식 지원** — `{tox_val}`, `{vth_offset * 1.1}` 같은 중괄호 수식을 파라미터 값으로 사용 가능
- **내용 미리보기** — 저장 전 Smart Spice 문법으로 출력될 내용을 팝업으로 확인
- **저장 / 다른 이름으로 저장** — 수정 내용을 원본에 덮어쓰거나 새 경로로 내보냄 (80자 기준 `+` 자동 줄바꿈)

---

## 프로젝트 구조

```
tr-fitting-manual/
├── main.py          # 메인 GUI 애플리케이션 (Tkinter)
├── data_model.py    # 데이터 클래스: LibFile, LibBlock, ModelEntry, ParamEntry
├── lib_parser.py    # .lib 파일 파서
├── lib_writer.py    # 직렬화기 — 데이터 모델을 Smart Spice 문법으로 변환
├── sample.lib       # 테스트용 예제 .lib 파일
└── 사용설명서.md     # 상세 사용 설명서
```

---

## 요구 사항

- Python 3.8 이상
- Tkinter (Python 표준 라이브러리에 포함)

> 별도의 서드파티 패키지 설치가 필요 없습니다.

---

## 실행 방법

```bash
cd tr-fitting-manual
python3 main.py
```

실행 후 툴바의 **📂 파일 열기** 버튼을 클릭하여 `.lib` 파일을 불러옵니다.

---

## 사용법 요약

| 동작 | 방법 |
|---|---|
| `.lib` 파일 열기 | 툴바의 **📂 파일 열기** 클릭 |
| 모델 선택 | 좌측 트리에서 `⚙️ MODEL` 항목 클릭 |
| 파라미터 값 수정 | 셀 더블클릭 → 입력 → `Enter` 확정 / `Esc` 취소 |
| 파라미터 추가 | 모델 또는 PARAMS 노드 선택 후 **＋ 파라미터 추가** 클릭 |
| 파라미터 삭제 | 행 선택 후 **－ 삭제** 클릭 |
| 변수 할당 | 파라미터 행 선택 후 **🔤 변수 → 값 설정** 클릭 |
| 내용 미리보기 | 툴바의 **👁 내용 미리보기** 클릭 |
| 저장 | **💾 저장** (원본 덮어쓰기) 또는 **💾 다른 이름으로 저장** |

---

## 값 색상 코딩

| 색상 | 의미 |
|---|---|
| 🟢 초록 | 숫자 리터럴 (예: `0.45`, `1.2e-8`) |
| 🟡 노랑 | 변수 단순 참조 (예: `{tox_global}`) |
| 🟣 보라 | 산술 수식 (예: `{vth_offset + 0.40}`) |

---

## 출력 파일 형식

편집 후 저장하면 Smart Spice 문법을 유지하며, 긴 줄은 `+` continuation line으로 자동 줄바꿈(80자 기준)됩니다.

```spice
.PARAM tox_global=1.2e-8

.LIB NMOS_LIB
.PARAM vth_offset=0.05
.MODEL NMOS_V1 NMOS
+ LEVEL=3 VTH0=0.45 TOX={tox_global} XJ=1.5e-7
+ K1=0.559 K2=-0.04
.ENDL NMOS_LIB
```

---

## 라이선스

MIT
