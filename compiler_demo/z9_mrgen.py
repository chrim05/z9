# middle representation generator

from data import *

class MrGen:
  def __init__(self, unit) -> None:
    from unit import TranslationUnit

    self.unit: TranslationUnit = unit

  @property
  def root(self) -> MultipleNode:
    return self.unit.root

  @property
  def tab(self) -> SemaTable:
    return self.unit.tab

  def gen_whole_unit(self) -> None:
    for top_level in self.root.nodes:
      pass