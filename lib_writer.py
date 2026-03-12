"""
lib_writer.py
LibFile 객체를 Smart Spice 문법의 .lib 텍스트로 직렬화합니다.

긴 파라미터 줄은 + continuation line으로 자동 줄바꿈 (기본 80자).
"""
from data_model import LibFile, LibBlock, ModelEntry, ParamEntry

_LINE_WIDTH = 80


def _format_params(params: dict, indent: str = "+ ") -> list:
    """
    파라미터 dict를 continuation line 형식 문자열 리스트로 반환합니다.
    예:
      + vth0=0.45 tox=1.2e-8
      + level=3
    """
    if not params:
        return []

    items = [f"{k}={v}" for k, v in params.items()]
    lines = []
    current = indent
    for item in items:
        if len(current) + len(item) + 1 > _LINE_WIDTH and current.strip() != '+':
            lines.append(current.rstrip())
            current = indent + item + ' '
        else:
            current += item + ' '
    if current.strip() and current.strip() != '+':
        lines.append(current.rstrip())
    return lines


def _write_param_entries(entries: list) -> list:
    """ParamEntry 리스트를 .PARAM 줄들로 변환합니다."""
    if not entries:
        return []
    lines = []
    current = ".PARAM "
    for e in entries:
        token = f"{e.name}={e.value} "
        if len(current) + len(token) > _LINE_WIDTH and current.strip() != '.PARAM':
            lines.append(current.rstrip())
            current = "+ " + token
        else:
            current += token
    if current.strip() not in ('.PARAM', '+'):
        lines.append(current.rstrip())
    return lines


def write_lib(lib_file: LibFile) -> str:
    """
    LibFile 객체를 Smart Spice .lib 형식의 문자열로 변환합니다.
    """
    out = []

    # 파일 선두 주석
    for c in lib_file.leading_comments:
        out.append(c)

    # 전역 .PARAM
    if lib_file.global_params:
        out.extend(_write_param_entries(lib_file.global_params))
        out.append('')

    # LIB 블록들
    for lb in lib_file.lib_blocks:
        # LIB 앞 주석
        for c in lb.leading_comments:
            out.append(c)

        out.append(f".LIB {lb.name}")

        # LIB 내 .PARAM
        if lb.params:
            out.extend(_write_param_entries(lb.params))

        # MODEL 엔트리들
        for model in lb.models:
            for c in model.comment_lines:
                out.append(c)
            out.append(f".MODEL {model.name} {model.model_type}")
            if model.params:
                out.extend(_format_params(model.params, indent="+ "))

        out.append(f".ENDL {lb.name}")
        out.append('')

    return '\n'.join(out)


def save_lib(lib_file: LibFile, filepath: str = None) -> str:
    """
    LibFile 객체를 파일로 저장합니다.
    filepath가 None이면 lib_file.filepath를 사용합니다.
    저장된 경로를 반환합니다.
    """
    path = filepath or lib_file.filepath
    if not path:
        raise ValueError("저장할 파일 경로가 지정되지 않았습니다.")
    content = write_lib(lib_file)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path
