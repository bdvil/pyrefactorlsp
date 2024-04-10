import sample_project.pkg.mod2 as mod2
from sample_project import a as aa

from . import mod4

z = mod4.b

y = mod2.x

z, w = (mod2.x, mod2.x)


def test_func(x: mod2.T):
    tmp = aa + y
    return x


class Test:
    aa: mod2.T

    def __init__(self):
        self.bb = y + 2

    def fun1(self):
        return test_func(self.aa)

    def fun2(self, cc):
        return self.bb
