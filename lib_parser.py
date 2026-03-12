"""
lib_parser.py
Smart Spice .lib 파일 파서

문법 참조:
  .LIB <libname>
    .MODEL <name> <type>
    + param1=val1 param2=val2 ...
    .PARAM var1=v1 var2=v2
  .ENDL <libname>
  *  주석 (줄 첫 글자가 *)
  $ 인라인 주석
"""
import re
from collections import OrderedDict
from typing import List, Tuple

from data_model import LibFile, LibBlock, ModelEntry, ParamEntry

# 인라인 주석 제거 ($ 이후 제거), 문자열 리터럴 내부 보호
_INLINE_COMMENT_RE = re.compile(r'\$.*$')


def _strip_inline_comment(line: str) -> str:
    """$ 이후의 인라인 주석을 제거합니다 (문자열 외부에서만)."""
    return _INLINE_COMMENT_RE.sub('', line).rstrip()


def _parse_param_pairs(text: str) -> OrderedDict:
    """
    'param1=val1 param2={val2+1} ...' 형식의 문자열을
    OrderedDict({'param1': 'val1', 'param2': '{val2+1}'}) 로 파싱합니다.
    값은 중괄호로 묶인 수식도 포함할 수 있습니다.
    """
    params = OrderedDict()
    text = text.strip()
    if not text:
        return params

    # 토큰 분리: 'name=value' 쌍을 추출 (값이 {} 포함 가능)
    # 예: vth0=0.45 tox={tox_var*1.1} level=3
    pattern = re.compile(
        r'(\w+)\s*=\s*'           # 파라미터 이름과 =
        r'('
        r'\{[^}]*\}'              # 중괄호 수식 {expr}
        r'|'
        r'[^\s={}]+'              # 일반 값 (공백/= 없는 토큰)
        r')'
    )
    for m in pattern.finditer(text):
        name = m.group(1).strip()
        value = m.group(2).strip()
        params[name] = value

    return params


def _join_continuation_lines(raw_lines: List[str]) -> List[str]:
    """
    + 로 시작하는 continuation line을 이전 줄에 합칩니다.
    주석 줄(* 로 시작)은 그대로 유지합니다.
    """
    joined: List[str] = []
    for raw in raw_lines:
        stripped = raw.strip()
        if not stripped:
            joined.append('')
            continue
        if stripped.startswith('+'):
            # continuation: 이전 실질 내용 줄에 이어 붙임
            rest = stripped[1:].strip()
            # 이전 줄을 찾아서 이어붙이기
            if joined:
                joined[-1] = joined[-1].rstrip() + ' ' + rest
            else:
                joined.append(rest)
        else:
            joined.append(stripped)
    return joined


def parse_lib(filepath: str) -> LibFile:
    """
    .lib 파일을 파싱하여 LibFile 객체를 반환합니다.
    """
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        raw_lines = f.readlines()

    lib_file = LibFile(filepath=filepath)

    # 1단계: continuation line 합치기
    lines = _join_continuation_lines(raw_lines)

    # 2단계: 순차 파싱
    current_lib: LibBlock = None
    current_model: ModelEntry = None
    pending_comments: List[str] = []
    in_lib_block = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 빈 줄
        if not stripped:
            i += 1
            continue

        # 주석 줄 (* 시작)
        if stripped.startswith('*'):
            pending_comments.append(stripped)
            i += 1
            continue

        # 인라인 주석 제거
        stripped = _strip_inline_comment(stripped)
        if not stripped:
            i += 1
            continue

        upper = stripped.upper()

        # .LIB 시작
        if upper.startswith('.LIB') and not upper.startswith('.LIBRARY'):
            parts = stripped.split(None, 1)
            lib_name = parts[1].strip() if len(parts) > 1 else 'UNNAMED'
            current_lib = LibBlock(name=lib_name, leading_comments=pending_comments)
            pending_comments = []
            current_model = None
            in_lib_block = True
            i += 1
            continue

        # .ENDL
        if upper.startswith('.ENDL'):
            if current_lib is not None:
                lib_file.lib_blocks.append(current_lib)
            current_lib = None
            current_model = None
            in_lib_block = False
            i += 1
            continue

        # .MODEL
        if upper.startswith('.MODEL'):
            parts = stripped.split(None, 3)
            # .MODEL <name> <type> [params...]
            model_name = parts[1] if len(parts) > 1 else 'UNKNOWN'
            model_type = parts[2] if len(parts) > 2 else ''
            param_text = parts[3] if len(parts) > 3 else ''
            model_params = _parse_param_pairs(param_text)
            current_model = ModelEntry(
                name=model_name,
                model_type=model_type,
                params=model_params,
                comment_lines=pending_comments,
            )
            pending_comments = []
            if current_lib is not None:
                current_lib.models.append(current_model)
            i += 1
            continue

        # .PARAM
        if upper.startswith('.PARAM'):
            param_text = stripped[6:].strip()  # .PARAM 이후 텍스트
            pairs = _parse_param_pairs(param_text)
            entries = [ParamEntry(name=k, value=v) for k, v in pairs.items()]
            if in_lib_block and current_lib is not None:
                current_lib.params.extend(entries)
            else:
                lib_file.global_params.extend(entries)
            pending_comments = []
            i += 1
            continue

        # 그 외 줄 (무시하거나 보존)
        i += 1

    # 파일 최상단 주석
    lib_file.leading_comments = []

    return lib_file
