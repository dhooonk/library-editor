# lib-editor — CLAUDE.md

> Smart Spice `.lib` 모델 파일 편집 GUI 도구 | Python 3 · Tkinter

---

## 프로젝트 개요

반도체 공정 시뮬레이터(Smart Spice)용 `.lib` 파일을 GUI로 편집하는 데스크탑 애플리케이션입니다.  
텍스트 에디터 없이 파라미터를 트리뷰·테이블로 탐색/수정하고, Excel로 내보낼 수 있습니다.

---

## 폴더 구조

```
lib-editor/
├── src/                    # Python 소스 코드
│   ├── main.py             # 메인 GUI (진입점) — Tkinter 애플리케이션 전체
│   ├── data_model.py       # 데이터 클래스 — LibFile / LibBlock / ModelEntry 등
│   ├── lib_parser.py       # 파서 — .lib 텍스트 → LibFile 객체
│   ├── lib_writer.py       # 직렬화기 — LibFile 객체 → Smart Spice 텍스트
│   └── excel_exporter.py   # Excel 내보내기 — LibFile → .xlsx
├── samples/                # 테스트·예제용 .lib 파일
│   └── sample.lib
├── docs/                   # 문서
│   ├── README.md           # 개발 배경·구현 사항·버전 히스토리
│   └── 사용설명서.md        # 처음 사용하는 분들을 위한 단계별 안내서
├── build.spec              # PyInstaller 빌드 설정
└── CLAUDE.md               # 이 파일 — 프로젝트 구조 및 개발 가이드
```

---

## 아키텍처

```
.lib 파일
   │
   ▼
lib_parser.py  ──parse_lib()──▶  LibFile (data_model.py)
                                      │
                          ┌───────────┴───────────┐
                          ▼                       ▼
                    lib_writer.py          excel_exporter.py
                 save_lib() / write_lib()  export_lib_to_excel()
                          │
                          ▼
                     .lib 파일 저장                .xlsx 파일
```

**데이터 계층**: `LibFile → LibBlock → ModelEntry / ParamEntry / DirectiveEntry`

---

## 주요 클래스 (src/main.py)

| 클래스 | 역할 |
|--------|------|
| `LibEditorApp` | 메인 윈도우 — 파일 I/O, 트리뷰, 파라미터 테이블, 테마 전환 |
| `InlineCellEditor` | Treeview 셀 위에 Entry 위젯을 올려 Excel처럼 직접 편집 |
| `ParamAddDialog` | 파라미터/변수 추가 팝업 |
| `BatchEditDialog` | 일괄 파라미터 수정 팝업 |
| `ParameterViewWindow` | 파라미터 중심 — 모델별 값 비교 창 |

---

## 색상 코딩 (파라미터 값 타입별)

| 태그 | 의미 | Dark | Light |
|------|------|------|-------|
| `num` | 숫자 리터럴 | `#57c17e` 초록 | `#1a7a1a` 진한 초록 |
| `var` | 변수 단순 참조 `{name}` | `#dbb86c` 황금색 | `#976008` 황갈색 |
| `expr` | 산술 수식 `{a * b}` | `#a48fd4` 보라 | `#6250a0` 짙은 보라 |

---

## 실행 방법

```bash
cd lib-editor
python3 src/main.py
```

의존성 설치 (Excel 내보내기):
```bash
pip install openpyxl
```

---

## 빌드 (PyInstaller)

```bash
pyinstaller build.spec
```

출력: `dist/SmartSpiceLibEditor` (콘솔 없는 단일 실행 파일)

---

## 개발 규칙

- **테마**: `THEMES` dict(`src/main.py` 상단)에서 색상 일괄 관리. 개별 위젯에 하드코딩 금지.
- **파서 확장**: `.lib` 문법 토큰 추가 시 `lib_parser.py`의 2단계 파서만 수정.
- **데이터 모델 변경**: `data_model.py`의 `copy()` 메서드도 함께 업데이트.
- **임포트**: `src/` 내 파일끼리 상대 임포트 없이 모듈명 직접 임포트 (`from data_model import ...`).

---

## 문의

**dhooonk@lgdisplay.com**
