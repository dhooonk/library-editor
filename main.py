"""
main.py
─────────────────────────────────────────────────────────────────────────────
Smart Spice LIB 파일 편집기 — 메인 GUI 애플리케이션
Python 표준 라이브러리 Tkinter 기반

이 파일은 애플리케이션의 진입점(Entry Point)이자 GUI 전체를 담당합니다.
파일 열기/저장, 트리뷰 탐색, 파라미터 인라인 편집, 일괄 수정,
다이얼로그 창, 테마 전환 등 모든 UI 로직이 이 파일에 정의되어 있습니다.

주요 클래스:
    InlineCellEditor    : Treeview 셀 위에 Entry 위젯을 올려 직접 편집 지원
    LibEditorApp        : 메인 윈도우 — 파일 I/O, 트리뷰, 파라미터 테이블, 이벤트 처리
    ParamAddDialog      : 파라미터/변수 추가 팝업 다이얼로그
    BatchEditDialog     : 일괄 파라미터 수정 팝업 다이얼로그
    ParameterViewWindow : 파라미터 중심으로 모델별 값을 비교하는 별도 창

외부 모듈 의존성:
    data_model      : LibFile, LibBlock, ModelEntry, ParamEntry, DirectiveEntry
    lib_parser      : parse_lib()   — .lib 텍스트 → LibFile 객체
    lib_writer      : save_lib(), write_lib() — LibFile 객체 → .lib 텍스트/파일
    excel_exporter  : export_lib_to_excel()  — LibFile → .xlsx 파일
─────────────────────────────────────────────────────────────────────────────
"""
import os
import sys

# src/ 폴더의 모듈을 임포트할 수 있도록 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from collections import OrderedDict

from data_model import LibFile, LibBlock, ModelEntry, ParamEntry, DirectiveEntry
from lib_parser import parse_lib
from lib_writer import save_lib, write_lib
from excel_exporter import export_lib_to_excel

# ═════════════════════════════════════════════════════════════════════════════
# 테마 색상 팔레트 정의
# ─────────────────────────────────────────────────────────────────────────────
# 두 가지 테마(dark/light)를 사전(dict) 형태로 정의합니다.
# 각 키는 UI 요소별 색상 역할을 나타내며, 테마 전환 시 전역 변수에 반영됩니다.
# ═════════════════════════════════════════════════════════════════════════════
THEMES = {
    "dark": {
        "BG_DARK":    "#1c1c1c",   # 최외곽 배경 (가장 어두운 레이어)
        "BG_PANEL":   "#262626",   # 패널/사이드바 배경
        "BG_HEADER":  "#2e2e2e",   # 헤더·툴바 배경
        "BG_ROW_ODD": "#222222",   # 테이블 홀수 행 배경
        "BG_ROW_EVN": "#262626",   # 테이블 짝수 행 배경
        "FG_MAIN":    "#d4d4d4",   # 기본 텍스트 색상
        "FG_DIM":     "#707070",   # 보조(흐린) 텍스트 색상
        "FG_ACCENT":  "#b0b0b0",   # 강조 텍스트 색상 (헤더 등)
        "FG_GREEN":   "#6bcb77",   # 숫자 리터럴 (밝은 라임 초록)
        "FG_RED":     "#ff6b6b",   # 위험/삭제 버튼 텍스트 (선명한 빨강)
        "FG_YELLOW":  "#ffd166",   # 변수 참조 (선명한 노랑)
        "FG_PURPLE":  "#c77dff",   # 수식 (선명한 보라)
        "SEL_BG":     "#3a3a3a",   # 선택(Selection) 배경
        "BORDER":     "#444444",   # 경계선 색상
    },
    "light": {
        "BG_DARK":    "#f0f0f0",   # 최외곽 배경 (밝은 회색)
        "BG_PANEL":   "#ffffff",   # 패널 배경 (흰색)
        "BG_HEADER":  "#e0e0e0",   # 헤더·툴바 배경
        "BG_ROW_ODD": "#f8f8f8",   # 테이블 홀수 행 배경
        "BG_ROW_EVN": "#ffffff",   # 테이블 짝수 행 배경
        "FG_MAIN":    "#2c2c2c",   # 기본 텍스트 (어두운 색)
        "FG_DIM":     "#888888",   # 보조 텍스트
        "FG_ACCENT":  "#444444",   # 강조 텍스트
        "FG_GREEN":   "#1b7c34",   # 숫자 리터럴 (진한 초록, 흰 배경 대비)
        "FG_RED":     "#d63031",   # 위험 요소 (선명한 빨강)
        "FG_YELLOW":  "#c67c00",   # 변수 참조 (진한 호박색, 흰 배경 가독성)
        "FG_PURPLE":  "#6c3db3",   # 수식 (짙은 보라, 흰 배경 대비)
        "SEL_BG":     "#cccccc",   # 선택 배경
        "BORDER":     "#bbbbbb",   # 경계선
    },
}

# 현재 활성 테마 이름 (초기값: "dark")
_active_theme = "dark"


def _t(key):
    """현재 테마에서 색상 값을 반환하는 헬퍼 함수"""
    return THEMES[_active_theme][key]


# ── 전역 색상 변수 (하위 호환 및 위젯 생성 시 직접 참조용) ──────────────────
# 테마 변경 시 LibEditorApp._apply_theme_globals()에서 이 변수들을 재할당합니다.
BG_DARK    = THEMES["dark"]["BG_DARK"]
BG_PANEL   = THEMES["dark"]["BG_PANEL"]
BG_HEADER  = THEMES["dark"]["BG_HEADER"]
BG_ROW_ODD = THEMES["dark"]["BG_ROW_ODD"]
BG_ROW_EVN = THEMES["dark"]["BG_ROW_EVN"]
FG_MAIN    = THEMES["dark"]["FG_MAIN"]
FG_DIM     = THEMES["dark"]["FG_DIM"]
FG_ACCENT  = THEMES["dark"]["FG_ACCENT"]
FG_GREEN   = THEMES["dark"]["FG_GREEN"]
FG_RED     = THEMES["dark"]["FG_RED"]
FG_YELLOW  = THEMES["dark"]["FG_YELLOW"]
FG_PURPLE  = THEMES["dark"]["FG_PURPLE"]
SEL_BG     = THEMES["dark"]["SEL_BG"]
BORDER     = THEMES["dark"]["BORDER"]

# ── 폰트 정의 ──────────────────────────────────────────────────────────────
FONT_BODY  = ("Consolas", 11)         # 파라미터 값 등 코드성 텍스트용
FONT_BOLD  = ("Consolas", 11, "bold") # 버튼·헤더 등 강조용
FONT_TITLE = ("Segoe UI", 13, "bold") # 패널 제목 텍스트
FONT_SMALL = ("Consolas", 10)         # 상태바 등 작은 텍스트


# ═════════════════════════════════════════════════════════════════════════════
# InlineCellEditor : Treeview 셀 위에 Entry 위젯을 올려 Excel처럼 직접 편집
# ═════════════════════════════════════════════════════════════════════════════
class InlineCellEditor:
    """
    Tkinter Treeview 안에서 Excel처럼 셀을 직접 클릭하여 수정할 수 있게 해주는
    헬퍼 클래스입니다.

    동작 방식:
        1. start_edit(item, col_index) 호출 시, 선택된 셀의 위치(bbox)를 구합니다.
        2. 동일한 좌표에 임시 tk.Entry 위젯을 'place'하여 셀 위에 겹쳐 표시합니다.
        3. 사용자가 값을 입력하고 Enter 또는 Tab을 누르면 _commit()이 호출됩니다.
        4. _commit()은 on_commit 콜백을 통해 호출자에게 새 값을 전달합니다.
        5. Esc를 누르면 편집을 취소하고 Entry를 제거합니다.

    Attributes:
        tree      : 대상 ttk.Treeview 위젯
        on_commit : 값 확정 시 호출되는 콜백 함수 (item_id, col_index, new_value) → None
        _entry    : 현재 편집 중인 tk.Entry 위젯 (편집 중이 아니면 None)
        _item     : 편집 중인 Treeview 행의 item ID
        _col      : 편집 중인 열 인덱스(0-based)
    """

    def __init__(self, tree: ttk.Treeview, on_commit):
        self.tree = tree
        self.on_commit = on_commit  # 값 확정 콜백: (item_id, col_index, new_value) → None
        self._entry = None          # 현재 표시 중인 Entry 위젯
        self._item  = None          # 편집 중인 행 ID
        self._col   = None          # 편집 중인 열 인덱스

    def start_edit(self, item: str, col_index: int):
        """
        지정된 Treeview 셀에 Entry 위젯을 겹쳐 편집 UI를 시작합니다.

        처리 흐름:
            1. 기존에 열려있는 Entry가 있으면 먼저 취소(cancel())합니다.
            2. tree.bbox()로 해당 셀의 픽셀 좌표와 크기를 가져옵니다.
               (셀이 보이지 않는 위치에 있으면 bbox()가 빈 값을 반환 → 중단)
            3. 셀의 현재 값을 Entry에 미리 채워 넣습니다.
            4. Entry를 셀 위치에 배치(place)하고 포커스를 이동합니다.
            5. Enter/Tab → _commit(), Esc → cancel() 이벤트를 바인딩합니다.

        Args:
            item      (str): Treeview 행의 item ID
            col_index (int): 열 인덱스 (0-based)
        """
        self.cancel()  # 기존 편집 중인 Entry 정리

        col_id = f"#{col_index + 1}"
        bbox = self.tree.bbox(item, col_id)
        if not bbox:
            return  # 셀이 화면에 보이지 않으면 중단
        x, y, width, height = bbox
        value = self.tree.set(item, col_id)  # 셀의 현재 값 읽기

        self._item = item
        self._col  = col_index

        # ── Entry 위젯 생성 및 셀 위치에 배치 ──
        self._entry = tk.Entry(
            self.tree,
            font=FONT_BODY,
            background=BG_HEADER,
            foreground=FG_MAIN,
            insertbackground=FG_MAIN,   # 커서 색상
            relief="flat",
            highlightthickness=1,
            highlightcolor=FG_ACCENT,
            highlightbackground=BORDER,
        )
        self._entry.insert(0, value)           # 셀 현재 값을 Entry에 삽입
        self._entry.place(x=x, y=y, width=width, height=height)  # 셀 위치에 겹치기
        self._entry.focus_set()                # 입력 포커스 이동
        self._entry.select_range(0, tk.END)    # 기존 값 전체 선택

        # ── 이벤트 바인딩 ──
        self._entry.bind("<Return>", self._commit)            # Enter → 확정
        self._entry.bind("<Escape>", lambda e: self.cancel()) # Esc   → 취소
        self._entry.bind("<Tab>",    self._commit)            # Tab   → 확정

    def _commit(self, event=None):
        """
        Entry에 입력된 값을 확정하고 on_commit 콜백을 호출합니다.
        콜백 호출 전에 먼저 Entry를 닫아 UI가 깜빡이지 않도록 합니다.
        """
        if self._entry is None:
            return
        new_value = self._entry.get()         # 사용자가 입력한 새 값
        item, col  = self._item, self._col
        self.cancel()                          # Entry 위젯 제거
        self.on_commit(item, col, new_value)   # 호출자에게 새 값 전달

    def cancel(self):
        """
        진행 중인 편집을 취소하고 Entry 위젯을 파괴합니다.
        편집 상태 변수(_item, _col)도 초기화합니다.
        """
        if self._entry:
            self._entry.destroy()
            self._entry = None
        self._item = None
        self._col  = None


# ═════════════════════════════════════════════════════════════════════════════
# LibEditorApp : 메인 윈도우 — 전체 GUI 라이프사이클 관장
# ═════════════════════════════════════════════════════════════════════════════
class LibEditorApp(tk.Tk):
    """
    Tkinter 기반 Smart Spice .lib 에디터 메인 창 클래스입니다.

    책임 영역:
        - 파일 열기 / 저장 / 다른 이름으로 저장
        - 좌측 트리뷰(사이드바)에 LibFile 구조 반영 및 탐색
        - 우측 파라미터 테이블의 표시 및 인라인 셀 편집
        - 파라미터 추가 / 삭제 / 일괄 수정
        - 미리보기 팝업 및 Excel 내보내기
        - 파라미터 중심 뷰(ParameterViewWindow) 호출
        - Light ↔ Dark 테마 전환

    인스턴스 속성:
        lib_file        (LibFile)     : 현재 열려있는 LIB 파일 데이터 객체
        _current_node   (tuple|None)  : 현재 선택된 트리 노드 정보
                                        예: ("model", model_entry, lib_block)
        _node_map       (dict)        : tree item ID → 백엔드 데이터 객체 매핑
                                        예: {"I001": ("model", model, lb)}
        _param_items    (list)        : 우측 파라미터 테이블의 현재 행 iid 목록
        _current_theme  (str)         : 현재 활성 테마 이름 ("dark" 또는 "light")
    """

    def __init__(self):
        super().__init__()
        self.title("Lib. Editor")
        self.geometry("1280x780")
        self.minsize(900, 600)

        # ── 초기 테마 적용 ──
        self._current_theme = "dark"
        self._apply_theme_globals("dark")
        self.configure(bg=BG_DARK)

        # ── 상태 변수 초기화 ──
        self.lib_file: LibFile = None        # 현재 열린 파일 데이터
        self._current_node = None            # 현재 선택된 트리 노드
        self._node_map = {}                  # tree item id → 데이터 객체 매핑
        self._param_items = []               # 파라미터 테이블 행 ID 목록

        # ── UI 구성 ──
        self._setup_styles()         # ttk 스타일 설정
        self._build_toolbar()        # 상단 툴바 생성
        self._build_main_layout()    # 메인 레이아웃(트리뷰 + 편집 패널) 생성

    # ─────────────────────────────────────────────────────────────────────────
    # 테마 관련 메서드
    # ─────────────────────────────────────────────────────────────────────────

    def _apply_theme_globals(self, theme_name: str):
        """
        전역 색상 변수(BG_DARK, FG_MAIN 등)를 선택된 테마 값으로 일괄 갱신합니다.

        이 함수를 먼저 호출한 뒤 위젯을 생성해야 올바른 색상이 적용됩니다.
        테마 전환 시에는 _toggle_theme() 내부에서 이 함수를 먼저 호출합니다.

        Args:
            theme_name (str): "dark" 또는 "light"
        """
        global BG_DARK, BG_PANEL, BG_HEADER, BG_ROW_ODD, BG_ROW_EVN
        global FG_MAIN, FG_DIM, FG_ACCENT, FG_GREEN, FG_RED
        global FG_YELLOW, FG_PURPLE, SEL_BG, BORDER
        t = THEMES[theme_name]
        BG_DARK    = t["BG_DARK"]
        BG_PANEL   = t["BG_PANEL"]
        BG_HEADER  = t["BG_HEADER"]
        BG_ROW_ODD = t["BG_ROW_ODD"]
        BG_ROW_EVN = t["BG_ROW_EVN"]
        FG_MAIN    = t["FG_MAIN"]
        FG_DIM     = t["FG_DIM"]
        FG_ACCENT  = t["FG_ACCENT"]
        FG_GREEN   = t["FG_GREEN"]
        FG_RED     = t["FG_RED"]
        FG_YELLOW  = t["FG_YELLOW"]
        FG_PURPLE  = t["FG_PURPLE"]
        SEL_BG     = t["SEL_BG"]
        BORDER     = t["BORDER"]

    def _toggle_theme(self):
        """
        Light ↔ Dark 테마를 전환하고 전체 UI를 새 테마로 다시 그립니다.

        처리 흐름:
            1. 현재 테마와 반대 테마명을 결정합니다.
            2. 전역 색상 변수를 새 테마로 갱신합니다.
            3. ttk 스타일을 새로 적용합니다.
            4. 기존 모든 위젯을 파괴하고 툴바·메인 레이아웃을 재구성합니다.
            5. 파일이 열려있으면 트리뷰를 다시 그립니다.
        """
        new_theme = "light" if self._current_theme == "dark" else "dark"
        self._current_theme = new_theme
        self._apply_theme_globals(new_theme)
        self._setup_styles()
        self.configure(bg=BG_DARK)

        # 기존 모든 위젯 파괴 후 재구성
        for widget in self.winfo_children():
            widget.destroy()
        self._build_toolbar()
        self._build_main_layout()

        # 파일이 열려있으면 트리뷰 재구성
        if self.lib_file:
            self._rebuild_tree()
            self._info_var.set("← 좌측 트리에서 항목을 선택하세요")

    # ─────────────────────────────────────────────────────────────────────────
    # UI 스타일 설정
    # ─────────────────────────────────────────────────────────────────────────

    def _setup_styles(self):
        """
        ttk.Style을 사용하여 앱 전체의 위젯 스타일을 현재 테마에 맞게 설정합니다.

        정의하는 스타일 목록:
            - Toolbar.TFrame     : 툴바 프레임 배경
            - Toolbar.TButton    : 툴바 버튼 기본 스타일
            - Accent.TButton     : 확인/추가 등 주요 동작 버튼 (밝은 강조)
            - Danger.TButton     : 삭제 등 위험 동작 버튼 (붉은 계열)
            - Tree.Treeview      : 좌측 사이드바 트리뷰
            - Param.Treeview     : 우측 파라미터 테이블 트리뷰
            - TScrollbar         : 스크롤바
            - TLabel, Header.TLabel: 일반·헤더 라벨
            - TEntry             : 텍스트 입력 필드
        """
        style = ttk.Style(self)
        style.theme_use("clam")  # macOS/윈도우 기본 테마 대신 clam 사용 (커스터마이징 용이)

        # 테마별 동적 색상
        accent_hover = "#888888" if self._current_theme == "dark" else "#333333"
        danger_bg    = "#3a2020" if self._current_theme == "dark" else "#f0e0e0"

        # ── 전역 기본 스타일 ──
        style.configure(".",
            background=BG_DARK,
            foreground=FG_MAIN,
            fieldbackground=BG_PANEL,
            troughcolor=BG_PANEL,
            bordercolor=BORDER,
            darkcolor=BG_DARK,
            lightcolor=BG_PANEL,
            font=FONT_BODY,
        )

        # ── 툴바 ──
        style.configure("Toolbar.TFrame", background=BG_HEADER)
        style.configure("Toolbar.TButton",
            background=BG_HEADER, foreground=FG_MAIN,
            relief="flat", padding=(10, 5), font=FONT_BOLD,
            borderwidth=0,
        )
        style.map("Toolbar.TButton",
            background=[("active", SEL_BG), ("pressed", BORDER)],
            foreground=[("active", FG_ACCENT)],
        )

        # ── 주요 동작 버튼 (확인, 추가 등) ──
        style.configure("Accent.TButton",
            background=SEL_BG, foreground=FG_MAIN,
            relief="flat", padding=(8, 4), font=FONT_BOLD,
        )
        style.map("Accent.TButton",
            background=[("active", accent_hover), ("pressed", BORDER)],
        )

        # ── 위험 버튼 (삭제 등) ──
        style.configure("Danger.TButton",
            background=danger_bg, foreground=FG_RED,
            relief="flat", padding=(8, 4), font=FONT_BOLD,
        )
        style.map("Danger.TButton",
            background=[("active", SEL_BG), ("pressed", BORDER)],
        )

        # ── 좌측 트리뷰 ──
        style.configure("Tree.Treeview",
            background=BG_PANEL, foreground=FG_MAIN,
            fieldbackground=BG_PANEL, rowheight=26,
            borderwidth=0,
        )
        style.configure("Tree.Treeview.Heading",
            background=BG_HEADER, foreground=FG_ACCENT,
            relief="flat", font=FONT_BOLD,
        )
        style.map("Tree.Treeview",
            background=[("selected", SEL_BG)],
            foreground=[("selected", FG_MAIN)],
        )

        # ── 우측 파라미터 테이블 ──
        style.configure("Param.Treeview",
            background=BG_PANEL, foreground=FG_MAIN,
            fieldbackground=BG_PANEL, rowheight=28,
            borderwidth=0,
        )
        style.configure("Param.Treeview.Heading",
            background=BG_HEADER, foreground=FG_ACCENT,
            relief="flat", font=FONT_BOLD,
        )
        style.map("Param.Treeview",
            background=[("selected", SEL_BG)],
            foreground=[("selected", FG_MAIN)],
        )

        # ── 스크롤바 ──
        style.configure("TScrollbar",
            background=BG_PANEL, troughcolor=BG_DARK,
            arrowcolor=FG_DIM, borderwidth=0, width=8,
        )

        # ── 라벨 ──
        style.configure("TLabel",
            background=BG_DARK, foreground=FG_MAIN,
            font=FONT_BODY,
        )
        style.configure("Header.TLabel",
            background=BG_HEADER, foreground=FG_ACCENT,
            font=FONT_TITLE, padding=(12, 6),
        )

        # ── 텍스트 입력 필드 ──
        style.configure("TEntry",
            fieldbackground=BG_PANEL, foreground=FG_MAIN,
            insertcolor=FG_MAIN, borderwidth=1,
            relief="flat",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 툴바 구성
    # ─────────────────────────────────────────────────────────────────────────

    def _build_toolbar(self):
        """
        창 상단에 파일 조작·기능 버튼이 나열된 툴바를 생성합니다.

        배치 순서 (왼쪽 → 오른쪽):
            📂 파일 열기 | 💾 저장 | 💾 다른 이름으로 저장 |
            👁 내용 미리보기 | 📊 Excel 내보내기 | [현재 파일 경로]

        오른쪽 끝:
            ☀ Light / 🌙 Dark 테마 전환 버튼

        추가로 현재 열린 파일 경로를 표시하는 라벨을 배치합니다.
        """
        tb = ttk.Frame(self, style="Toolbar.TFrame")
        tb.pack(side=tk.TOP, fill=tk.X)

        # ── 좌측 버튼 그룹 ──
        ttk.Button(tb, text="📂  파일 열기",         style="Toolbar.TButton",
                   command=self._open_file).pack(side=tk.LEFT, padx=2, pady=4)
        ttk.Button(tb, text="💾  저장",             style="Toolbar.TButton",
                   command=self._save_file).pack(side=tk.LEFT, padx=2, pady=4)
        ttk.Button(tb, text="💾  다른 이름으로 저장", style="Toolbar.TButton",
                   command=self._save_as_file).pack(side=tk.LEFT, padx=2, pady=4)
        ttk.Button(tb, text="👁  내용 미리보기",     style="Toolbar.TButton",
                   command=self._preview).pack(side=tk.LEFT, padx=2, pady=4)
        ttk.Button(tb, text="📊  Excel 내보내기",   style="Toolbar.TButton",
                   command=self._export_excel).pack(side=tk.LEFT, padx=2, pady=4)

        # ── 테마 전환 버튼 (우측 정렬) ──
        # 현재 테마가 dark이면 "☀ Light" 버튼, light이면 "🌙 Dark" 버튼을 표시합니다.
        theme_label = "☀  Light" if self._current_theme == "dark" else "🌙  Dark"
        ttk.Button(tb, text=theme_label, style="Toolbar.TButton",
                   command=self._toggle_theme).pack(side=tk.RIGHT, padx=8, pady=4)

        # ── 현재 파일 경로 라벨 ──
        self._filepath_var = tk.StringVar(value="— 파일을 열어주세요 —")
        ttk.Label(tb, textvariable=self._filepath_var,
                  style="Toolbar.TButton", foreground=FG_DIM).pack(
                  side=tk.LEFT, padx=20)

    # ─────────────────────────────────────────────────────────────────────────
    # 메인 레이아웃 구성 (좌: 트리뷰 / 우: 편집 패널)
    # ─────────────────────────────────────────────────────────────────────────

    def _build_main_layout(self):
        """
        PanedWindow를 사용한 좌우 분할 레이아웃을 구성합니다.

        ┌────────────────────┬──────────────────────────────────────────────┐
        │  좌측 패널         │  우측 패널                                   │
        │  (트리뷰 사이드바)  │  (파라미터 편집 테이블 + 하단 버튼 바)       │
        │  너비: 280px       │  너비: 가변 (나머지 전체)                    │
        └────────────────────┴──────────────────────────────────────────────┘

        좌측 패널 구성:
            - 헤더 라벨 ("📋 라이브러리 구조")
            - 세로 스크롤바가 있는 Treeview (Tree.Treeview 스타일)
            - 하단: 🔄 파라미터 중심 뷰 열기 버튼

        우측 패널 구성:
            - 상단 정보 헤더 (선택된 항목 이름 표시)
            - 세로·가로 스크롤바가 있는 Treeview (Param.Treeview 스타일)
            - 색상 태그: odd/even(배경), var(노랑), expr(보라), num(초록)
            - 하단 버튼 바: ＋추가, －삭제, 📋일괄 수정
            - 변수 전용 프레임(_var_frame, 예약)

        최하단:
            하단 상태바 (문의 이메일 + 버전 라벨)
        """
        # ── PanedWindow (좌우 분할 컨테이너) ──
        pw = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                            bg=BORDER, sashwidth=4,
                            sashrelief="flat")
        pw.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        # ──────────────── 좌측 패널: 트리뷰 ────────────────────────────────
        left = tk.Frame(pw, bg=BG_PANEL, width=280)
        left.pack_propagate(False)   # 자식 위젯이 프레임 크기를 변경하지 못하도록 고정
        pw.add(left, minsize=200)

        # 헤더 라벨
        lbl = tk.Label(left, text="📋  라이브러리 구조",
                       bg=BG_HEADER, fg=FG_ACCENT,
                       font=FONT_TITLE, anchor="w", padx=12, pady=8)
        lbl.pack(fill=tk.X)

        # 트리뷰 컨테이너 프레임
        tree_frame = tk.Frame(left, bg=BG_PANEL)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # 세로 스크롤바
        vsb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        # 라이브러리 구조 트리뷰
        self.tree = ttk.Treeview(tree_frame, style="Tree.Treeview",
                                  yscrollcommand=vsb.set, show="tree headings",
                                  selectmode="browse")   # 한 번에 하나만 선택
        self.tree.heading("#0", text="구조")
        self.tree.column("#0", width=250, minwidth=150)
        self.tree.pack(fill=tk.BOTH, expand=True)
        vsb.config(command=self.tree.yview)

        # ── 트리뷰 이벤트 바인딩 ──
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)      # 단일 클릭 선택
        self.tree.bind("<Double-1>", self._on_tree_double_click)        # 더블클릭 이름 변경

        # ── 파라미터 중심 뷰 전환 버튼 ──
        ttk.Button(left, text="🔄  파라미터 중심 뷰 열기", style="Toolbar.TButton",
                   command=self._open_param_view).pack(fill=tk.X, side=tk.BOTTOM, padx=4, pady=4)

        # ──────────────── 우측 패널: 편집 영역 ──────────────────────────────
        right = tk.Frame(pw, bg=BG_DARK)
        pw.add(right, minsize=400)

        # 상단 정보 헤더 — 현재 선택 항목 이름 표시
        self._info_var = tk.StringVar(value="← 좌측 트리에서 항목을 선택하세요")
        info_lbl = tk.Label(right, textvariable=self._info_var,
                             bg=BG_HEADER, fg=FG_ACCENT,
                             font=FONT_TITLE, anchor="w", padx=14, pady=8)
        info_lbl.pack(fill=tk.X)

        # 파라미터 테이블 영역
        table_frame = tk.Frame(right, bg=BG_DARK)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # 세로 스크롤바
        tvsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL)
        tvsb.pack(side=tk.RIGHT, fill=tk.Y)
        # 가로 스크롤바
        thsb = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        thsb.pack(side=tk.BOTTOM, fill=tk.X)

        # ── 파라미터 테이블 (Param.Treeview) ──
        # 열 구성: "name" (파라미터명) | "value" (파라미터 값)
        self.param_tree = ttk.Treeview(
            table_frame,
            style="Param.Treeview",
            columns=("name", "value"),
            show="headings",             # 열 헤더만 표시 (트리 아이콘 숨김)
            selectmode="browse",
            yscrollcommand=tvsb.set,
            xscrollcommand=thsb.set,
        )
        self.param_tree.heading("name",  text="Parameter 명",  anchor="w")
        self.param_tree.heading("value", text="Parameter 값",  anchor="w")
        self.param_tree.column("name",  width=280, minwidth=120, anchor="w")
        self.param_tree.column("value", width=400, minwidth=120, anchor="w")
        self.param_tree.pack(fill=tk.BOTH, expand=True)
        tvsb.config(command=self.param_tree.yview)
        thsb.config(command=self.param_tree.xview)

        # ── 색상 태그 정의 ──
        # 파라미터 값의 종류에 따라 행 색상을 구분합니다.
        self.param_tree.tag_configure("odd",  background=BG_ROW_ODD)  # 홀수 행 배경
        self.param_tree.tag_configure("even", background=BG_ROW_EVN)  # 짝수 행 배경
        self.param_tree.tag_configure("var",  foreground=FG_YELLOW)   # 변수 단순 참조: 노랑
        self.param_tree.tag_configure("expr", foreground=FG_PURPLE)   # 산술 수식: 보라
        self.param_tree.tag_configure("num",  foreground=FG_GREEN)    # 숫자 리터럴: 초록

        # ── 더블클릭 → 인라인 셀 편집 ──
        self.param_tree.bind("<Double-1>", self._on_param_dblclick)
        self._cell_editor = InlineCellEditor(self.param_tree, self._on_cell_commit)

        # ── 하단 버튼 바 ──
        btn_bar = tk.Frame(right, bg=BG_PANEL, pady=6)
        btn_bar.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Button(btn_bar, text="＋  파라미터 추가", style="Accent.TButton",
                   command=self._add_param).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_bar, text="－  삭제",         style="Danger.TButton",
                   command=self._delete_param).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_bar, text="📋  일괄 수정",   style="Toolbar.TButton",
                   command=self._batch_edit_param).pack(side=tk.LEFT, padx=4)

        # ── 변수(PARAM) 전용 하단 섹션 (예약 영역) ──
        self._var_frame = tk.Frame(right, bg=BG_DARK)
        self._var_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=8, pady=(0, 4))

        # ── 최하단 상태바 — 문의 이메일 및 버전 표시 ──
        status_bar = tk.Frame(self, bg=BG_HEADER, relief="flat")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(
            status_bar,
            text="문의사항 : dhooonk@lgdisplay.com    v1.1.0",
            bg=BG_HEADER,
            fg=FG_DIM,
            font=FONT_SMALL,
            anchor="e",
            padx=12,
            pady=4,
        ).pack(side=tk.RIGHT)

    # ─────────────────────────────────────────────────────────────────────────
    # 파일 열기 / 저장 / 미리보기
    # ─────────────────────────────────────────────────────────────────────────

    def _open_file(self):
        """
        파일 선택 다이얼로그를 열고 선택된 .lib 파일을 파싱하여 화면에 반영합니다.

        처리 흐름:
            1. filedialog.askopenfilename()으로 .lib 파일 경로를 선택받습니다.
            2. parse_lib()로 파일을 파싱하여 lib_file 속성에 저장합니다.
            3. 툴바의 파일 경로 라벨을 현재 경로로 갱신합니다.
            4. 트리뷰를 재구성합니다.
            5. 파싱 중 예외 발생 시 오류 메시지 박스를 표시합니다.
        """
        path = filedialog.askopenfilename(
            title="LIB 파일 선택",
            filetypes=[("LIB 파일", "*.lib *.LIB"), ("모든 파일", "*.*")],
        )
        if not path:
            return  # 선택 취소 시 무시
        try:
            self.lib_file = parse_lib(path)
            self._filepath_var.set(path)          # 툴바 경로 갱신
            self._rebuild_tree()                  # 트리뷰 재구성
            self._info_var.set("← 좌측 트리에서 MODEL이나 PARAMS를 선택하세요")
            self._clear_param_table()             # 이전 테이블 초기화
        except Exception as e:
            messagebox.showerror("파싱 오류", f"파일을 읽는 중 오류가 발생했습니다:\n{e}")

    def _save_file(self):
        """
        현재 열린 파일을 원본 경로에 덮어씌워 저장합니다.

        파일이 열려있지 않으면 경고 메시지를 표시합니다.
        저장 성공 시 완료 알림, 실패 시 오류 메시지를 표시합니다.
        """
        if not self.lib_file:
            messagebox.showwarning("경고", "열린 파일이 없습니다.")
            return
        try:
            path = save_lib(self.lib_file)   # 원본 경로에 저장 (filepath=None → lib_file.filepath 사용)
            messagebox.showinfo("저장 완료", f"저장 완료:\n{path}")
        except Exception as e:
            messagebox.showerror("저장 오류", str(e))

    def _save_as_file(self):
        """
        새 파일명을 입력받아 현재 LIB 데이터를 저장합니다.

        처리 흐름:
            1. 파일 저장 다이얼로그로 저장 경로를 선택받습니다.
            2. 선택된 경로에 save_lib()로 저장합니다.
            3. lib_file.filepath와 툴바 경로 라벨을 새 경로로 갱신합니다.
        """
        if not self.lib_file:
            messagebox.showwarning("경고", "열린 파일이 없습니다.")
            return
        path = filedialog.asksaveasfilename(
            title="다른 이름으로 저장",
            defaultextension=".lib",
            filetypes=[("LIB 파일", "*.lib"), ("모든 파일", "*.*")],
        )
        if not path:
            return  # 선택 취소 시 무시
        try:
            save_lib(self.lib_file, filepath=path)
            self.lib_file.filepath = path    # 내부 경로 갱신
            self._filepath_var.set(path)     # 툴바 경로 라벨 갱신
            messagebox.showinfo("저장 완료", f"저장 완료:\n{path}")
        except Exception as e:
            messagebox.showerror("저장 오류", str(e))

    def _preview(self):
        """
        현재 편집 중인 LIB 데이터를 Smart Spice 문법 텍스트로 변환하여
        팝업 창(읽기 전용)에 표시합니다.

        write_lib()로 직렬화한 텍스트를 tk.Text 위젯에 삽입하고
        state="disabled"로 설정하여 수정을 방지합니다.
        """
        if not self.lib_file:
            messagebox.showwarning("경고", "열린 파일이 없습니다.")
            return
        text = write_lib(self.lib_file)   # 현재 데이터를 텍스트로 직렬화

        # ── 미리보기 팝업 창 ──
        win = tk.Toplevel(self)
        win.title("📄 LIB 파일 미리보기")
        win.geometry("900x650")
        win.configure(bg=BG_DARK)

        # 헤더 라벨
        tk.Label(win, text="LIB 파일 미리보기 (읽기 전용)",
                 bg=BG_HEADER, fg=FG_ACCENT,
                 font=FONT_TITLE, anchor="w", padx=12, pady=6).pack(fill=tk.X)

        # 텍스트 영역 + 스크롤바
        frame = tk.Frame(win, bg=BG_DARK)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        sb_y = ttk.Scrollbar(frame); sb_y.pack(side=tk.RIGHT, fill=tk.Y)
        sb_x = ttk.Scrollbar(frame, orient=tk.HORIZONTAL)
        sb_x.pack(side=tk.BOTTOM, fill=tk.X)

        txt = tk.Text(frame,
                      bg=BG_PANEL, fg=FG_MAIN,
                      font=FONT_BODY, wrap=tk.NONE,
                      insertbackground=FG_MAIN,
                      yscrollcommand=sb_y.set,
                      xscrollcommand=sb_x.set,
                      relief="flat")
        txt.pack(fill=tk.BOTH, expand=True)
        sb_y.config(command=txt.yview)
        sb_x.config(command=txt.xview)
        txt.insert("1.0", text)           # 직렬화된 텍스트 삽입
        txt.configure(state="disabled")   # 읽기 전용으로 설정

    # ─────────────────────────────────────────────────────────────────────────
    # 트리뷰 구성 및 이벤트 처리
    # ─────────────────────────────────────────────────────────────────────────

    def _rebuild_tree(self):
        """
        메모리에 파싱된 `self.lib_file` 데이터를 기반으로
        좌측 사이드바 트리뷰를 초기화하고 다시 그립니다.

        출력 계층 구조:
            🔧 전역 PARAMS          ← lib_file.global_params 존재 시
               ├─ var = value
            📄 전역 설정            ← lib_file.global_directives 존재 시
               ├─ .temp 27
            📁 LIB: 이름            ← lib_file.lib_blocks 순서대로
               ├─ 🔧 PARAMS
               ├─ 📄 설정
               └─ ⚙️ MODEL명 [타입]

        _node_map 매핑 구조:
            tree_item_id → ("kind", data_object, [optional: lib_block])
            예: "I003" → ("model", model_entry, lib_block)
        """
        # 기존 트리 항목 전체 삭제
        self.tree.delete(*self.tree.get_children())
        self._node_map.clear()   # 매핑 테이블 초기화

        if not self.lib_file:
            return

        # ── 전역 PARAMS 노드 ──
        # lib_file.global_params가 있을 때만 표시합니다.
        if self.lib_file.global_params:
            node = self.tree.insert("", "end",
                                    text="🔧 전역 PARAMS",
                                    open=True, tags=("params",))
            self._node_map[node] = ("global_params", None)
            # 각 전역 파라미터를 자식 노드로 추가
            for pe in self.lib_file.global_params:
                child = self.tree.insert(node, "end",
                                         text=f"  {pe.name} = {pe.value}",
                                         tags=("param_var",))
                self._node_map[child] = ("global_param_var", pe)

        # ── 전역 기타 지시어 노드 ──
        if self.lib_file.global_directives:
            node = self.tree.insert("", "end",
                                    text="📄 전역 설정 (.directives)",
                                    open=True, tags=("directives",))
            self._node_map[node] = ("global_directives", None)
            for de in self.lib_file.global_directives:
                child = self.tree.insert(node, "end",
                                         text=f"  {de.raw_text}",
                                         tags=("directive_var",))
                self._node_map[child] = ("global_directive_var", de)

        # ── 각 LIB 블록 노드 ──
        for lb in self.lib_file.lib_blocks:
            lib_node = self.tree.insert("", "end",
                                         text=f"📁 LIB: {lb.name}",
                                         open=True, tags=("lib",))
            self._node_map[lib_node] = ("lib", lb)

            # LIB 내 PARAMS 노드
            if lb.params:
                p_node = self.tree.insert(lib_node, "end",
                                          text="  🔧 PARAMS",
                                          tags=("params",))
                self._node_map[p_node] = ("lib_params", lb)

            # LIB 내 기타 지시어 노드
            if lb.directives:
                d_node = self.tree.insert(lib_node, "end",
                                          text="  📄 설정 (.directives)",
                                          tags=("directives",))
                self._node_map[d_node] = ("lib_directives", lb)

            # LIB 내 MODEL 노드들
            for model in lb.models:
                m_node = self.tree.insert(
                    lib_node, "end",
                    text=f"  ⚙️ {model.name}  [{model.model_type}]",
                    tags=("model",),
                )
                self._node_map[m_node] = ("model", model, lb)

        # ── 트리 태그 색상 설정 ──
        self.tree.tag_configure("lib",           foreground=FG_ACCENT)  # LIB 블록명
        self.tree.tag_configure("model",         foreground=FG_GREEN)   # MODEL명
        self.tree.tag_configure("params",        foreground=FG_YELLOW)  # PARAMS 노드
        self.tree.tag_configure("param_var",     foreground=FG_DIM)     # 개별 변수
        self.tree.tag_configure("directives",    foreground=FG_PURPLE)  # 지시어 노드
        self.tree.tag_configure("directive_var", foreground=FG_DIM)     # 개별 지시어

    def _on_tree_double_click(self, event):
        """
        트리뷰 항목을 더블클릭했을 때 이름/속성 변경 다이얼로그를 엽니다.

        지원 대상:
            - "lib"   : LIB 블록 이름 변경 (simpledialog.askstring 사용)
            - "model" : MODEL 이름·타입 변경 (ParamAddDialog 재활용)
        """
        sel = self.tree.selection()
        if not sel:
            return
        iid  = sel[0]
        info = self._node_map.get(iid)
        if not info:
            return

        kind = info[0]
        if kind == "lib":
            # ── LIB 블록 이름 변경 ──
            lb = info[1]
            new_name = simpledialog.askstring(
                "LIB 이름 변경", "새 LIB 이름을 입력하세요:",
                initialvalue=lb.name, parent=self)
            if new_name and new_name.strip():
                lb.name = new_name.strip()
                self._rebuild_tree()   # 트리뷰 갱신

        elif kind == "model":
            # ── MODEL 이름·타입 변경 (ParamAddDialog 재활용) ──
            model = info[1]
            dlg = ParamAddDialog(self, title="MODEL 속성 변경")
            dlg._name_var.set(model.name)
            dlg._val_var.set(model.model_type)
            if dlg.result:
                new_name, new_type = dlg.result
                model.name       = new_name
                model.model_type = new_type
                self._rebuild_tree()
                self._on_tree_select()

    def _on_tree_select(self, event=None):
        """
        트리뷰 항목 선택 시 호출되는 이벤트 핸들러입니다.

        선택된 항목의 종류(kind)에 따라 우측 편집 패널을 갱신합니다:
            "model"            → _show_model_params()  — MODEL 파라미터 목록 표시
            "global_params"    → _show_param_list()    — 전역 PARAM 변수 목록
            "lib_params"       → _show_param_list()    — LIB별 PARAM 변수 목록
            "lib"              → _clear_param_table()  — LIB 블록 요약 정보만 표시
            "global_directives"→ _show_directive_list()— 전역 지시어 목록
            "lib_directives"   → _show_directive_list()— LIB별 지시어 목록
            그 외              → _clear_param_table()  — 테이블 초기화
        """
        sel = self.tree.selection()
        if not sel:
            return
        iid  = sel[0]
        info = self._node_map.get(iid)
        if not info:
            return
        kind = info[0]

        if kind == "model":
            _, model, lb = info
            self._current_node = ("model", model, lb)
            self._info_var.set(f"⚙️  MODEL: {model.name}   타입: {model.model_type}")
            self._show_model_params(model)

        elif kind == "global_params":
            self._current_node = ("global_params", None)
            self._info_var.set("🔧  전역 PARAMS  (.PARAM 변수)")
            self._show_param_list(self.lib_file.global_params)

        elif kind == "lib_params":
            lb = info[1]
            self._current_node = ("lib_params", lb)
            self._info_var.set(f"🔧  LIB [{lb.name}] – PARAMS  (.PARAM 변수)")
            self._show_param_list(lb.params)

        elif kind == "lib":
            lb = info[1]
            self._current_node = ("lib", lb)
            self._info_var.set(
                f"📁  LIB: {lb.name}   (MODEL {len(lb.models)}개 / PARAM {len(lb.params)}개)")
            self._clear_param_table()

        elif kind == "global_directives":
            self._current_node = ("global_directives", None)
            self._info_var.set("📄  전역 설정 (.directives)")
            self._show_directive_list(self.lib_file.global_directives)

        elif kind == "lib_directives":
            lb = info[1]
            self._current_node = ("lib_directives", lb)
            self._info_var.set(f"📄  LIB [{lb.name}] – 설정 (.directives)")
            self._show_directive_list(lb.directives)

        else:
            self._clear_param_table()

    # ─────────────────────────────────────────────────────────────────────────
    # 파라미터 테이블 표시 메서드
    # ─────────────────────────────────────────────────────────────────────────

    def _show_model_params(self, model: ModelEntry):
        """
        선택된 ModelEntry의 파라미터를 우측 테이블에 채웁니다.

        테이블 행 색상은 _value_tag()로 결정합니다:
            숫자 → 초록(num), 변수 참조 → 노랑(var), 수식 → 보라(expr)

        Args:
            model (ModelEntry): 파라미터를 표시할 모델 객체
        """
        self._clear_param_table()
        for i, (name, value) in enumerate(model.params.items()):
            tag = self._value_tag(value, i)
            iid = self.param_tree.insert("", "end",
                                          values=(name, value),
                                          tags=tag)
            self._param_items.append(iid)

    def _show_param_list(self, param_list: list):
        """
        .PARAM 변수 목록(ParamEntry 리스트)을 우측 테이블에 표시합니다.

        열 헤더를 "변수명" / "변수 값" 으로 변경하여 PARAM 뷰임을 명시합니다.

        Args:
            param_list (list[ParamEntry]): 표시할 ParamEntry 목록
        """
        self._clear_param_table()
        self.param_tree.heading("name",  text="변수명")
        self.param_tree.heading("value", text="변수 값")
        for i, pe in enumerate(param_list):
            tag = self._value_tag(pe.value, i)
            iid = self.param_tree.insert("", "end",
                                          values=(pe.name, pe.value),
                                          tags=tag)
            self._param_items.append(iid)

    def _show_directive_list(self, directive_list: list):
        """
        지시어 목록(DirectiveEntry 리스트)을 우측 테이블에 표시합니다.

        열 헤더를 "키워드" / "전체 지시어 (원문)" 으로 변경합니다.

        Args:
            directive_list (list[DirectiveEntry]): 표시할 DirectiveEntry 목록
        """
        self._clear_param_table()
        self.param_tree.heading("name",  text="키워드")
        self.param_tree.heading("value", text="전체 지시어 (원문)")
        for i, de in enumerate(directive_list):
            base = "odd" if i % 2 == 0 else "even"
            iid = self.param_tree.insert("", "end",
                                          values=(de.keyword, de.raw_text),
                                          tags=(base,))
            self._param_items.append(iid)

    def _value_tag(self, value: str, row_idx: int) -> str:
        """
        파라미터 값 문자열을 분석하여 적절한 색상 태그를 반환합니다.

        태그 결정 규칙:
            1. 값에 '{' 와 '}' 가 모두 포함된 경우:
               - 내부에 사칙연산자( + - * / )가 있으면 → "expr" (수식, 보라색)
               - 그렇지 않으면 → "var" (변수 단순 참조, 노랑색)
            2. 값을 float으로 변환 가능하면 → "num" (숫자, 초록색)
            3. 나머지 → "odd" 또는 "even" (홀짝 행 배경색)

        Args:
            value   (str): 파라미터 값 문자열
            row_idx (int): 테이블 행 인덱스 (홀짝 배경 결정용)

        Returns:
            str: Treeview 태그 이름 ("var", "expr", "num", "odd", "even")
        """
        base = "odd" if row_idx % 2 == 0 else "even"
        if "{" in value and "}" in value:
            # 중괄호 수식: 사칙연산 포함 여부로 expr/var 구분
            stripped = value.strip("{} ")
            if any(op in stripped for op in ["+", "-", "*", "/"]):
                return (base, "expr")
            return (base, "var")
        try:
            float(value)
            return (base, "num")   # float 변환 성공 → 숫자 리터럴
        except ValueError:
            pass
        return (base,)  # 기타 → 홀짝 배경만

    def _clear_param_table(self):
        """
        파라미터 테이블의 모든 행을 삭제하고 열 헤더를 기본값으로 초기화합니다.

        새 항목을 선택하거나 트리뷰를 재구성하기 전에 이 함수를 호출합니다.
        """
        self.param_tree.heading("name",  text="Parameter 명")
        self.param_tree.heading("value", text="Parameter 값")
        for iid in self.param_tree.get_children():
            self.param_tree.delete(iid)
        self._param_items = []

    # ─────────────────────────────────────────────────────────────────────────
    # 인라인 셀 편집
    # ─────────────────────────────────────────────────────────────────────────

    def _on_param_dblclick(self, event):
        """
        파라미터 테이블 셀을 더블클릭했을 때 인라인 편집을 시작합니다.

        처리 흐름:
            1. 클릭된 영역이 "cell" 인지 확인합니다 (헤더 클릭 제외).
            2. 클릭된 열 인덱스(0-based)와 행 ID를 파악합니다.
            3. InlineCellEditor.start_edit()으로 Entry 위젯을 시작합니다.
        """
        region = self.param_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        col_id    = self.param_tree.identify_column(event.x)
        col_index = int(col_id.replace("#", "")) - 1  # "#1" → 0, "#2" → 1
        item      = self.param_tree.identify_row(event.y)
        if not item:
            return
        self._cell_editor.start_edit(item, col_index)

    def _on_cell_commit(self, item_id: str, col_index: int, new_value: str):
        """
        인라인 편집이 완료(Enter/Tab)되었을 때 데이터 모델을 업데이트합니다.

        처리 로직:
            - 열 인덱스 0 (파라미터 이름 열):
                _rename_param_key()로 파라미터 이름을 변경합니다.
            - 열 인덱스 1 (파라미터 값 열):
                _update_param_value()로 값을 변경하고 태그를 재적용합니다.

        Args:
            item_id   (str): 편집된 Treeview 행의 item ID
            col_index (int): 편집된 열 인덱스 (0: 이름, 1: 값)
            new_value (str): 사용자가 입력한 새 값
        """
        col_id = f"#{col_index + 1}"
        old_values = self.param_tree.item(item_id, "values")
        if not old_values:
            return
        old_name, old_val = old_values[0], old_values[1]

        if col_index == 0:
            # ── 파라미터 이름 변경 ──
            new_name = new_value.strip()
            if not new_name:
                return
            self._rename_param_key(old_name, new_name)
            self.param_tree.set(item_id, "#1", new_name)

        elif col_index == 1:
            # ── 파라미터 값 변경 ──
            self._update_param_value(old_name, new_value.strip())
            self.param_tree.set(item_id, "#2", new_value.strip())
            # 새 값에 맞게 색상 태그 재적용
            row_idx = self.param_tree.index(item_id)
            tag = self._value_tag(new_value.strip(), row_idx)
            self.param_tree.item(item_id, tags=tag)

    def _rename_param_key(self, old_name: str, new_name: str):
        """
        현재 선택된 노드에서 파라미터 이름을 old_name → new_name 으로 변경합니다.

        노드 종류별 처리:
            "model"               : ModelEntry.params (OrderedDict)의 키를 교체합니다.
                                    OrderedDict는 키 교체를 직접 지원하지 않으므로
                                    items() 리스트로 변환 → 해당 인덱스의 키 교체 →
                                    새 OrderedDict 생성 방식을 사용합니다.
            "global_params" /
            "lib_params"          : ParamEntry.name을 변경합니다.
            "global_directives" /
            "lib_directives"      : DirectiveEntry.keyword를 변경합니다.

        Args:
            old_name (str): 변경 전 파라미터 이름
            new_name (str): 변경 후 파라미터 이름
        """
        node = self._current_node
        if not node:
            return
        kind = node[0]

        if kind == "model":
            model: ModelEntry = node[1]
            if old_name in model.params:
                # OrderedDict 키 순서 보존 방식으로 이름 교체
                keys  = list(model.params.keys())
                idx   = keys.index(old_name)
                items = list(model.params.items())
                items[idx] = (new_name, items[idx][1])
                model.params = OrderedDict(items)

        elif kind in ("global_params", "lib_params"):
            param_list = (self.lib_file.global_params
                          if kind == "global_params"
                          else node[1].params)
            for pe in param_list:
                if pe.name == old_name:
                    pe.name = new_name
                    break

        elif kind in ("global_directives", "lib_directives"):
            directive_list = (self.lib_file.global_directives
                              if kind == "global_directives"
                              else node[1].directives)
            for de in directive_list:
                if de.keyword == old_name:
                    de.keyword = new_name
                    break

    def _update_param_value(self, param_name: str, new_value: str):
        """
        현재 선택된 노드에서 특정 파라미터의 값을 new_value로 변경합니다.

        노드 종류별 처리:
            "model"               : model.params[param_name] 직접 갱신
            "global_params" /
            "lib_params"          : 해당 이름의 ParamEntry.value 갱신
            "global_directives" /
            "lib_directives"      : 해당 키워드의 DirectiveEntry.raw_text 갱신

        Args:
            param_name (str): 값을 변경할 파라미터 이름
            new_value  (str): 새 파라미터 값 문자열
        """
        node = self._current_node
        if not node:
            return
        kind = node[0]

        if kind == "model":
            model: ModelEntry = node[1]
            if param_name in model.params:
                model.params[param_name] = new_value

        elif kind in ("global_params", "lib_params"):
            param_list = (self.lib_file.global_params
                          if kind == "global_params"
                          else node[1].params)
            for pe in param_list:
                if pe.name == param_name:
                    pe.value = new_value
                    break

        elif kind in ("global_directives", "lib_directives"):
            directive_list = (self.lib_file.global_directives
                              if kind == "global_directives"
                              else node[1].directives)
            for de in directive_list:
                if de.keyword == param_name:
                    de.raw_text = new_value
                    break

    # ─────────────────────────────────────────────────────────────────────────
    # 파라미터 추가
    # ─────────────────────────────────────────────────────────────────────────

    def _add_param(self):
        """
        현재 선택된 노드에 새 파라미터(또는 변수·지시어)를 추가합니다.

        노드 종류별 처리:
            "model"               : ModelEntry.params 에 새 항목 추가
            "global_params" /
            "lib_params"          : ParamEntry 객체를 해당 목록에 추가
            "global_directives" /
            "lib_directives"      : DirectiveEntry 객체를 해당 지시어 목록에 추가
            "lib"                 : LibBlock.params에 새 변수 추가

        모든 경우 ParamAddDialog로 이름·값 입력을 받습니다.
        추가 후 파라미터 테이블과 필요 시 트리뷰도 갱신합니다.
        """
        node = self._current_node
        if not node:
            messagebox.showwarning("선택 필요", "먼저 좌측 트리에서 MODEL 또는 PARAMS를 선택하세요.")
            return

        kind = node[0]

        if kind == "model":
            # ── MODEL 파라미터 추가 ──
            model: ModelEntry = node[1]
            dlg = ParamAddDialog(self, title="파라미터 추가")
            if dlg.result:
                pname, pval = dlg.result
                model.params[pname] = pval          # 데이터 모델에 추가
                row_idx = len(self._param_items)
                tag = self._value_tag(pval, row_idx)
                iid = self.param_tree.insert("", "end", values=(pname, pval), tags=tag)
                self._param_items.append(iid)
                self.param_tree.see(iid)            # 새 행이 보이도록 스크롤

        elif kind in ("global_params", "lib_params"):
            # ── PARAM 변수 추가 ──
            param_list = (self.lib_file.global_params
                          if kind == "global_params"
                          else node[1].params)
            dlg = ParamAddDialog(self, title="변수(PARAM) 추가")
            if dlg.result:
                pname, pval = dlg.result
                param_list.append(ParamEntry(name=pname, value=pval))
                row_idx = len(self._param_items)
                tag = self._value_tag(pval, row_idx)
                iid = self.param_tree.insert("", "end", values=(pname, pval), tags=tag)
                self._param_items.append(iid)
                self.param_tree.see(iid)
                self._rebuild_tree()  # 트리뷰에도 새 변수 반영

        elif kind in ("global_directives", "lib_directives"):
            # ── 지시어 추가 ──
            directive_list = (self.lib_file.global_directives
                              if kind == "global_directives"
                              else node[1].directives)
            dlg = ParamAddDialog(self, title="지시어(Directive) 추가")
            if dlg.result:
                keyw, text = dlg.result
                directive_list.append(DirectiveEntry(keyword=keyw, raw_text=text))
                row_idx = len(self._param_items)
                base = "odd" if row_idx % 2 == 0 else "even"
                iid = self.param_tree.insert("", "end", values=(keyw, text), tags=(base,))
                self._param_items.append(iid)
                self.param_tree.see(iid)
                self._rebuild_tree()

        elif kind == "lib":
            # ── LIB 블록에 변수 추가 ──
            lb: LibBlock = node[1]
            dlg = ParamAddDialog(self, title="변수(PARAM) 추가")
            if dlg.result:
                pname, pval = dlg.result
                lb.params.append(ParamEntry(name=pname, value=pval))
                self._rebuild_tree()

    # ─────────────────────────────────────────────────────────────────────────
    # 파라미터 삭제
    # ─────────────────────────────────────────────────────────────────────────

    def _delete_param(self):
        """
        우측 테이블에서 선택된 파라미터(또는 변수·지시어)를 삭제합니다.

        처리 흐름:
            1. 테이블에서 선택된 행을 확인합니다.
            2. 삭제 전 확인 다이얼로그를 표시합니다.
            3. 현재 노드 종류에 따라 데이터 모델에서 해당 항목을 제거합니다.
            4. 테이블 UI에서 행을 삭제하고 _param_items 목록을 갱신합니다.

        노드 종류별 처리:
            "model"               : model.params 딕셔너리에서 키 삭제
            "global_params" /
            "lib_params"          : param_list에서 해당 ParamEntry 제거
            "global_directives" /
            "lib_directives"      : directive_list에서 해당 DirectiveEntry 제거
        """
        sel = self.param_tree.selection()
        if not sel:
            messagebox.showwarning("선택 필요", "삭제할 파라미터를 선택하세요.")
            return
        item_id = sel[0]
        values  = self.param_tree.item(item_id, "values")
        if not values:
            return
        param_name = values[0]  # 1열 = 파라미터 이름

        # 삭제 확인 다이얼로그
        if not messagebox.askyesno("삭제 확인",
                                    f"'{param_name}' 파라미터를 삭제하시겠습니까?"):
            return

        node = self._current_node
        if not node:
            return
        kind = node[0]

        if kind == "model":
            model: ModelEntry = node[1]
            if param_name in model.params:
                del model.params[param_name]

        elif kind in ("global_params", "lib_params"):
            param_list = (self.lib_file.global_params
                          if kind == "global_params"
                          else node[1].params)
            for i, pe in enumerate(param_list):
                if pe.name == param_name:
                    param_list.pop(i)
                    break
            self._rebuild_tree()  # 트리뷰 갱신

        elif kind in ("global_directives", "lib_directives"):
            directive_list = (self.lib_file.global_directives
                              if kind == "global_directives"
                              else node[1].directives)
            for i, de in enumerate(directive_list):
                if de.keyword == param_name:
                    directive_list.pop(i)
                    break
            self._rebuild_tree()

        # ── UI 테이블에서 행 삭제 ──
        self.param_tree.delete(item_id)
        if item_id in self._param_items:
            self._param_items.remove(item_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Excel 내보내기 및 일괄 수정
    # ─────────────────────────────────────────────────────────────────────────

    def _export_excel(self):
        """
        현재 LIB 파일 전체 데이터를 Excel(.xlsx) 파일로 내보냅니다.

        처리 흐름:
            1. 저장 경로를 filedialog로 선택받습니다.
               (기본 파일명: 원본 파일명 + "_export.xlsx")
            2. export_lib_to_excel()을 호출하여 .xlsx 파일을 생성합니다.
            3. 성공 시 완료 알림, 실패 시 오류 메시지를 표시합니다.
        """
        if not self.lib_file:
            messagebox.showwarning("경고", "열린 파일이 없습니다.")
            return

        # 기본 저장 파일명: 원본 이름 + "_export.xlsx"
        default_name = os.path.splitext(
            os.path.basename(self.lib_file.filepath))[0] + "_export.xlsx"
        path = filedialog.asksaveasfilename(
            title="Excel로 내보내기",
            initialfile=default_name,
            defaultextension=".xlsx",
            filetypes=[("Excel 파일", "*.xlsx")],
        )
        if not path:
            return
        try:
            export_lib_to_excel(self.lib_file, path)
            messagebox.showinfo("내보내기 완료", f"Excel 생성 완료:\n{path}")
        except Exception as e:
            messagebox.showerror("오류", f"Excel 내보내기 실패:\n{e}")

    def _batch_edit_param(self):
        """
        일괄 수정(Batch Edit) 다이얼로그를 띄워 특정 파라미터의 값 전체를 변경합니다.

        처리 흐름:
            1. BatchEditDialog를 열어 파라미터 이름, 새 값, 적용 범위를 선택받습니다.
            2. 선택된 범위(전체 LIB 또는 현재 선택 LIB)의 모든 모델을 순회합니다.
            3. 대상 파라미터 이름이 일치하는 모든 모델의 값을 새 값으로 교체합니다.
            4. 변경된 모델 수를 알림 메시지로 표시하고 현재 뷰를 갱신합니다.

        적용 범위:
            "all" : lib_file.lib_blocks 전체 모델
            "lib" : 현재 선택된 LIB 블록 내 모델만
        """
        if not self.lib_file:
            return

        dlg = BatchEditDialog(self, self.lib_file, getattr(self, '_current_node', None))
        if dlg.result:
            p_name, p_value, scope = dlg.result
            count = 0

            # ── 적용 범위 결정 ──
            if scope == "all":
                blocks = self.lib_file.lib_blocks   # 전체 LIB 블록
            elif scope == "lib" and self._current_node and self._current_node[0] in (
                    "lib", "model", "lib_params", "lib_directives"):
                # 현재 선택된 LIB 블록 식별 (노드 종류별 위치 다름)
                lb = (self._current_node[1]
                      if self._current_node[0] != "model"
                      else self._current_node[2])
                blocks = [lb]
            else:
                blocks = self.lib_file.lib_blocks   # 기본: 전체

            # ── 순회하며 값 교체 ──
            for lb in blocks:
                for model in lb.models:
                    if p_name in model.params:
                        model.params[p_name] = p_value
                        count += 1

            messagebox.showinfo("적용 완료",
                                f"총 {count}개의 모델에서 '{p_name}' 값이 변경되었습니다.")

            # 현재 선택된 뷰 갱신 (우측 테이블 업데이트)
            if self._current_node:
                self._on_tree_select()

    def _open_param_view(self):
        """
        파라미터 중심 뷰(ParameterViewWindow)를 새 창으로 엽니다.

        파일이 열려있지 않으면 경고 메시지를 표시합니다.
        """
        if not self.lib_file:
            messagebox.showwarning("경고", "열린 파일이 없습니다.")
            return
        ParameterViewWindow(self, self.lib_file)


# ═════════════════════════════════════════════════════════════════════════════
# ParamAddDialog : 파라미터·변수 추가 팝업 다이얼로그
# ═════════════════════════════════════════════════════════════════════════════
class ParamAddDialog(tk.Toplevel):
    """
    새 파라미터(또는 변수·지시어)의 이름과 값을 입력받는 모달 다이얼로그입니다.

    사용 시나리오:
        - MODEL 파라미터 추가
        - PARAM 변수 추가
        - Directive 추가
        - MODEL 이름·타입 변경 (재활용)

    결과:
        self.result = (name: str, value: str)  — 확인 클릭 시
        self.result = None                      — 취소 또는 창 닫기 시

    단축키:
        Enter → 확인(_ok)
        Esc   → 취소(destroy)
    """

    def __init__(self, parent, title="파라미터 추가"):
        super().__init__(parent)
        self.title(title)
        self.result = None       # 확인 시 (name, value) 튜플로 갱신
        self.resizable(False, False)
        self.configure(bg=BG_DARK)
        self.grab_set()          # 모달 동작: 이 창이 열린 동안 부모 창 비활성화
        self._build(title)
        self.transient(parent)   # 부모 창 위에 항상 표시
        self.wait_window()       # 창이 닫힐 때까지 블로킹

    def _build(self, title):
        """
        다이얼로그 UI를 구성합니다.

        구성 요소:
            - 헤더 라벨 (title 텍스트)
            - "이름:" 라벨 + Entry (_name_var)
            - "값:"  라벨 + Entry (_val_var)
            - 수식 사용 안내 문구
            - 확인 / 취소 버튼
        """
        # ── 헤더 ──
        tk.Label(self, text=title, bg=BG_HEADER, fg=FG_ACCENT,
                 font=FONT_TITLE, anchor="w", padx=14, pady=8
                 ).pack(fill=tk.X)

        # ── 입력 폼 ──
        frm = tk.Frame(self, bg=BG_DARK, padx=20, pady=16)
        frm.pack(fill=tk.BOTH)

        # 이름 입력란
        tk.Label(frm, text="이름:", bg=BG_DARK, fg=FG_MAIN, font=FONT_BODY).grid(
            row=0, column=0, sticky="w", pady=6)
        self._name_var = tk.StringVar()
        tk.Entry(frm, textvariable=self._name_var,
                 bg=BG_PANEL, fg=FG_MAIN, insertbackground=FG_MAIN,
                 font=FONT_BODY, relief="flat",
                 highlightthickness=1, highlightcolor=FG_ACCENT,
                 highlightbackground=BORDER, width=28
                 ).grid(row=0, column=1, pady=6, padx=(8, 0))

        # 값 입력란
        tk.Label(frm, text="값:", bg=BG_DARK, fg=FG_MAIN, font=FONT_BODY).grid(
            row=1, column=0, sticky="w", pady=6)
        self._val_var = tk.StringVar()
        tk.Entry(frm, textvariable=self._val_var,
                 bg=BG_PANEL, fg=FG_MAIN, insertbackground=FG_MAIN,
                 font=FONT_BODY, relief="flat",
                 highlightthickness=1, highlightcolor=FG_ACCENT,
                 highlightbackground=BORDER, width=28
                 ).grid(row=1, column=1, pady=6, padx=(8, 0))

        # 수식 사용 안내 문구
        tk.Label(frm,
                 text="※ 수식은 중괄호로: {var_name}  또는  {var_name * 1.1}",
                 bg=BG_DARK, fg=FG_DIM, font=FONT_SMALL
                 ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 6))

        # ── 버튼 ──
        btn_frm = tk.Frame(self, bg=BG_DARK, pady=10)
        btn_frm.pack()
        ttk.Button(btn_frm, text="확인", style="Accent.TButton",
                   command=self._ok).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frm, text="취소", style="Toolbar.TButton",
                   command=self.destroy).pack(side=tk.LEFT, padx=8)

        # 단축키 바인딩
        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _ok(self):
        """
        이름 필드가 비어있지 않으면 result 튜플을 설정하고 창을 닫습니다.
        이름이 비어있으면 경고를 표시합니다.
        """
        name = self._name_var.get().strip()
        val  = self._val_var.get().strip()
        if not name:
            messagebox.showwarning("입력 오류", "이름을 입력하세요.", parent=self)
            return
        self.result = (name, val)
        self.destroy()


# ═════════════════════════════════════════════════════════════════════════════
# BatchEditDialog : 파라미터 일괄 수정 팝업 다이얼로그
# ═════════════════════════════════════════════════════════════════════════════
class BatchEditDialog(tk.Toplevel):
    """
    특정 파라미터 이름을 선택하고 새 값을 입력하여 적용 범위 내의
    모든 모델에 일괄 적용하는 모달 다이얼로그입니다.

    사용 흐름:
        1. 파일 전체에 존재하는 파라미터 이름 목록을 Combobox로 선택합니다.
        2. 새 파라미터 값을 입력합니다.
        3. 적용 범위를 라디오 버튼으로 선택합니다:
               "모든 LIB"         → 파일 내 모든 LIB 블록
               "현재 보고있는 LIB" → 현재 선택된 LIB 블록만
        4. 적용 버튼을 누르면 result 튜플이 설정되고 창이 닫힙니다.

    결과:
        self.result = (p_name: str, p_value: str, scope: str)  — 적용 클릭 시
                      scope: "all" 또는 "lib"
        self.result = None  — 취소 시
    """

    def __init__(self, parent, lib_file: LibFile, current_node):
        super().__init__(parent)
        self.title("일괄 파라미터 수정")
        self.result = None
        self.resizable(False, False)
        self.configure(bg=BG_DARK)
        self.grab_set()
        self.transient(parent)
        self._build(lib_file, current_node)
        self.wait_window()

    def _build(self, lib_file: LibFile, current_node):
        """
        일괄 수정 다이얼로그 UI를 구성합니다.

        구성 요소:
            - 헤더 라벨
            - 대상 파라미터 선택 Combobox (전체 파라미터명 목록)
            - 새 파라미터 값 Entry
            - 적용 범위 RadioButton ("모든 LIB" / "현재 보고있는 LIB")
            - 적용 / 취소 버튼
        """
        # ── 헤더 ──
        tk.Label(self, text="일괄 파라미터 수정",
                 bg=BG_HEADER, fg=FG_ACCENT,
                 font=FONT_TITLE, anchor="w", padx=14, pady=8
                 ).pack(fill=tk.X)

        frm = tk.Frame(self, bg=BG_DARK, padx=20, pady=16)
        frm.pack(fill=tk.BOTH)

        # ── 파라미터 이름 목록 수집 (파일 전체) ──
        all_params = set()
        for lb in lib_file.lib_blocks:
            for model in lb.models:
                all_params.update(model.params.keys())
        p_names = sorted(list(all_params))  # 알파벳 순 정렬

        # 대상 파라미터 선택 Combobox
        tk.Label(frm, text="대상 파라미터:", bg=BG_DARK, fg=FG_MAIN,
                 font=FONT_BODY).grid(row=0, column=0, sticky="w", pady=6)
        self._p_name = tk.StringVar()
        var_combo = ttk.Combobox(frm, textvariable=self._p_name,
                                 values=p_names, width=26, font=FONT_BODY)
        var_combo.grid(row=0, column=1, pady=6, padx=(8, 0))

        # 새 파라미터 값 Entry
        tk.Label(frm, text="새 파라미터 값:", bg=BG_DARK, fg=FG_MAIN,
                 font=FONT_BODY).grid(row=1, column=0, sticky="w", pady=6)
        self._p_val = tk.StringVar()
        tk.Entry(frm, textvariable=self._p_val,
                 bg=BG_PANEL, fg=FG_MAIN, insertbackground=FG_MAIN,
                 font=FONT_BODY, relief="flat",
                 highlightthickness=1, highlightcolor=FG_ACCENT,
                 highlightbackground=BORDER, width=28
                 ).grid(row=1, column=1, pady=6, padx=(8, 0))

        # 적용 범위 RadioButton
        tk.Label(frm, text="적용 범위:",
                 bg=BG_DARK, fg=FG_MAIN, font=FONT_BODY
                 ).grid(row=2, column=0, sticky="w", pady=6)
        self._scope_var = tk.StringVar(value="all")  # 기본: 전체
        rb_frm = tk.Frame(frm, bg=BG_DARK)
        rb_frm.grid(row=2, column=1, sticky="w", pady=6, padx=(8, 0))
        tk.Radiobutton(rb_frm, text="모든 LIB",
                       variable=self._scope_var, value="all",
                       bg=BG_DARK, fg=FG_MAIN, selectcolor=BG_PANEL,
                       font=FONT_BODY).pack(side=tk.LEFT)
        tk.Radiobutton(rb_frm, text="현재 보고있는 LIB",
                       variable=self._scope_var, value="lib",
                       bg=BG_DARK, fg=FG_MAIN, selectcolor=BG_PANEL,
                       font=FONT_BODY).pack(side=tk.LEFT)

        # ── 버튼 ──
        btn_frm = tk.Frame(self, bg=BG_DARK, pady=10)
        btn_frm.pack()
        ttk.Button(btn_frm, text="적용", style="Accent.TButton",
                   command=self._ok).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frm, text="취소", style="Toolbar.TButton",
                   command=self.destroy).pack(side=tk.LEFT, padx=8)

        self.bind("<Return>", lambda e: self._ok())
        self.bind("<Escape>", lambda e: self.destroy())

    def _ok(self):
        """
        파라미터 이름이 비어있지 않으면 result 튜플을 설정하고 창을 닫습니다.
        이름이 비어있으면 경고를 표시합니다.
        """
        p_name = self._p_name.get().strip()
        p_val  = self._p_val.get().strip()
        scope  = self._scope_var.get()
        if not p_name:
            messagebox.showwarning("입력 오류", "이름을 입력하세요.", parent=self)
            return
        self.result = (p_name, p_val, scope)
        self.destroy()


# ═════════════════════════════════════════════════════════════════════════════
# ParameterViewWindow : 파라미터 중심 비교 뷰 창
# ═════════════════════════════════════════════════════════════════════════════
class ParameterViewWindow(tk.Toplevel):
    """
    선택한 파라미터에 대해 모든 모델의 값을 한눈에 비교할 수 있는 별도 창입니다.

    레이아웃:
        ┌──────────────────┬─────────────────────────────────────────────────┐
        │  좌측: 파라미터  │  우측: 해당 파라미터의 LIB/모델별 값 목록       │
        │  목록 (트리뷰)   │  열: LIB명 | MODEL명 | 값                      │
        └──────────────────┴─────────────────────────────────────────────────┘

    동작 방식:
        1. _populate_params()로 파일 전체의 파라미터명을 알파벳 순으로 좌측 트리에 채웁니다.
        2. 좌측에서 파라미터를 선택하면 _on_p_select()가 호출됩니다.
        3. _on_p_select()는 해당 파라미터를 가진 모든 (LIB, MODEL, 값)을 우측 테이블에 표시합니다.
    """

    def __init__(self, parent, lib_file: LibFile):
        super().__init__(parent)
        self.title("파라미터 중심 뷰")
        self.geometry("900x600")
        self.configure(bg=BG_DARK)
        self.lib_file = lib_file
        self._build()

    def _build(self):
        """
        좌우 분할 레이아웃과 트리뷰 위젯을 구성합니다.

        좌측: 파라미터명 트리뷰 (p_tree)
        우측: LIB명·MODEL명·값 3열 트리뷰 (v_tree)
        """
        pw = tk.PanedWindow(self, orient=tk.HORIZONTAL,
                            bg=BORDER, sashwidth=4, sashrelief="flat")
        pw.pack(fill=tk.BOTH, expand=True)

        # ── 좌측: 파라미터 목록 ──
        left = tk.Frame(pw, bg=BG_PANEL, width=250)
        pw.add(left, minsize=150)
        tk.Label(left, text="파라미터 목록",
                 bg=BG_HEADER, fg=FG_ACCENT,
                 font=FONT_TITLE, anchor="w", padx=12, pady=8).pack(fill=tk.X)

        tframe = tk.Frame(left, bg=BG_PANEL)
        tframe.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        vsb1 = ttk.Scrollbar(tframe, orient=tk.VERTICAL)
        vsb1.pack(side=tk.RIGHT, fill=tk.Y)

        # 파라미터명 트리뷰 (단순 목록 형태)
        self.p_tree = ttk.Treeview(tframe, style="Tree.Treeview",
                                   show="tree", yscrollcommand=vsb1.set)
        self.p_tree.pack(fill=tk.BOTH, expand=True)
        vsb1.config(command=self.p_tree.yview)
        self.p_tree.bind("<<TreeviewSelect>>", self._on_p_select)

        # ── 우측: 모델별 값 목록 ──
        right = tk.Frame(pw, bg=BG_DARK)
        pw.add(right, minsize=400)

        self._title_var = tk.StringVar(value="← 파라미터를 선택하세요")
        tk.Label(right, textvariable=self._title_var,
                 bg=BG_HEADER, fg=FG_ACCENT,
                 font=FONT_TITLE, anchor="w", padx=14, pady=8).pack(fill=tk.X)

        rframe = tk.Frame(right, bg=BG_DARK)
        rframe.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        vsb2 = ttk.Scrollbar(rframe, orient=tk.VERTICAL)
        vsb2.pack(side=tk.RIGHT, fill=tk.Y)

        # LIB명 | MODEL명 | 값 비교 트리뷰
        self.v_tree = ttk.Treeview(rframe, style="Param.Treeview",
                                   columns=("lib", "model", "val"),
                                   show="headings",
                                   yscrollcommand=vsb2.set)
        self.v_tree.heading("lib",   text="LIB명",   anchor="w")
        self.v_tree.heading("model", text="MODEL명", anchor="w")
        self.v_tree.heading("val",   text="값",      anchor="w")
        self.v_tree.column("lib",   width=200, anchor="w")
        self.v_tree.column("model", width=200, anchor="w")
        self.v_tree.column("val",   width=200, anchor="w")

        # 홀짝 행 배경색 태그
        self.v_tree.tag_configure("odd",  background=BG_ROW_ODD)
        self.v_tree.tag_configure("even", background=BG_ROW_EVN)

        self.v_tree.pack(fill=tk.BOTH, expand=True)
        vsb2.config(command=self.v_tree.yview)

        # 파라미터 목록 초기 채우기
        self._populate_params()

    def _populate_params(self):
        """
        파일 전체에 존재하는 파라미터 이름을 수집하여 좌측 트리뷰에 알파벳 순으로 채웁니다.

        각 항목의 iid(item id)를 파라미터 이름으로 설정하여
        _on_p_select()에서 별도 매핑 없이 선택된 파라미터명을 직접 가져올 수 있습니다.
        """
        all_params = set()
        for lb in self.lib_file.lib_blocks:
            for model in lb.models:
                all_params.update(model.params.keys())

        for p in sorted(list(all_params)):
            self.p_tree.insert("", "end", text=f"  {p}", iid=p)

    def _on_p_select(self, event=None):
        """
        좌측 트리에서 파라미터를 선택했을 때 우측 비교 테이블을 갱신합니다.

        처리 흐름:
            1. 선택된 파라미터 이름(iid)을 가져옵니다.
            2. 우측 테이블의 기존 행을 모두 삭제합니다.
            3. 파일 전체 모델을 순회하며 해당 파라미터를 가진 행을 추가합니다.
               (LIB명, MODEL명, 파라미터 값, 홀짝 배경 태그)
        """
        sel = self.p_tree.selection()
        if not sel:
            return
        p_name = sel[0]   # iid = 파라미터명

        # 우측 테이블 초기화
        for iid in self.v_tree.get_children():
            self.v_tree.delete(iid)

        # 제목 라벨 갱신
        self._title_var.set(f"파라미터: {p_name}")

        # 해당 파라미터를 보유한 모든 모델 행 추가
        row_idx = 0
        for lb in self.lib_file.lib_blocks:
            for model in lb.models:
                if p_name in model.params:
                    val = model.params[p_name]
                    tag = "odd" if row_idx % 2 == 0 else "even"
                    self.v_tree.insert("", "end",
                                       values=(lb.name, model.name, val),
                                       tags=(tag,))
                    row_idx += 1


# ═════════════════════════════════════════════════════════════════════════════
# 진입점 (Entry Point)
# ═════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = LibEditorApp()
    app.mainloop()
