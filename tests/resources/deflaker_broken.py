class SuperOld:
    def magic(self):
        assert True


class SuperNew:
    def magic(self):
        assert False


class App(SuperNew):
    pass


def test_app():
    App().magic()
