"""
lib_writer.py
─────────────────────────────────────────────────────────────────────────────
LibFile 객체를 Smart Spice 문법의 .lib 텍스트로 직렬화(Serialize)하는 모듈입니다.

역할:
    lib_parser.py 가 파일을 읽어 메모리(LibFile)에 올리면,
    이 모듈은 그 역과정 — 메모리 → 텍스트 문자열 → 파일 저장 — 을 담당합니다.

주요 처리:
    - 긴 파라미터 줄은 `+ ` continuation line으로 자동 줄바꿈 (기본 80자 기준)
    - 원본에 있던 괄호 ( ) 구조, * 주석, $ 인라인 주석을 그대로 복원
    - .MODEL 블록 사이에 빈 줄을 삽입하여 가독성 유지

공개 인터페이스:
    write_lib(lib_file) → str         : LibFile → 순수 텍스트 문자열
    save_lib(lib_file, filepath) → str: LibFile → 파일 저장 후 경로 반환
─────────────────────────────────────────────────────────────────────────────
"""
from data_model import LibFile, LibBlock, ModelEntry, ParamEntry, DirectiveEntry

# ── 출력 줄 최대 폭 (기본 80자, Smart Spice 관행) ──
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

    이 함수는 .MODEL 블록의 파라미터 줄(continuation line)을 생성할 때 사용됩니다.
    파라미터가 많아서 한 줄에 다 쓰기 어려울 경우, _LINE_WIDTH 기준으로 자동 줄바꿈하여
    각 줄 앞에 `+ ` 접두사를 붙인 Smart Spice continuation 형식으로 출력합니다.

    처리 로직:
        1. open_paren이 True이면 첫 줄 indent 직후에 '(' 를 붙입니다.
        2. 각 파라미터 토큰("이름=값")을 현재 줄에 추가합니다.
        3. 추가 시 줄 길이가 _LINE_WIDTH를 초과하면:
              현재 줄을 리스트에 저장하고 새 줄을 시작합니다.
        4. close_paren이 True이면 마지막 파라미터 토큰 끝에 ')' 를 붙입니다.
        5. continuation_comments가 제공되면 각 줄 끝에 원본 인라인 주석을 복원합니다.
           (키: 해당 줄의 첫 번째 파라미터명 대문자 → 값: "$ ..." 주석 문자열)

    Args:
        params               (dict) : { 파라미터명: 값 } — 순서가 보존된 OrderedDict
        indent               (str)  : continuation 줄 앞에 붙이는 접두사 (기본 "+ ")
        open_paren           (bool) : 파라미터 리스트 시작에 '(' 를 붙일지 여부
        close_paren          (bool) : 파라미터 리스트 끝에 ')' 를 붙일지 여부
        continuation_comments(dict) : { "파라미터명(대문자)": "$ 주석 문자열" }
                                      각 '+' 줄 끝에 인라인 주석을 복원할 때 사용합니다.

    Returns:
        list: Smart Spice 문법의 continuation line 문자열 목록
              예: ["+ (VTH0=0.45 TOX=1.2e-8  $ threshold",
                   "+  K1=0.559)  $ mobility"]

    예시 출력 (open_paren=True, close_paren=True):
        + (vth0=0.45 tox=1.2e-8  $ level/oxide params
        + level=3)
    """
    if continuation_comments is None:
        continuation_comments = {}

    # 파라미터가 없을 때 괄호만 출력하는 예외 처리
    if not params:
        if open_paren and close_paren:
            return [indent + "()"]
        elif open_paren:
            return [indent + "("]
        elif close_paren:
            return [indent + ")"]
        return []

    items = list(params.items())   # [(이름, 값), ...] 원본 순서 유지
    lines = []                     # 완성된 '+' 줄 목록

    # 현재 작성 중인 줄 버퍼 초기화
    current = indent
    if open_paren:
        current += "("   # 첫 줄에 여는 괄호 추가

    # 현재 줄의 첫 파라미터 이름 (인라인 주석 조회 키로 사용)
    current_line_first_key: str = None

    for i, (key, val) in enumerate(items):
        is_last = (i == len(items) - 1)

        # 토큰 생성: "이름=값" — 마지막 항목이고 close_paren이면 ')' 추가
        token = f"{key}={val}"
        if is_last and close_paren:
            token += ")"

        stripped_cur = current.strip()

        # ── 줄 길이 초과 여부 판단 ──
        # 현재 줄이 이미 indent 또는 indent+'(' 뿐(= 새 줄 초기 상태)이면
        # 토큰을 강제 추가해야 무한 루프를 방지할 수 있으므로 줄바꿈 생략
        if len(current) + len(token) + 1 > _LINE_WIDTH and stripped_cur not in ('+', '+(', '+ ('):
            # ── 현재 줄을 마무리하고 인라인 주석 복원 ──
            comment = continuation_comments.get(
                current_line_first_key.upper() if current_line_first_key else '', ''
            )
            out_line = current.rstrip()
            if comment:
                out_line += '  ' + comment  # 2칸 공백 후 주석 연결
            lines.append(out_line)

            # ── 새 줄 시작: 이 줄의 첫 파라미터는 현재 key ──
            current = indent + token + ' '
            current_line_first_key = key
        else:
            # 현재 줄에 토큰 추가
            if current_line_first_key is None:
                current_line_first_key = key  # 이 줄의 첫 파라미터명 기록
            current += token + ' '

    # ── 마지막 줄 처리 ──
    # 버퍼에 남은 내용이 있으면 줄 마무리 (단순 indent만 있는 경우는 건너뜀)
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
    ParamEntry 객체 리스트를 `.PARAM` 명령어 라인 목록으로 직렬화합니다.

    파라미터가 많아서 한 줄에 다 담기 어려울 경우,
    80자(_LINE_WIDTH)를 넘지 않게 `+` continuation 라인을 자동으로 생성합니다.

    처리 로직:
        1. ".PARAM "으로 시작하는 줄 버퍼를 초기화합니다.
        2. 각 ParamEntry를 "이름=값 " 토큰으로 변환해 순서대로 버퍼에 붙입니다.
        3. 추가 시 _LINE_WIDTH를 넘으면 현재 줄을 저장하고 "+ " 로 새 줄을 시작합니다.
        4. 마지막 남은 줄을 결과에 추가합니다.

    Args:
        entries (list[ParamEntry]): 직렬화할 ParamEntry 객체 리스트

    Returns:
        list[str]: 생성된 .PARAM 줄 목록
                   예: [".PARAM tox_val=1.2e-8 vth_offset=0.05",
                        "+ k1_base=0.559"]
    """
    if not entries:
        return []

    lines = []
    current = ".PARAM "  # 첫 줄 시작: .PARAM 키워드

    for e in entries:
        token = f"{e.name}={e.value} "
        # _LINE_WIDTH 초과 시 줄바꿈 (현재 줄이 초기 상태".PARAM"이면 무조건 추가)
        if len(current) + len(token) > _LINE_WIDTH and current.strip() != '.PARAM':
            lines.append(current.rstrip())    # 현재 줄 저장
            current = "+ " + token            # 새 continuation 줄 시작
        else:
            current += token                  # 현재 줄에 토큰 추가

    # 마지막 남은 줄 저장 (단순 키워드만 있는 경우는 건너뜀)
    if current.strip() not in ('.PARAM', '+'):
        lines.append(current.rstrip())

    return lines


def write_lib(lib_file: LibFile) -> str:
    """
    메모리에 올려진 `LibFile` 구조 객체를 순수 텍스트(Smart Spice 문법 문자열)로
    변환(직렬화)합니다.

    출력 순서:
        1. 파일 최선두 주석 (* 주석 줄)
        2. 전역 .PARAM 선언부
        3. 전역 기타 지시어 (.temp 등)
        4. 각 .LIB 블록 (순서대로):
            a. 블록 앞 주석
            b. ".LIB 이름" 선언
            c. 블록 내 .PARAM 선언부
            d. 블록 내 기타 지시어
            e. .MODEL 블록들 (두 번째 모델부터 앞에 빈 줄 삽입)
            f. ".ENDL 이름" 선언

    주석·괄호 복원:
        - 각 .MODEL의 comment_lines(* 줄) → 모델 선언 바로 위에 출력
        - open_paren / close_paren → 파라미터 리스트의 괄호를 원형대로 복원
        - continuation_comments    → '+' 줄 끝에 $ 인라인 주석 복원

    Args:
        lib_file (LibFile): 편집이 완료된 LibFile 데이터 객체

    Returns:
        str: Smart Spice 문법으로 직렬화된 파일 전체 텍스트
    """
    out = []  # 출력 줄 목록 (최종적으로 '\n'.join 으로 합침)

    # ── 1. 파일 선두 주석 복원 ──
    for c in lib_file.leading_comments:
        out.append(c)

    # ── 2. 전역 .PARAM 직렬화 ──
    if lib_file.global_params:
        out.extend(_write_param_entries(lib_file.global_params))
        out.append('')  # 블록 간 빈 줄

    # ── 3. 전역 기타 지시어 직렬화 ──
    if lib_file.global_directives:
        for d in lib_file.global_directives:
            out.append(d.raw_text)  # 원문 그대로 출력
        out.append('')  # 지시어 끝 빈 줄

    # ── 4. 각 LIB 블록 직렬화 ──
    for lb in lib_file.lib_blocks:

        # 4-a. 블록 앞 주석 복원
        for c in lb.leading_comments:
            out.append(c)

        # 4-b. .LIB 선언
        out.append(f".LIB {lb.name}")

        # 4-c. 블록 내 .PARAM 선언
        if lb.params:
            out.extend(_write_param_entries(lb.params))

        # 4-d. 블록 내 기타 지시어 (원문 그대로)
        if lb.directives:
            for d in lb.directives:
                out.append(d.raw_text)
            out.append('')  # 지시어 끝 빈 줄

        # 4-e. .MODEL 엔트리들 직렬화
        for idx, model in enumerate(lb.models):

            # 두 번째 모델부터 .MODEL 블록 앞에 빈 줄 한 칸 삽입 (가독성)
            if idx > 0:
                out.append('')

            # 모델 선언 위에 있던 * 주석 복원
            for c in model.comment_lines:
                out.append(c)

            # .MODEL 헤더 출력: ".MODEL 이름 타입"
            model_header = f".MODEL {model.name} {model.model_type}"
            out.append(model_header)

            # 파라미터 줄 출력 (인라인 주석 복원 포함)
            # open_paren / close_paren / continuation_comments를 함께 전달
            if model.params or model.open_paren or model.close_paren:
                out.extend(_format_params(
                    model.params,
                    indent="+ ",
                    open_paren=model.open_paren,
                    close_paren=model.close_paren,
                    continuation_comments=model.continuation_comments,
                ))

        # 4-f. .ENDL 선언 및 블록 뒤 빈 줄
        out.append(f".ENDL {lb.name}")
        out.append('')  # 다음 LIB 블록과의 사이 빈 줄

    # 모든 줄을 개행 문자로 연결하여 단일 문자열 반환
    return '\n'.join(out)


def save_lib(lib_file: LibFile, filepath: str = None) -> str:
    """
    write_lib()로 생성한 텍스트를 실제 로컬 파일에 저장합니다.

    애플리케이션(main.py)에서 「저장」 또는 「다른 이름으로 저장」 버튼을 눌렀을 때
    호출되는 최종 저장 API 입니다.

    처리 흐름:
        1. filepath 인수가 제공되면 그 경로에 저장합니다.
        2. filepath가 None이면 lib_file.filepath(원본 경로)에 덮어씁니다.
        3. 두 경로 모두 없으면 ValueError를 발생시킵니다.
        4. UTF-8 인코딩으로 파일을 씁니다.

    Args:
        lib_file (LibFile): 저장할 LibFile 데이터 객체
        filepath (str, optional): 저장할 파일 경로.
                                  None이면 lib_file.filepath를 사용합니다.

    Returns:
        str: 실제 저장된 파일의 경로

    Raises:
        ValueError: filepath와 lib_file.filepath 모두 None 또는 빈 문자열인 경우
    """
    # ── 저장 경로 결정 ──
    path = filepath or lib_file.filepath
    if not path:
        raise ValueError("저장할 파일 경로가 지정되지 않았습니다.")

    # ── 직렬화 후 파일 쓰기 ──
    content = write_lib(lib_file)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return path
