"""
lib_writer.py
LibFile 객체를 Smart Spice 문법의 .lib 텍스트로 직렬화합니다.

긴 파라미터 줄은 + continuation line으로 자동 줄바꿈 (기본 80자).
"""
from data_model import LibFile, LibBlock, ModelEntry, ParamEntry, DirectiveEntry

_LINE_WIDTH = 80


def _format_params(
    params: dict,
    indent: str = "+ ",
    open_paren: bool = False,
    close_paren: bool = False,
    continuation_comments: dict = None,
) -> list:
    """
    파라미터 딕셔너리를 Smart Spice 문법에 맞는 문자열 리스트(멀티 라인)로 변환합니다.

    특징:
    1. 긴 줄을 `_LINE_WIDTH`(기본 80자) 기준으로 여러 줄로 자동 개행합니다.
    2. 파싱 때 기록해둔 `open_paren`과 `close_paren` 값을 참조하여
       원형처럼 괄호로 파라미터를 감싸서 출력합니다.
    3. continuation_comments 딕셔너리가 제공되면, 각 '+' 줄 끝에
       원본 인라인 주석($ ...)을 복원합니다.
       키는 해당 줄 맨 첫 파라미터 이름(대문자)이어야 합니다.

    예:
      + (vth0=0.45 tox=1.2e-8  $ level/oxide params
      + level=3)
    """
    if continuation_comments is None:
        continuation_comments = {}

    if not params:
        # 파라미터가 없는데 괄호만 있을 수도 있음
        if open_paren and close_paren:
            return [indent + "()"]
        elif open_paren:
            return [indent + "("]
        elif close_paren:
            return [indent + ")"]
        return []

    items = list(params.items())   # [(이름, 값), ...] 원본 순서 유지
    lines = []                     # 완성된 '+' 줄 목록

    current = indent
    if open_paren:
        current += "("

    # 현재 출력 중인 줄의 첫 번째 파라미터 이름 (대문자, 주석 키로 사용)
    current_line_first_key: str = None

    for i, (key, val) in enumerate(items):
        is_last = (i == len(items) - 1)

        # 마지막 항목이고 close_paren이 True이면 ')' 붙임
        token = f"{key}={val}"
        if is_last and close_paren:
            token += ")"

        stripped_cur = current.strip()
        if len(current) + len(token) + 1 > _LINE_WIDTH and stripped_cur not in ('+', '+(', '+ ('):
            # 줄 바꿈: 현재 줄 첫 파라미터명(대문자)으로 주석 조회 후 줄 완성
            comment = continuation_comments.get(
                current_line_first_key.upper() if current_line_first_key else '', ''
            )
            out_line = current.rstrip()
            if comment:
                out_line += '  ' + comment  # 2칸 띄우고 주석 연결
            lines.append(out_line)

            # 새 줄 시작: 이 줄의 첫 파라미터는 현재 key
            current = indent + token + ' '
            current_line_first_key = key
        else:
            if current_line_first_key is None:
                # 이 줄의 첫 파라미터 이름 기록
                current_line_first_key = key
            current += token + ' '

    # 마지막 줄 처리
    if current.strip() and current.strip() not in ('+', '+(', '+ ('):
        comment = continuation_comments.get(
            current_line_first_key.upper() if current_line_first_key else '', ''
        )
        out_line = current.rstrip()
        if comment:
            out_line += '  ' + comment
        lines.append(out_line)

    return lines


def _write_param_entries(entries: list) -> list:
    """
    ParamEntry 객체 리스트를 `.PARAM` 명령어 라인들로 직렬화합니다.
    여러 개의 파라미터가 있을 경우 80자를 넘지 않게 `+` continuation 라인으로 이어서 생성합니다.
    """
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
    메모리에 올려진 `LibFile` 구조 객체를 다시 순수 텍스트(Smart Spice 문법 문자열) 로 변환(직렬화)합니다.
    트리 순서(전역 영역 -> 각 LIB 블록 -> 내부 모델)를 그대로 따르며,
    주석 위치와 .MODEL 사이 빈 줄도 본래대로 복구합니다.
    """
    out = []

    # 파일 선두 주석
    for c in lib_file.leading_comments:
        out.append(c)

    # 전역 .PARAM
    if lib_file.global_params:
        out.extend(_write_param_entries(lib_file.global_params))
        out.append('')

    # 전역 기타 directive
    if lib_file.global_directives:
        for d in lib_file.global_directives:
            out.append(d.raw_text)
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

        # LIB별 기타 directive
        if lb.directives:
            for d in lb.directives:
                out.append(d.raw_text)
            out.append('')

        # MODEL 엔트리들: .MODEL 사이에 빈 줄 한 칸 삽입
        for idx, model in enumerate(lb.models):
            # 두 번째 모델부터 앞에 빈 줄 한 칸 삽입
            if idx > 0:
                out.append('')
            # 모델 선언 앞에 있던 * 주석 복원
            for c in model.comment_lines:
                out.append(c)
            # .MODEL 헤더 출력
            model_header = f".MODEL {model.name} {model.model_type}"
            out.append(model_header)
            # 파라미터 줄 출력 (인라인 주석 복원 포함)
            if model.params or model.open_paren or model.close_paren:
                out.extend(_format_params(
                    model.params,
                    indent="+ ",
                    open_paren=model.open_paren,
                    close_paren=model.close_paren,
                    continuation_comments=model.continuation_comments,
                ))

        out.append(f".ENDL {lb.name}")
        out.append('')

    return '\n'.join(out)


def save_lib(lib_file: LibFile, filepath: str = None) -> str:
    """
    메인 애플리케이션 등에서 호출하는 저장 API입니다.
    텍스트로 변환된 `LibFile`을 실제 로컬 파일 시스템의 경로(`filepath`)에 저장합니다.
    """
    path = filepath or lib_file.filepath
    if not path:
        raise ValueError("저장할 파일 경로가 지정되지 않았습니다.")
    content = write_lib(lib_file)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return path
