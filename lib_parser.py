"""
lib_parser.py
─────────────────────────────────────────────────────────────────────────────
Smart Spice .lib 파일을 읽어 LibFile 데이터 구조로 파싱하는 모듈입니다.

지원 문법 참조:
    .LIB <libname>          : 라이브러리 블록 시작
      .PARAM var=val ...    : 변수 선언
      .MODEL <name> <type>  : 모델 선언
      + param1=val1 ...     : continuation line (이전 줄 이어받기)
    .ENDL <libname>         : 라이브러리 블록 종료
    *  주석 (줄 첫 글자가 *)
    $  인라인 주석 (줄 중간에 $가 나타나면 이후는 주석)

파싱 2단계 처리:
    [1단계] _join_continuation_lines():
              '+' 로 시작하는 continuation line을 이전 줄에 합칩니다.
              이 때 인라인 주석($ ...)은 분리하여 별도 맵에 저장합니다.
    [2단계] parse_lib() 본문:
              합쳐진 줄을 순서대로 스캔하면서 .LIB / .ENDL / .MODEL /
              .PARAM / 기타 지시어 / 주석 을 인식하고 LibFile 객체에 채웁니다.

공개 인터페이스:
    parse_lib(filepath) → LibFile
─────────────────────────────────────────────────────────────────────────────
"""
import re
from collections import OrderedDict
from typing import List, Tuple

from data_model import LibFile, LibBlock, ModelEntry, ParamEntry, DirectiveEntry

# ── 정규식 상수 ──────────────────────────────────────────────────────────────

# 줄에서 $ 이후 인라인 주석 전체를 찾는 정규식
_INLINE_COMMENT_RE = re.compile(r'\$.*$')

# continuation line(+)의 내용 중 첫 번째 "파라미터명=" 을 찾는 정규식
# 인라인 주석을 해당 줄의 첫 파라미터명에 연결(키)하기 위해 사용합니다.
_FIRST_PARAM_RE = re.compile(r'(\w+)\s*=')


def _strip_inline_comment(line: str) -> str:
    """
    줄 문자열에서 $ 이후의 인라인 주석을 제거하고, 나머지 내용(우측 공백 제거)을 반환합니다.

    예:
        ".MODEL NMOS_1 NMOS  $ fast corner"  →  ".MODEL NMOS_1 NMOS"
        "+ VTH0=0.45  $ threshold"           →  "+ VTH0=0.45"

    Args:
        line (str): 처리할 줄 문자열

    Returns:
        str: $ 이후 주석이 제거된 줄 (우측 공백 제거 적용)
    """
    return _INLINE_COMMENT_RE.sub('', line).rstrip()


def _extract_inline_comment(line: str) -> str:
    """
    줄 문자열에서 $ 이후의 인라인 주석 문자열만 추출하여 반환합니다.
    인라인 주석이 없으면 빈 문자열을 반환합니다.

    예:
        "+ K1=0.559  $ mobility"  →  "$ mobility"
        "+ VTH0=0.45"              →  ""

    Args:
        line (str): 처리할 줄 문자열

    Returns:
        str: "$ ..." 형태의 주석 문자열, 없으면 ""
    """
    m = _INLINE_COMMENT_RE.search(line)
    return m.group(0).strip() if m else ''


def _parse_param_pairs(text: str) -> tuple[OrderedDict, bool, bool]:
    """
    'param1=val1 param2={val2+1} ...' 형식의 파라미터 텍스트를 파싱하여
    OrderedDict 와 괄호 존재 여부(open/close)를 함께 반환합니다.

    이 함수는 다음 두 상황에서 호출됩니다:
        1. .MODEL 줄 또는 합쳐진 continuation 줄의 파라미터 파싱
        2. .PARAM 줄의 변수 선언 파싱

    괄호 처리:
        파라미터 리스트 전체가 괄호로 둘러싸일 수 있습니다.
        예: "(VTH0=0.4 TOX=1e-8)"
        이 경우 괄호를 벗겨내고 open_paren / close_paren 플래그를 True로 설정합니다.
        저장 시 _format_params()에서 이 플래그를 참조하여 괄호를 복원합니다.

    값 형식 지원:
        - 단순 숫자  : "0.45", "1.2e-8"
        - 중괄호 수식: "{tox_var}", "{vth_offset * 1.1}"

    정규식 패턴:
        r'(\w+)\s*=\s*(\{[^}]*\}|[^\s={}]+)'
        → 이름(1그룹) = 값(2그룹: 중괄호 수식 또는 일반 토큰)

    Args:
        text (str): 파싱할 파라미터 텍스트 문자열
                    예: "VTH0=0.45 TOX={tox_global} K1=0.559"

    Returns:
        tuple:
            [0] OrderedDict : { '파라미터명': '값' } — 선언 순서 유지
            [1] bool        : open_paren  (시작 '(' 존재 여부)
            [2] bool        : close_paren (끝   ')' 존재 여부)
    """
    params = OrderedDict()
    text = text.strip()

    # ── 앞/뒤 괄호 검사 및 제거 ──
    open_paren = False
    close_paren = False

    if text.startswith('('):
        open_paren = True
        text = text[1:].strip()   # 여는 괄호 제거

    if text.endswith(')'):
        close_paren = True
        text = text[:-1].strip()  # 닫는 괄호 제거

    if not text:
        return params, open_paren, close_paren

    # ── 파라미터 쌍 추출 정규식 ──
    # 그룹1: 파라미터 이름 (영숫자·밑줄 조합)
    # 그룹2: 값 — 중괄호 수식 "{...}" 또는 공백·등호·중괄호가 없는 일반 토큰
    pattern = re.compile(
        r'(\w+)\s*=\s*'           # 파라미터 이름과 등호(=)
        r'('
        r'\{[^}]*\}'              # 중괄호로 감싸인 수식 (예: {var + 1})
        r'|'
        r'[^\s={}]+'              # 일반 숫자·문자열 토큰 (공백·=·{} 미포함)
        r')'
    )

    for m in pattern.finditer(text):
        name  = m.group(1).strip()
        value = m.group(2).strip()

        # 값 끝에 ')' 가 혼재하는 경우 제거 (괄호가 값 토큰에 붙어있는 엣지 케이스)
        if value.endswith(')'):
            value = value[:-1]
            close_paren = True

        params[name] = value

    return params, open_paren, close_paren


def _join_continuation_lines(raw_lines: List[str]) -> Tuple[List[str], dict]:
    """
    파일 원文 줄 목록에서 + 로 시작하는 continuation line을 이전 줄에 합칩니다.

    Smart Spice에서 긴 파라미터 줄은 다음 줄 맨 앞에 `+` 를 써서 이어받습니다.
    이 함수는 그것을 역방향으로 처리하여, 여러 줄에 나눠진 파라미터 선언을
    하나의 긴 줄로 합칩니다.

    추가로, 각 continuation 줄 끝의 인라인 주석($ ...)을 파라미터 내용과 분리하고,
    그 줄의 첫 번째 파라미터 이름(대문자)을 키로 사용하는 딕셔너리에 저장합니다.

    인라인 주석을 파라미터명 키로 저장하는 이유:
        저장(write_lib) 시 80자 기준으로 줄이 재분배되기 때문에 줄 인덱스(0, 1, ...)는
        신뢰할 수 없습니다. 파라미터 이름은 모델 내에서 고유하므로, 해당 파라미터가
        처음 등장하는 줄 끝에 주석을 정확히 복원할 수 있습니다.

    처리 규칙:
        - '+' 로 시작하는 줄: 주석 분리 → 내용을 직전 줄에 연결
        - '*' 로 시작하는 줄: 주석 줄 그대로 유지
        - 빈 줄             : 빈 문자열로 유지
        - 나머지            : 그대로 유지

    Args:
        raw_lines (List[str]): 파일에서 읽은 원문 줄 목록

    Returns:
        tuple:
            [0] List[str]: continuation 처리가 완료된 줄 목록
            [1] dict     : { "첫_파라미터명(대문자)": "$ 주석 문자열" }
                           예: {"VTH0": "$ threshold params", "K1": "$ mobility"}
    """
    joined: List[str] = []
    # { 첫 파라미터명(대문자) → 인라인 주석 문자열 }
    cont_comment_map: dict = {}

    for raw in raw_lines:
        stripped = raw.strip()

        # 빈 줄 처리
        if not stripped:
            joined.append('')
            continue

        if stripped.startswith('+'):
            # ── continuation line 처리 ──
            # [1] 인라인 주석($) 추출
            inline_comment = _extract_inline_comment(stripped)
            # [2] '+' 와 인라인 주석을 제거하여 순수 파라미터 텍스트만 남김
            rest = _strip_inline_comment(stripped[1:].strip())

            # [3] 직전 줄에 이어 붙이기 (직전 줄이 없으면 새 줄로 추가)
            if joined:
                joined[-1] = joined[-1].rstrip() + ' ' + rest
            else:
                joined.append(rest)

            # [4] 인라인 주석이 있으면 이 줄의 첫 파라미터명을 키로 저장
            if inline_comment and rest:
                clean_rest = rest.strip().lstrip('(')  # 여는 괄호를 제거한 후 파라미터명 탐색
                m = _FIRST_PARAM_RE.match(clean_rest)
                if m:
                    key = m.group(1).upper()  # 대문자로 통일하여 저장
                    # 동일 키가 이미 있으면 덮어쓰지 않음 (첫 번째 등장 우선)
                    cont_comment_map.setdefault(key, inline_comment)
        else:
            # continuation이 아닌 일반 줄: 그대로 추가
            joined.append(stripped)

    return joined, cont_comment_map


def parse_lib(filepath: str) -> LibFile:
    """
    지정된 경로의 .lib 파일을 읽어 LibFile 객체로 파싱합니다.

    파싱 흐름:
        [1] 파일 전체를 줄 단위로 읽고, _join_continuation_lines()로
            '+' continuation 줄을 병합하면서 인라인 주석 맵도 생성합니다.

        [2] 병합된 줄 목록을 위에서 아래로 한 줄씩 스캔하며 패턴을 인식합니다:
            ── 빈 줄         : 건너뜀
            ── * 주석 줄     : pending_comments 버퍼에 누적
            ── .LIB          : 새 LibBlock 생성, in_lib_block=True
            ── .ENDL         : 현재 LibBlock을 lib_file.lib_blocks에 추가, 상태 초기화
            ── .MODEL        : 새 ModelEntry 생성, 현재 LibBlock에 추가
            ── .PARAM        : ParamEntry 생성, 현재 스코프(전역/LIB 블록)에 추가
            ── 기타 . 지시어 : DirectiveEntry 생성, 현재 스코프에 추가
            ── 그 외 줄      : 무시(건너뜀)

        [3] pending_comments에 누적된 * 주석은 바로 다음 인식된 블록/모델에 귀속됩니다.

    인라인 주석 처리:
        cont_comment_map에서 .MODEL의 파라미터명과 일치하는 키를 필터링하여
        해당 ModelEntry의 continuation_comments 에 저장합니다.
        사용된 키는 맵에서 제거하여 다음 모델에 주석이 누출되지 않도록 합니다.

    Args:
        filepath (str): 파싱할 .lib 파일의 절대(또는 상대) 경로

    Returns:
        LibFile: 파일 전체가 파싱된 데이터 구조 객체
    """
    # ── 파일 읽기 ──
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw_lines = f.readlines()

    lib_file = LibFile(filepath=filepath)

    # ── [1단계] continuation line 병합 + 인라인 주석 맵 생성 ──
    lines, cont_comment_map = _join_continuation_lines(raw_lines)

    # ── [2단계] 순차 파싱 초기 상태 ──
    current_lib: LibBlock = None      # 현재 처리 중인 LIB 블록 객체
    current_model: ModelEntry = None  # 현재 처리 중인 MODEL 객체 (미사용, 구조 확장 대비)
    pending_comments: List[str] = []  # 다음 블록/모델에 귀속시킬 * 주석 버퍼
    in_lib_block = False              # 현재 .LIB … .ENDL 내부에 있는지 여부

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ── 빈 줄 건너뜀 ──
        if not stripped:
            i += 1
            continue

        # ── * 주석 줄: pending_comments 버퍼에 누적 ──
        # 다음으로 인식되는 블록(.LIB) 또는 모델(.MODEL)의 comment_lines 에 귀속됩니다.
        if stripped.startswith('*'):
            pending_comments.append(stripped)
            i += 1
            continue

        # ── 인라인 주석($) 제거 ──
        # 이미 1단계에서 continuation 줄에 대해 처리했지만,
        # 일반 줄에 있는 인라인 주석도 여기서 제거합니다.
        stripped = _strip_inline_comment(stripped)
        if not stripped:
            i += 1
            continue

        upper = stripped.upper()   # 키워드 비교는 대소문자 무시

        # ────────────────────────────────────────────────────────────────────
        # [조건 1] .LIB 시작 지시어 처리
        # 주의: .LIBRARY 는 외부 라이브러리 참조 구문이므로 .LIB 와 구분합니다.
        # ────────────────────────────────────────────────────────────────────
        if upper.startswith('.LIB') and not upper.startswith('.LIBRARY'):
            parts = stripped.split(None, 1)
            lib_name = parts[1].strip() if len(parts) > 1 else 'UNNAMED'

            # 새 LibBlock 객체 생성 — 누적된 주석을 leading_comments로 귀속
            current_lib = LibBlock(name=lib_name, leading_comments=pending_comments)
            pending_comments = []   # 주석 버퍼 초기화
            current_model = None
            in_lib_block = True
            i += 1
            continue

        # ────────────────────────────────────────────────────────────────────
        # [조건 2] .ENDL (라이브러리 블록 종료) 처리
        # ────────────────────────────────────────────────────────────────────
        if upper.startswith('.ENDL'):
            if current_lib is not None:
                # 완성된 LIB 블록을 파일 구조에 추가
                lib_file.lib_blocks.append(current_lib)

            # 상태 초기화: 다음 .LIB 블록 또는 전역 영역 처리 준비
            current_lib = None
            current_model = None
            in_lib_block = False
            i += 1
            continue

        # ────────────────────────────────────────────────────────────────────
        # [조건 3] .MODEL 처리
        # 형식: .MODEL <name> <type> [param1=val1 ...]
        # ────────────────────────────────────────────────────────────────────
        if upper.startswith('.MODEL'):
            parts = stripped.split(None, 3)          # 최대 4개 토큰으로 분리
            model_name  = parts[1] if len(parts) > 1 else 'UNKNOWN'
            model_type  = parts[2] if len(parts) > 2 else ''
            param_text  = parts[3] if len(parts) > 3 else ''

            # 모델 타입에 '(' 가 붙어있는 경우 분리 (예: .MODEL NMOS_1 (NMOS ...)
            m_open_paren = False
            if '(' in model_type:
                model_type = model_type.replace('(', '').strip()
                m_open_paren = True

            # 파라미터 텍스트 가장 앞의 '(' 처리
            if param_text.startswith('('):
                param_text = param_text[1:].strip()
                m_open_paren = True

            # 파라미터 텍스트 파싱 (내부 괄호·값 처리)
            model_params, p_open, p_close = _parse_param_pairs(param_text)

            # ── 인라인 주석 필터링 ──
            # cont_comment_map에서 이 모델의 파라미터명과 일치하는 항목만 추출합니다.
            # 사용된 키는 맵에서 제거하여 다음 모델에 주석이 누출되지 않도록 합니다.
            param_keys_upper = {p.upper() for p in model_params.keys()}
            model_cont_comments = {}
            for k in list(cont_comment_map.keys()):
                if k in param_keys_upper:
                    model_cont_comments[k] = cont_comment_map.pop(k)  # 맵에서 소비

            # ModelEntry 생성 — 누적된 * 주석을 comment_lines로 귀속
            current_model = ModelEntry(
                name=model_name,
                model_type=model_type,
                params=model_params,
                comment_lines=pending_comments,
                open_paren=m_open_paren or p_open,  # 어느 쪽에서든 '(' 발견 시 True
                close_paren=p_close,
                continuation_comments=model_cont_comments
            )
            pending_comments = []   # 주석 버퍼 초기화

            # 현재 LIB 블록에 모델 추가
            if current_lib is not None:
                current_lib.models.append(current_model)
            i += 1
            continue

        # ────────────────────────────────────────────────────────────────────
        # [조건 4] .PARAM 처리
        # 형식: .PARAM var1=val1 var2=val2 ...
        # ────────────────────────────────────────────────────────────────────
        if upper.startswith('.PARAM'):
            param_text = stripped[6:].strip()             # ".PARAM " 이후 텍스트
            pairs, _, _ = _parse_param_pairs(param_text)  # 이름=값 쌍 파싱
            entries = [ParamEntry(name=k, value=v) for k, v in pairs.items()]

            # 현재 스코프(LIB 블록 내부 또는 전역)에 따라 귀속 위치 결정
            if in_lib_block and current_lib is not None:
                current_lib.params.extend(entries)    # LIB 블록 내부 .PARAM
            else:
                lib_file.global_params.extend(entries) # 전역 .PARAM

            pending_comments = []
            i += 1
            continue

        # ────────────────────────────────────────────────────────────────────
        # [조건 5] 기타 .(dot) 으로 시작하는 지시어 처리
        # .PARAM / .MODEL / .LIB / .ENDL 이외의 지시어를 원문 그대로 보존합니다.
        # 예: .temp 27, .global vdd, .options scale=1e-6
        # ────────────────────────────────────────────────────────────────────
        if stripped.startswith('.'):
            parts = stripped.split(None, 1)
            keyword = parts[0]   # 첫 번째 단어 (.temp, .global 등)
            directive_entry = DirectiveEntry(keyword=keyword, raw_text=stripped)

            if in_lib_block and current_lib is not None:
                current_lib.directives.append(directive_entry)
            else:
                lib_file.global_directives.append(directive_entry)
            i += 1
            continue

        # ── 그 외 처리되지 않은 줄 → 무시하고 다음 줄로 이동 ──
        i += 1

    # ── 파일 최상단 주석 귀속 ──
    # .LIB 블록이 하나도 없는 파일에서 pending_comments가 남아 있으면
    # LibFile.leading_comments 에 귀속시킵니다.
    if not lib_file.lib_blocks and pending_comments:
        lib_file.leading_comments = pending_comments

    return lib_file
