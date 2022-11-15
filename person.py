import json
import os
import time
from typing import List

from loguru import logger

from config import settings

from pydantic import BaseModel, validator


class Person(BaseModel):
    first_name: str
    last_name: str
    position: str

    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class WorkTime(BaseModel):
    person: Person
    start_work_hour: int
    start_work_minute: int
    end_work_hour: int
    end_work_minute: int

    def time_work(self):
        return f"{self.person.full_name()} время работы {self.start_work_hour}:{self.start_work_minute}-" \
               f"{self.end_work_hour}:{self.end_work_minute}"

    @validator('start_work_minute', 'end_work_minute')
    def start_end_work_minut(cls, val: int):
        if 0 < val > 59:
            raise ValueError("Укажите минуты от 00 до 59")
        if val == 0 or val < 10:
            return f'0{val}'
        return val

    @validator('start_work_hour', 'end_work_hour')
    def start_end_work_hour(cls, val: int):
        if 0 < val > 23:
            raise ValueError("Укажите часы от 00 до 23")
        return val


class State(BaseModel):
    worktime: WorkTime

    @staticmethod
    def write_meeting_time(data, person):
        """Метод для записи встечи в файл"""
        with open(settings.file_state, 'w+') as file:
            json.dump(data, file)
        return logger.success(f'Запись сотруднику {person} успешно добавленна')

    @staticmethod
    def read_meeting_time():
        """Метода для получения данных из файла"""
        with open(settings.file_state, 'r+') as file:
            data = json.load(file)
        return data

    @staticmethod
    def check_correct_time(time_start_hour: int, time_start_minute: int,
                           time_end_hour: int, time_end_minute: int):
        """Проверка корректно указанного времени"""
        if time_start_hour > 23 or time_end_hour > 23:
            raise ValueError('Укажите корректно время')
        elif time_start_minute > 59 or time_end_minute > 59:
            raise ValueError('Укажите корректно время')

    def append_time_meet(self, time_start_hour: int, time_start_minute: int,
                         time_end_hour: int, time_end_minute: int):
        """Метод для добавления данных в файл"""
        start_meet = int(time_start_hour) * 60 + int(time_start_minute)
        end_meet = int(time_end_hour) * 60 + int(time_end_minute)
        start_day_work = int(self.worktime.start_work_hour) * 60 + int(self.worktime.start_work_minute)
        end_day_work = int(self.worktime.end_work_hour) * 60 + int(self.worktime.end_work_minute)
        meeting_file = {self.worktime.person.full_name(): [[start_meet, end_meet], [start_day_work, end_day_work]]}
        if self.is_empty_file():
            self.write_meeting_time(meeting_file, self.worktime.person.full_name())
            return
        data = self.read_meeting_time()
        self.check_correct_time(time_start_hour, time_start_minute, time_end_hour, time_end_minute)
        self.check_free_time(start_meet, end_meet)
        self.check_overlay_time(start_meet, end_meet)
        if self.worktime.person.full_name() in data:
            data[self.worktime.person.full_name()].append([int(time_start_hour) * 60 + int(time_start_minute),
                                                           int(time_end_hour) * 60 + int(time_end_minute)])
        else:
            data[self.worktime.person.full_name()] = [[start_meet, end_meet], [start_day_work, end_day_work]]
        self.write_meeting_time(data, self.worktime.person.full_name())

    def get_free_time(self):
        """Метод для просмотра свободного времени сотрудника"""
        data = self.check_person_job_time()
        if not data:
            return f'{self.worktime.time_work()} - у сотрудника нет занятых слотов'
        interval_person = self.get_interval_person(data)
        work_time: list = self.get_interval_person(data)[-1]
        del interval_person[-1]
        data_free_time = get_all_free_time(self.worktime.person.full_name(), interval_person, work_time)
        return data_free_time

    def get_interval_person(self, data):
        """Получаем интервал работы сотрудника"""
        return [v for v in data[self.worktime.person.full_name()]]

    def check_person_job_time(self):
        """Проверка времени работы сотрудника"""
        if self.is_empty_file():
            raise ValueError("У сотрудников нет занятых слотов")
        data = self.read_meeting_time()
        if self.worktime.person.full_name() in data:
            return data
        return False

    def check_overlay_time(self, start_interval: int, end_interval: int):
        """Проверка накладки временных промежутков"""
        data = self.check_person_job_time()
        if data:
            del data[self.worktime.person.full_name()][-1]
            for i in data[self.worktime.person.full_name()]:
                if start_interval >= i[0] and start_interval <= i[1] or end_interval >= i[0] and end_interval <= i[1]:
                    raise ValueError('Время не подходит под расписание')
                if start_interval < i[0] and end_interval > i[1]:
                    raise ValueError('Время не подходит под расписание')
                if start_interval > end_interval:
                    raise ValueError('Укажите время корректно')

    def check_free_time(self, start_interval: int, end_interval: int):
        """Проверка свободного времени"""
        start_work_day = (int(self.worktime.start_work_hour) * 60 + int(self.worktime.start_work_minute))
        end_work_day = (int(self.worktime.end_work_hour) * 60 + int(self.worktime.end_work_minute))
        if start_work_day > start_interval:
            raise ValueError('Время не входит в рабочий день')
        if end_work_day < end_interval:
            raise ValueError('Время не входит в рабочий день')
        if end_interval < start_interval:
            raise ValueError('Интервал указан неверно')

    @staticmethod
    def is_empty_file():
        """Проверка на пустоту файла"""
        if not os.path.exists(settings.file_state):
            create_file = open(settings.file_state, 'w')
            create_file.close()
        return os.stat(settings.file_state).st_size == 0


def get_all_free_time(person: str, interval_person: List[list], work_time: list):
    """Перевод времени в читаемый вид"""
    interval_free = []
    if work_time[0] != sorted(interval_person)[0][0]:
        interval_free.append([work_time[0], sorted(interval_person)[0][0]])
    for i in sorted(interval_person):
        index = sorted(interval_person).index(i)
        if index == len(interval_person) - 1:
            interval_free.append([i[1], work_time[1]])
            break
        interval_free.append([i[1], sorted(interval_person)[index + 1][0]])
    str_interval = []
    for i in interval_free:
        interval_start = f"{int(i[0] / 60)}:{int(i[0] % 60) if int(i[0] % 60) >= 10 else f'0{int(i[0] % 60)}'}"
        interval_end = f"{int(i[1] / 60)}:{int(i[1] % 60) if int(i[1] % 60) >= 10 else f'0{int(i[1] % 60)}'}"
        str_interval.append(f"{interval_start} - {interval_end}")
    data = {person: str_interval}
    return data


def get_free_time_persons(lst):
    """Получение данных о времени работы сотрудников"""
    try:
        with open(settings.file_state, 'r+') as file:
            data = json.load(file)
    except Exception:
        logger.info('У сотрудников нет занятых слотов')
        return
    all_data = []
    free_time = []
    for i in lst:
        try:
            perrson_free_time = get_all_free_time(i, data[i], data[i][-1])
            all_data.append(perrson_free_time)
        except KeyError as er:
            free_time.append(er.args)
    all_data.append({'свободные сотрудники': free_time})
    return all_data


person_1 = Person(first_name='jane', last_name='cory', position='data')
person_2 = Person(first_name='liam', last_name='neeson', position='data')
person_3 = Person(first_name='ian', last_name='mcKellen', position='data')
person_4 = Person(first_name='tom', last_name='hiddleston', position='data')
work_1 = WorkTime(person=person_1, start_work_hour=8, start_work_minute=5, end_work_hour=18, end_work_minute=30)
work_2 = WorkTime(person=person_2, start_work_hour=9, start_work_minute=00, end_work_hour=19, end_work_minute=30)
work_3 = WorkTime(person=person_3, start_work_hour=7, start_work_minute=00, end_work_hour=19, end_work_minute=40)
work_4 = WorkTime(person=person_4, start_work_hour=12, start_work_minute=5, end_work_hour=19, end_work_minute=10)


State(worktime=work_3).append_time_meet(14, 55, 15, 45)
State(worktime=work_2).append_time_meet(12, 55, 13, 45)
State(worktime=work_4).append_time_meet(14, 15, 17, 45)
time.sleep(0.2)
print(f'вывод свободного времени сотрудника - {State(worktime=work_4).get_free_time()}')
print(f'вывод свободного времени сотрудника - {State(worktime=work_2).get_free_time()}')
print(f"вывод свободного времени списка сотрудников - {get_free_time_persons(['jane cory', 'liam neeson', 'ian mcKellen', 'tom hiddleston'])}")
