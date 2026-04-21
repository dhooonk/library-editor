# lib-editor

> **v1.2.0** — Python · Tkinter 기반 Smart Spice `.lib` 모델 파일 편집 GUI 도구

---

## 개발 배경

반도체 소자 설계 및 공정 시뮬레이션 과정에서 Smart Spice는 SPICE 계열의 회로 시뮬레이터로 널리 사용됩니다.  
Smart Spice는 소자 특성 데이터를 `.lib` 파일 형식으로 관리하며, 이 파일에는 수십~수백 개의 `.MODEL` 블록과 수천 개의 파라미터가 포함될 수 있습니다.

기존 작업 방식에서는 이러한 파라미터를 **텍스트 에디터로 직접 수정**하거나 **수작업으로 Excel에 옮겨 비교**하는 불편함이 있었습니다. 특히 다음 상황에서 비효율이 두드러졌습니다.

- 프로세스 코너(TT / FF / SS / FS / SF)별로 동일 파라미터를 일괄 변경해야 할 때
- 여러 모델의 파라미터 값을 한 화면에서 비교하고 싶을 때
- `.lib` 문법(괄호·주석·continuation line)을 손상시키지 않고 편집해야 할 때

이러한 필요에서 **lib-editor**가 개발되었습니다.

---

## 목적

| 목표 | 설명 |
|------|------|
| **직관적 편집** | 트리 기반 구조 탐색과 셀 더블클릭 편집으로 텍스트 수정 없이 파라미터를 변경합니다. |
| **포맷 무결성 보장** | 파싱·저장 과정에서 원본 주석, 괄호, 지시어를 손실 없이 그대로 복원합니다. |
| **일괄 처리 효율화** | 여러 모델에 걸친 동일 파라미터를 한 번의 클릭으로 일괄 변경합니다. |
| **데이터 가시화** | 파라미터 중심 뷰와 Excel 내보내기로 모델 간 값 비교를 쉽게 합니다. |

---

## 구현 사항

### 1. 파일 파싱 (src/lib_parser.py)
- `.LIB / .ENDL / .MODEL / .PARAM` 구문을 인식하는 2단계 파서
- `+` continuation line 병합 처리
- `$` 인라인 주석·`*` 블록 주석 분리 및 보존
- 파라미터 값의 중괄호 수식 `{var * 1.1}` 지원

### 2. 데이터 모델 (src/data_model.py)
- `LibFile → LibBlock → ModelEntry / ParamEntry / DirectiveEntry` 계층 구조
- `OrderedDict` 기반 파라미터 선언 순서 보존
- `copy()` 메서드로 안전한 독립 복사

### 3. GUI 메인 창 (main.py)
- **트리뷰 사이드바**: LibFile 전체 구조를 계층 트리로 시각화
- **인라인 셀 편집**: 파라미터 셀 더블클릭 → Entry 위젯으로 즉시 편집
- **파라미터 색상 코딩**: 숫자(초록) / 변수 참조(황금색) / 수식(보라) 구분
- **테마 전환**: Light ↔ Dark 모드 실시간 전환
- **일괄 수정 (BatchEditDialog)**: 파라미터명 + 새 값 + 적용 범위 선택
- **파라미터 중심 뷰 (ParameterViewWindow)**: 선택 파라미터의 LIB/모델별 값 비교

### 4. 파일 직렬화 (src/lib_writer.py)
- `LibFile` 객체 → Smart Spice 문법 텍스트 역변환
- 80자 기준 자동 `+` continuation line 줄바꿈
- 원본 주석·괄호·인라인 주석 복원

### 5. Excel 내보내기 (src/excel_exporter.py)
- **Matrix View 시트**: 가로=모델명, 세로=파라미터명인 피벗 행렬
- **List View 시트**: Library/Model/Type/Parameter/Value 1차원 목록
- 열 너비 자동 조정

---

## 프로젝트 구조

```
lib-editor/
├── main.py                 # 메인 GUI 애플리케이션 (Tkinter) — 진입점
├── README.md               # 개발 배경·구현 사항 (이 문서)
├── src/                    # Python 소스 모듈
│   ├── data_model.py       # 데이터 클래스: LibFile, LibBlock, ModelEntry 등
│   ├── lib_parser.py       # .lib 파일 파서 (텍스트 → LibFile 객체)
│   ├── lib_writer.py       # 직렬화기 (LibFile 객체 → Smart Spice 텍스트)
│   └── excel_exporter.py   # Excel 내보내기 (LibFile → .xlsx)
├── samples/                # 테스트용 예제 .lib 파일
│   └── sample.lib
├── docs/                   # 문서
│   └── 사용설명서.md        # 처음 사용하는 분들을 위한 단계별 안내서
└── build.spec              # PyInstaller 빌드 설정
```

---

## 요구 사항

- **Python 3.8 이상**
- **Tkinter** (Python 표준 라이브러리에 포함)
- **openpyxl** — Excel 내보내기 기능에 필요

```bash
pip install openpyxl
```

---

## 실행 방법

```bash
cd lib-editor
python3 main.py
```

실행 후 툴바의 **📂 파일 열기** 버튼을 클릭하여 `.lib` 파일을 불러옵니다.

---

## 주요 기능 요약

| 기능 | 방법 |
|------|------|
| `.lib` 파일 열기 | 툴바 **📂 파일 열기** |
| 이름/타입 수정 | 트리에서 `📁 LIB` 또는 `⚙️ MODEL` 더블클릭 |
| 파라미터 값 수정 | 우측 테이블 셀 더블클릭 → 입력 후 `Enter` |
| 파라미터 추가/삭제 | 하단 **＋ 파라미터 추가** / **－ 삭제** |
| 일괄 수정 | 하단 **📋 일괄 수정** |
| 파라미터 중심 뷰 | 트리 하단 **🔄 파라미터 중심 뷰 열기** |
| 내용 미리보기 | 툴바 **👁 내용 미리보기** |
| Excel 내보내기 | 툴바 **📊 Excel 내보내기** |
| 저장 | 툴바 **💾 저장** / **💾 다른 이름으로 저장** |
| 테마 전환 | 툴바 우측 **☀ Light** / **🌙 Dark** |

---

## 값 색상 코딩

| 색상 | 의미 | 예시 | Dark | Light |
|------|------|------|------|-------|
| 🟢 초록 | 숫자 리터럴 | `0.45`, `1.2e-8` | `#6bcb77` | `#1b7c34` |
| 🟡 노랑 | 변수 단순 참조 | `{tox_global}` | `#ffd166` | `#c67c00` |
| 🟣 보라 | 산술 수식 | `{vth_offset + 0.40}`, `{k1 * 2}` | `#c77dff` | `#6c3db3` |

---

## 출력 파일 형식 (Smart Spice 문법)

편집 후 저장하면 아래와 같은 형식으로 출력됩니다:

```spice
.PARAM tox_global=1.2e-8

.LIB NMOS_LIB
.PARAM vth_offset=0.05
.MODEL NMOS_V1 NMOS
+ LEVEL=3 VTH0=0.45 TOX={tox_global} XJ=1.5e-7
+ K1=0.559 K2=-0.04
.ENDL NMOS_LIB
```

- 긴 줄은 `+` continuation line으로 자동 줄바꿈 (80자 기준)
- 원본의 `*` 주석, `$` 인라인 주석, 기타 `.지시어`가 위치 그대로 복원됩니다.
- 파라미터를 묶는 `( )` 괄호 구조도 원형대로 완벽하게 보존됩니다.

---

## 버전 히스토리

| 버전 | 변경 내용 |
|------|----------|
| v1.2.0 | 프로젝트명 lib-editor 변경, 폴더 구조 재편(src/docs/samples), 색상 가독성 개선 |
| v1.1.0 | 다크/라이트 테마 전환, 코드 상세 주석, README·사용설명서 정비 |
| v1.0.0 | 초기 릴리즈 — 파싱·편집·일괄 수정·Excel 내보내기 |

---

## 문의

개발 문의: **dhooonk@lgdisplay.com**

---

## 라이선스

MIT
