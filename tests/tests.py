import unittest

from person import Person, WorkTime, State, person_1, work_4


class TestStringMethods(unittest.TestCase):

    def test_instance(self):
        self.assertTrue(isinstance(person_1, Person))
        self.assertTrue(isinstance(work_4, WorkTime))
        self.assertTrue(isinstance(State(worktime=work_4).get_free_time(), str))

if __name__ == '__main__':
    unittest.main()


