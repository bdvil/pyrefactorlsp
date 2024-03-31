from sample_project import a
from sample_project.pkg.mod2 import T, x

y = x

z, w = (x, x)


def test_func(x: T):
    tmp = a + y
    return x


class Test:
    aa: T

    def __init__(self):
        self.bb = y + 2

    def fun1(self):
        return test_func(self.aa)

    def fun2(self, cc):
        return self.bb
