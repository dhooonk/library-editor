"""
data_model.py
─────────────────────────────────────────────────────────────────────────────
Smart Spice LIB 파일의 데이터 모델(데이터 클래스) 정의 모듈입니다.

이 모듈은 .lib 파일 전체를 메모리에 올릴 때 사용하는 계층적 데이터 구조를
Python dataclass로 정의합니다.

계층 구조:
    LibFile  (파일 전체)
    └─ LibBlock  (.LIB … .ENDL 한 쌍)
       ├─ ParamEntry    (.PARAM 변수 하나)
       ├─ DirectiveEntry (기타 지시어 한 줄)
       └─ ModelEntry    (.MODEL 블록 하나)
          └─ params: OrderedDict  (파라미터 이름 → 값)

의존성:
    - collections.OrderedDict : 파라미터 선언 순서를 보존합니다.
    - dataclasses             : 간결한 데이터 클래스 선언에 사용합니다.
    - typing                  : 타입 힌트 제공용입니다.
─────────────────────────────────────────────────────────────────────────────
"""
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# ParamEntry : .PARAM 선언의 단일 변수 하나를 표현하는 데이터 클래스
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ParamEntry:
    """
    .PARAM 선언의 단일 변수를 나타내는 데이터 클래스입니다.

    Smart Spice에서 .PARAM은 전역 또는 LIB 블록 내부에 선언할 수 있는
    파라미터 변수로, 모델 파라미터 값을 유연하게 제어하는 데 활용됩니다.

    예시:
        .PARAM tox_val=1.2e-8
        → name  = "tox_val"
        → value = "1.2e-8"

    Attributes:
        name  (str): 파라미터 이름 (예: "tox_val")
        value (str): 파라미터 값 문자열.
                     단순 숫자("1.2e-8"), 수식 참조("{tox_offset * 1.1}") 등
                     모든 형태를 문자열로 그대로 보관합니다.
    """
    name: str
    value: str  # 파라미터 값 (단순 숫자, 수식 {vth_offset * 1.1} 등 모두 문자열로 보관)


# ─────────────────────────────────────────────────────────────────────────────
# DirectiveEntry : .PARAM · .MODEL · .LIB · .ENDL 이외의 기타 지시어 한 줄
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class DirectiveEntry:
    """
    정의된 구조(.PARAM, .MODEL, .LIB, .ENDL) 이외의 기타
    .(dot) 시작 지시어 명령줄을 저장하는 클래스입니다.

    파일을 파싱·저장할 때 알 수 없는 지시어를 손실 없이
    원문 그대로 보존하기 위해 사용됩니다.

    예시:
        .temp 27        → keyword=".temp",  raw_text=".temp 27"
        .global vdd     → keyword=".global", raw_text=".global vdd"

    Attributes:
        keyword  (str): 지시어의 첫 번째 단어 (예: ".temp", ".global")
        raw_text (str): 줄 전체 원문 텍스트 (예: ".temp 27")
    """
    keyword: str       # 분석된 지시어 첫번째 단어 (예: ".temp")
    raw_text: str      # 줄 전체 원문 텍스트 (예: ".temp 27")


# ─────────────────────────────────────────────────────────────────────────────
# ModelEntry : .MODEL 명령 하나와 그 하위 파라미터 목록
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class ModelEntry:
    """
    .MODEL 명령 하나와 그 하위에 종속된 파라미터 목록을 나타내는 데이터 클래스입니다.

    Smart Spice의 .MODEL 구문 예시:
        * 이것은 NMOS 모델입니다          ← comment_lines
        .MODEL NMOS_1 NMOS               ← name="NMOS_1", model_type="NMOS"
        + (VTH0=0.45 TOX=1.2e-8          ← open_paren=True
        +  K1=0.559)  $ mobility params  ← close_paren=True, cont_comment

    저장 시 원본 파일의 포맷(괄호·주석 위치)을 그대로 복원합니다.

    Attributes:
        name                 (str)         : 모델명 (예: "NMOS_1")
        model_type           (str)         : 모델 타입 (예: "NMOS", "PMOS")
        params               (OrderedDict) : { '파라미터명': '값' } – 선언 순서 유지
        comment_lines        (List[str])   : .MODEL 선언 윗부분의 * 주석 줄 목록
        open_paren           (bool)        : 파라미터 리스트 시작의 '(' 존재 여부
        close_paren          (bool)        : 파라미터 리스트 끝의 ')' 존재 여부
        continuation_comments(dict)        : '+' continuation 줄별 인라인 주석
                                             키: 해당 줄 첫 파라미터명(대문자)
                                             값: "$ ..." 형태의 주석 문자열
                                             예: {"VTH0": "$ threshold",
                                                  "K1":   "$ mobility params"}
    """
    name: str                            # 모델명 (예: "NMOS_1")
    model_type: str                      # 모델 타입 (예: "NMOS" 또는 "PMOS")
    params: OrderedDict = field(default_factory=OrderedDict)
    # params: { '파라미터명': '값', ... } - 순서를 유지하는 딕셔너리
    comment_lines: List[str] = field(default_factory=list)  # 모델 선언 윗부분에 적혀있던 주석 목록
    open_paren: bool = False             # 타입명 뒤 또는 파라미터 리스트 맨 앞에 여는 형식의 괄호 '(' 가 있었는지 여부
    close_paren: bool = False            # 파라미터 리스트 맨 끝에 닫는 형식의 괄호 ')' 가 있었는지 여부
    # continuation_comments: 각 '+' 파라미터 줄별 인라인 주석 목록
    # 키: 해당 continuation line의 첫 번째 파라미터명(대문자), 값: '$ ...' 형태의 주석 문자열
    # 예: {"VTH0": "$ level and threshold", "K1": "$ mobility params"}
    continuation_comments: dict = field(default_factory=dict)

    def copy(self) -> "ModelEntry":
        """
        현재 ModelEntry 객체의 깊은 복사본을 생성하여 반환합니다.
        params(OrderedDict)와 comment_lines(list),
        continuation_comments(dict)를 독립적으로 복사하여
        원본 데이터와 분리된 새 객체를 돌려줍니다.
        """
        return ModelEntry(
            name=self.name,
            model_type=self.model_type,
            params=OrderedDict(self.params),            # 얕은 복사 (값이 문자열이므로 충분)
            comment_lines=list(self.comment_lines),     # 리스트 복사
            open_paren=self.open_paren,
            close_paren=self.close_paren,
            continuation_comments=dict(self.continuation_comments)  # 딕셔너리 복사
        )


# ─────────────────────────────────────────────────────────────────────────────
# LibBlock : .LIB … .ENDL 한 쌍으로 구성된 하나의 라이브러리 블록
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class LibBlock:
    """
    .LIB 부터 .ENDL 까지 묶이는 하나의 독립된 라이브러리 블록을 나타냅니다.

    Smart Spice 모델 파일은 여러 개의 LIB 블록으로 내용을 그룹화합니다.
    각 블록은 고유한 이름(name)을 가지며, 내부에 여러 .MODEL,
    .PARAM 변수, 기타 지시어를 포함할 수 있습니다.

    예시:
        .LIB NMOS_TT
          .PARAM vth_offset=0.05
          .MODEL NMOS_V1 NMOS
          + VTH0=0.45
        .ENDL NMOS_TT

    Attributes:
        name             (str)               : LIB 블록 이름 (예: "NMOS_TT")
        models           (List[ModelEntry])  : 블록 내부에 속한 .MODEL 목록
        params           (List[ParamEntry])  : 블록 내부에서 선언된 .PARAM 목록
        directives       (List[DirectiveEntry]): .PARAM 외 기타 지시어 목록
        leading_comments (List[str])         : .LIB 선언부 윗부분의 블록 주석 목록
    """
    name: str                                            # LIB 블록 이름
    models: List[ModelEntry] = field(default_factory=list)     # 블록 내부에 속한 .MODEL 배열
    params: List[ParamEntry] = field(default_factory=list)     # 블록 내부에서 선언된 .PARAM 변수 배열
    directives: List[DirectiveEntry] = field(default_factory=list)
    # .PARAM 외에 블록 내부에 속한 여러 지시어 명령어들
    leading_comments: List[str] = field(default_factory=list)
    # .LIB 선언부 윗부분에 적혀있던 블록 주석들

    def find_model(self, name: str) -> Optional[ModelEntry]:
        """
        이 LIB 블록 안에서 모델명(대소문자 무시)으로 ModelEntry를 검색합니다.

        Args:
            name (str): 검색할 모델명

        Returns:
            ModelEntry: 찾은 경우 해당 ModelEntry 객체
            None      : 해당 이름의 모델이 없는 경우
        """
        for m in self.models:
            if m.name.upper() == name.upper():
                return m
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LibFile : 파싱된 .lib 파일 전체를 최상단에서 관리하는 루트 데이터 구조
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class LibFile:
    """
    파싱된 하나의 .lib 파일 전체를 루트 레벨에서 관리하는 최상단 데이터 구조입니다.

    파일 전체는 크게 두 영역으로 나뉩니다:
        1. 전역 영역 (global_*)  : .LIB 블록 바깥에 선언된 변수·지시어
        2. LIB 블록 영역         : .LIB … .ENDL 로 묶인 개별 라이브러리

    Attributes:
        filepath          (str)                 : 현재 파싱/저장된 원본 파일 경로
        global_params     (List[ParamEntry])    : 전역 레벨에 선언된 .PARAM 목록
        global_directives (List[DirectiveEntry]): 전역 레벨의 기타 지시어 목록
        lib_blocks        (List[LibBlock])      : 파일 내의 모든 .LIB 블록 목록
        leading_comments  (List[str])           : 파일 최상단(가장 윗줄)에 있는 주석 목록
    """
    filepath: str = ""                                               # 현재 파싱/저장된 원본 파일 경로
    global_params: List[ParamEntry] = field(default_factory=list)    # 전역 레벨에 설정된 .PARAM 들
    global_directives: List[DirectiveEntry] = field(default_factory=list)
    # 전역 레벨에 설정된 기타 지시어 명령들 (.temp 등)
    lib_blocks: List[LibBlock] = field(default_factory=list)         # 파일 안의 모든 .LIB 블록들 모음
    leading_comments: List[str] = field(default_factory=list)
    # 가장 윗단 파일 첫머리에 적혀있는 요약/설명 주석들 모음

    def find_lib(self, name: str) -> Optional[LibBlock]:
        """
        이름(대소문자 무시)으로 LIB 블록을 검색합니다.

        Args:
            name (str): 검색할 LIB 블록 이름

        Returns:
            LibBlock: 찾은 경우 해당 LibBlock 객체
            None    : 해당 이름의 블록이 없는 경우
        """
        for lb in self.lib_blocks:
            if lb.name.upper() == name.upper():
                return lb
        return None

    def all_params(self) -> List[ParamEntry]:
        """
        전역 .PARAM과 모든 LIB 블록 내부 .PARAM을 합산하여 반환합니다.

        Returns:
            List[ParamEntry]: 전역 + 각 LIB 블록의 ParamEntry 전체 목록
        """
        result = list(self.global_params)     # 전역 .PARAM 복사
        for lb in self.lib_blocks:
            result.extend(lb.params)          # 각 LIB 블록 .PARAM 추가
        return result
