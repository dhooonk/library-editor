"""
data_model.py
Smart Spice LIB 파일의 데이터 모델 정의
"""
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ParamEntry:
    """
    .PARAM 선언의 단일 변수를 나타냄
    예: .PARAM tox_val=1.2e-8
    """
    name: str
    value: str  # 값은 숫자, 수식 등 문자열로 보관


@dataclass
class ModelEntry:
    """
    .MODEL 엔트리를 나타냄
    예:
      .MODEL NMOS_1 NMOS
      + VTH0=0.45 TOX=1.2e-8
    """
    name: str
    model_type: str
    params: OrderedDict = field(default_factory=OrderedDict)
    # params: { 'param_name': 'param_value', ... }
    comment_lines: List[str] = field(default_factory=list)  # 앞에 붙는 주석들

    def copy(self) -> "ModelEntry":
        return ModelEntry(
            name=self.name,
            model_type=self.model_type,
            params=OrderedDict(self.params),
            comment_lines=list(self.comment_lines),
        )


@dataclass
class LibBlock:
    """
    .LIB ~ .ENDL 블록을 나타냄
    """
    name: str
    models: List[ModelEntry] = field(default_factory=list)
    params: List[ParamEntry] = field(default_factory=list)
    # LIB 블록 내 .PARAM 선언
    leading_comments: List[str] = field(default_factory=list)

    def find_model(self, name: str) -> Optional[ModelEntry]:
        for m in self.models:
            if m.name.upper() == name.upper():
                return m
        return None


@dataclass
class LibFile:
    """
    파싱된 .lib 파일 전체를 나타냄
    """
    filepath: str = ""
    global_params: List[ParamEntry] = field(default_factory=list)
    # 전역 .PARAM (LIB 블록 밖에 선언된 것)
    lib_blocks: List[LibBlock] = field(default_factory=list)
    leading_comments: List[str] = field(default_factory=list)
    # 파일 최상단 주석

    def find_lib(self, name: str) -> Optional[LibBlock]:
        for lb in self.lib_blocks:
            if lb.name.upper() == name.upper():
                return lb
        return None

    def all_params(self) -> List[ParamEntry]:
        """전역 + 모든 LIB 블록의 param 합계"""
        result = list(self.global_params)
        for lb in self.lib_blocks:
            result.extend(lb.params)
        return result
